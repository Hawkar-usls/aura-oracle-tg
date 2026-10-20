#!/usr/bin/env python3
"""CHRONOS-003: inspect externally supplied signed timing/entropy records.

The local validator cannot authenticate physical instruments, laboratory
independence, a trusted UTC timebase or external Git publication timestamps.
Consequently the global HARDWARE gate intentionally remains BLOCKED.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from aura_native_digit_head_v1 import checked_forecast, score_external


SCHEMA = "janus.aura.chronos003.signed_external_observation.v1"
STATEMENT_SCHEMA = "janus.aura.chronos003.observation_statement.v1"
RESULT_SCHEMA = "janus.aura.chronos003.evidence_audit.v1"
TRIALS = 100
NOMINAL_NS = 1_000_000
MAX_OFFSET_NS = 100_000
MAX_UNCERTAINTY_NS = 100_000
MAX_INTERVAL_DEVIATION_NS = 200_000
# Initial forecast freeze commit, not mutable latest PR head.
CHRONOS002_NATIVE10_FREEZE_COMMIT = "4162f4beb5a927ef45eacbf109aefdb6dad1cfc8"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True, allow_nan=False).encode("utf-8")


def require_int(value: Any, name: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(name)
    return value


def require_ref(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError(name)
    return value


def require_instrument(data: Any, kind: str, valid_types: set[str]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("type") not in valid_types:
        raise ValueError(kind + "_INSTRUMENT_TYPE")
    for field in ("manufacturer", "model", "serial", "calibration_evidence_ref"):
        require_ref(data.get(field), kind + "_" + field.upper())
    return data


def check_statement(statement: Any, frozen: dict[str, Any]) -> dict[str, Any]:
    packet = checked_forecast(frozen)
    if not isinstance(statement, dict) or statement.get("schema") != STATEMENT_SCHEMA:
        raise ValueError("CHRONOS003_STATEMENT_SCHEMA_REQUIRED")
    if statement.get("experiment") != "CHRONOS-003-NATIVE10-EXTERNAL":
        raise ValueError("CHRONOS003_EXPERIMENT_IDENTIFIER_MISMATCH")
    if statement.get("forecast_sha256") != frozen["commitment_sha256"]:
        raise ValueError("CHRONOS003_FROZEN_FORECAST_MISMATCH")
    if statement.get("forecast_git_commit") != CHRONOS002_NATIVE10_FREEZE_COMMIT:
        raise ValueError("CHRONOS003_INITIAL_FREEZE_COMMIT_REQUIRED")
    if statement.get("origin") != "EXTERNAL_LAB_OBSERVER":
        raise ValueError("CHRONOS003_INDEPENDENT_ORIGIN_REQUIRED")
    require_ref(statement.get("observer_id"), "OBSERVER_ID_REQUIRED")
    require_ref(statement.get("git_commit_timing_evidence_ref"), "GIT_COMMIT_TIME_EVIDENCE_REQUIRED")
    begin_ns = require_int(statement.get("entropy_start_utc_ns"), "ENTROPY_START_TIMESTAMP_REQUIRED", minimum=1)
    published_ns = require_int(statement.get("forecast_commit_publication_utc_ns"),
                               "FORECAST_PUBLICATION_TIMESTAMP_REQUIRED", minimum=1)
    if not (packet["prepared_at_unix_ns"] < published_ns < begin_ns):
        raise ValueError("FORECAST_MUST_PREDATE_PUBLICATION_AND_ENTROPY")

    clock = require_instrument(statement.get("clock"), "CLOCK", {"GNSS_PPS", "PTP_GRANDMASTER"})
    for field in ("traceability_evidence_ref", "lock_state_log_ref", "offset_measurement_ref",
                  "jitter_measurement_ref"):
        require_ref(clock.get(field), "CLOCK_" + field.upper())
    offset_bound = require_int(clock.get("max_abs_utc_offset_ns"), "CLOCK_OFFSET_BOUND_MISSING")
    uncertainty_bound = require_int(clock.get("max_utc_uncertainty_ns"), "CLOCK_UNCERTAINTY_BOUND_MISSING")
    if offset_bound > MAX_OFFSET_NS or uncertainty_bound > MAX_UNCERTAINTY_NS:
        raise ValueError("CLOCK_CLAIMED_ERROR_BUDGET_TOO_LARGE")

    rng = require_instrument(statement.get("rng"), "RNG", {"HARDWARE_TRNG"})
    for field in ("entropy_health_evidence_ref", "raw_entropy_archive_ref", "extractor_implementation_ref"):
        require_ref(rng.get(field), "RNG_" + field.upper())
    if rng.get("digit_extraction") != "REJECTION_SAMPLED_UNIFORM_0_TO_9":
        raise ValueError("RNG_UNBIASED_EXTRACTION_REQUIRED")

    events = statement.get("events")
    if not isinstance(events, list) or len(events) != TRIALS:
        raise ValueError("CHRONOS003_EXACTLY_100_EVENTS_REQUIRED")
    prior_utc, prior_mono = None, None
    outcomes, intervals = [], []
    for trial, event in enumerate(events, 1):
        if not isinstance(event, dict) or event.get("trial") != trial:
            raise ValueError("CHRONOS003_NONCANONICAL_EVENT_ORDER")
        digit = require_int(event.get("digit"), "CHRONOS003_INVALID_DIGIT", maximum=9)
        utc_ns = require_int(event.get("event_utc_ns"), "CHRONOS003_EVENT_TIME_REQUIRED", minimum=1)
        mono_ns = require_int(event.get("capture_monotonic_ns"), "CHRONOS003_MONOTONIC_TIME_REQUIRED", minimum=1)
        u_ns = require_int(event.get("time_uncertainty_ns"), "CHRONOS003_EVENT_UNCERTAINTY_REQUIRED")
        if u_ns > MAX_UNCERTAINTY_NS:
            raise ValueError("CHRONOS003_EVENT_TIME_UNCERTAINTY_TOO_LARGE")
        if event.get("clock_locked_at_capture") is not True:
            raise ValueError("CHRONOS003_CLOCK_LOCK_NOT_ATTESTED")
        require_ref(event.get("raw_entropy_record_ref"), "CHRONOS003_EVENT_ENTROPY_REFERENCE_REQUIRED")
        if utc_ns < begin_ns or (utc_ns - u_ns) <= published_ns:
            raise ValueError("CHRONOS003_EVENT_MUST_FOLLOW_FORECAST_AND_ENTROPY_START")
        if prior_utc is not None:
            utc_delta = utc_ns - prior_utc
            mono_delta = mono_ns - prior_mono
            if not (NOMINAL_NS - MAX_INTERVAL_DEVIATION_NS <= utc_delta <= NOMINAL_NS + MAX_INTERVAL_DEVIATION_NS):
                raise ValueError("CHRONOS003_MILLISECOND_CADENCE_OUT_OF_SPEC")
            if not (NOMINAL_NS - MAX_INTERVAL_DEVIATION_NS <= mono_delta <= NOMINAL_NS + MAX_INTERVAL_DEVIATION_NS):
                raise ValueError("CHRONOS003_MONOTONIC_CADENCE_OUT_OF_SPEC")
            if abs(utc_delta - mono_delta) > MAX_OFFSET_NS + uncertainty_bound:
                raise ValueError("CHRONOS003_UTC_MONOTONIC_DISAGREEMENT")
            intervals.append(utc_delta)
        prior_utc, prior_mono = utc_ns, mono_ns
        outcomes.append(digit)
    require_ref(statement.get("signed_record_archive_ref"), "EXTERNAL_EVIDENCE_ARCHIVE_REQUIRED")
    return {
        "digits": outcomes,
        "first_event_utc_ns": events[0]["event_utc_ns"],
        "last_event_utc_ns": events[-1]["event_utc_ns"],
        "min_interval_ns": min(intervals),
        "max_interval_ns": max(intervals),
        "claimed_clock_error_bound_ns": offset_bound,
        "claimed_clock_uncertainty_ns": uncertainty_bound,
    }


def verify_ed25519(statement: dict[str, Any], signature_b64: str, public_key_path: Path) -> None:
    """Cryptographic integrity only. The caller must independently vet key ownership."""
    if not public_key_path.is_file():
        raise ValueError("OUT_OF_BAND_PUBLIC_KEY_MISSING")
    if not isinstance(signature_b64, str):
        raise ValueError("OBSERVER_SIGNATURE_REQUIRED")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("OBSERVER_SIGNATURE_MALFORMED") from exc
    if len(signature) != 64:
        raise ValueError("ED25519_SIGNATURE_MUST_BE_64_BYTES")
    with tempfile.TemporaryDirectory(prefix="chronos003-verify-") as directory:
        root = Path(directory)
        payload_path = root / "statement.json"
        signature_path = root / "signature.bin"
        payload_path.write_bytes(canonical(statement))
        signature_path.write_bytes(signature)
        command = ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key_path),
                   "-rawin", "-in", str(payload_path), "-sigfile", str(signature_path)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("ED25519_VERIFIER_UNAVAILABLE") from exc
        if result.returncode != 0:
            raise ValueError("ED25519_OBSERVER_SIGNATURE_INVALID")


def audit(frozen: dict[str, Any], evidence: Any, *, public_key: Path) -> dict[str, Any]:
    if not isinstance(evidence, dict) or evidence.get("schema") != SCHEMA:
        raise ValueError("CHRONOS003_SIGNED_ENVELOPE_REQUIRED")
    statement = evidence.get("statement")
    reviewed = check_statement(statement, frozen)
    verify_ed25519(statement, evidence.get("signature_ed25519_base64"), public_key)
    # These claims are solely from a signer's packet; even valid Ed25519 is not
    # traceability, a calibrated oscillator or proof of a separate RNG.
    observed = {
        "schema": "janus.aura.native_digit_head.external_observation.v1",
        "forecast_commitment_sha256": frozen["commitment_sha256"],
        "resolver": "EXTERNAL_LAB_OBSERVER_CLAIMED",
        "evidence_refs": [statement["signed_record_archive_ref"]],
        "observed_at_unix_ns": reviewed["last_event_utc_ns"],
        "outcomes": reviewed.pop("digits"),
    }
    score = score_external(frozen, observed)
    return {
        "schema": RESULT_SCHEMA,
        "statement_sha256": hashlib.sha256(canonical(statement)).hexdigest(),
        "forecast_sha256": frozen["commitment_sha256"],
        "cryptographic_signature_integrity": "PASS_WITH_SUPPLIED_PUBLIC_KEY",
        "evidence_structural_and_claimed_cadence": "PASS",
        "trusted_key_identity_established": False,
        "physical_clock_calibration_verified": False,
        "external_rng_physical_independence_verified": False,
        "git_commit_timestamp_externally_verified": False,
        "hardware_gate": "BLOCKED_PENDING_EXTERNAL_AUTHORITY_AND_REAL_DEVICE_EVIDENCE",
        "research_gate": "UNVERIFIED_OBSERVER_ASSERTIONS_ONLY",
        "physical_retrocausality_established": False,
        "event_timing_as_asserted": reviewed,
        "score_on_unauthenticated_physical_assertions_only": score,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CHRONOS-003 external evidence format/signature check; no hardware authority")
    parser.add_argument("--forecast", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--observer-public-key", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(json.loads(args.forecast.read_text(encoding="utf-8")),
                   json.loads(args.evidence.read_text(encoding="utf-8")),
                   public_key=args.observer_public_key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"phase": "STRUCTURAL_SIGNATURE_AUDIT_ONLY",
                      "hardware_gate": result["hardware_gate"],
                      "physical_retrocausality_established": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
