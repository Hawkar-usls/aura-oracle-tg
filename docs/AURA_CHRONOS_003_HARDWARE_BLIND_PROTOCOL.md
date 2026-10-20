# CHRONOS-003 — externally attested millisecond blind trial (pre-hardware)

**Status:** instrument requirements + signed-evidence validator implemented.
**Real experiment:** NOT RUN. **Physical timebase:** NOT AVAILABLE. **Independent
hardware RNG:** NOT AVAILABLE. **Global science gate:** BLOCKED.

## 1. Frozen forecast and timing interpretation

The CHRONOS-002 NATIVE10 frozen distributions are reused unchanged:

* Forecast SHA-256:
  `c1dd23d52fc283b53f300a9b349845491d8a56a0ad024ff773cd9bf71741e129`
* Initial freeze commit containing the forecast:
  `4162f4beb5a927ef45eacbf109aefdb6dad1cfc8`
* Source forecast:
  `experiments/AURA-NATIVE10-forecast-v1-frozen.json`

This first CHRONOS-003 trial, if physically performed, would test whether an
**already committed array of forecasts** matches independent digits sampled at
nominal **1-ms event intervals**. It would **not** test a precisely 1-ms
forecast-to-target lead: the forecast-to-first-draw interval can be hours or
days. Those two quantities must never be conflated. A subsequent separately
preregistered just-in-time protocol would be needed to claim a 1-ms lead.

## 2. Required independent physical apparatus

| Component | Required evidence | Why it matters |
| --- | --- | --- |
| Hardware TRNG | Manufacturer, model, serial, calibration/health records, raw entropy archive, unbiased rejection-sampling extractor | Prove digit production is separated from AURA and occurred after forecast freeze |
| Time standard | GNSS-disciplined PPS **or** qualified PTP grandmaster, clock serial/calibration, synchronization lock logs | Establish a traceable UTC timing chain and its uncertainty |
| Time capture | Hardware-latched event timestamps and independent monotonic capture, lock state per event | Reveal scheduling jitter and clock-offset or drift problems |
| External observer | Independently pinned Ed25519 public key, sealed evidence chain and signed canonical JSON | Detect tampering and identify a witness by an out-of-band trust procedure |
| Archive | Read-only immutable storage / externally verifiable hashes | Permit outsiders to repeat time and entropy checks |

**Provisional tolerances for v1**, chosen as conservative fractions of the
nominal 1-ms event separation, *not* achieved measurements:

* Claimed maximum absolute UTC offset: ≤100,000 ns (100 µs).
* Claimed clock and per-event uncertainty: ≤100,000 ns (100 µs).
* Consecutive event timestamps and monotonic capture deltas:
  1,000,000 ±200,000 ns.
* Capture must report continuous clock lock and ordered 100 physical draws.
* Target entropy creation must follow the Git publication of the frozen
  forecast. A Git SHA alone does not prove publication time; this needs
  independent timestamp evidence.

The tolerances only accept a **structure of claims**; the lab must supply
actual uncertainty measurements and independent calibration certificates.
PPS / GNSS or PTP does not automatically make a clock "atomic".

## 3. Signed statement format

The independent laboratory, not AURA/JANUS, must create the statement with
schema `janus.aura.chronos003.observation_statement.v1`. It must include:

1. `experiment = CHRONOS-003-NATIVE10-EXTERNAL`, immutable
   `forecast_sha256`, `forecast_git_commit`, `origin = EXTERNAL_LAB_OBSERVER`,
   `observer_id`, `git_commit_timing_evidence_ref`.
2. Nanosecond integer fields `forecast_commit_publication_utc_ns` and
   `entropy_start_utc_ns` with strict chronology after the original forecast.
3. `clock` fields `type` (GNSS_PPS/PTP_GRANDMASTER), manufacturer, model,
   serial, calibration/traceability/lock/offset/jitter references, and
   `max_abs_utc_offset_ns`, `max_utc_uncertainty_ns`.
4. `rng` fields `type = HARDWARE_TRNG`, identification and calibration,
   entropy health, raw archive, extraction implementation and
   `digit_extraction = REJECTION_SAMPLED_UNIFORM_0_TO_9`.
5. Exactly 100 ordered `events`: `trial`, `digit`, `event_utc_ns`,
   `capture_monotonic_ns`, `time_uncertainty_ns`, `clock_locked_at_capture`,
   `raw_entropy_record_ref`.
6. `signed_record_archive_ref` pointing to the archived raw observation file.

The outer JSON envelope has schema
`janus.aura.chronos003.signed_external_observation.v1`, a `statement`
object, and `signature_ed25519_base64` over the **canonical UTF-8 JSON**
(`sort_keys=True`, no whitespace separators, no NaNs). The trusted observer
public key must be provided separately, without allowing the packet to choose
its own trusted key.

## 4. Offline verification tool — always non-authoritative

```bash
python tools/aura_chronos_003_hardware_gate.py \
  --forecast experiments/AURA-NATIVE10-forecast-v1-frozen.json \
  --evidence /path/to/external-observer-signed-evidence.json \
  --observer-public-key /path/to/out-of-band-verified-observer-ed25519.pub.pem \
  --output /path/to/audit-result-new.json

python -m unittest discover -s tests -p 'test_aura_chronos_003_hardware_gate.py' -v
```

This tool reads but **never produces independent RNG outcomes or evidence**.
It checks the forecast SHA, initial freeze commit ID claim, event chronology,
cadence, uncertainty ceilings and Ed25519 signature using OpenSSL 3, then
reports descriptive hits, multiclass Brier and log loss. It has no provision to
execute AURA actions, deploy the project, merge a PR or mutate a forecast.

Signature validation can demonstrate that a known key signed data, **not**
whether the signer used the stated physical equipment. This program lacks an
out-of-band instrument audit, hardware calibration verification, source
inspection of a true physical RNG, independently authenticated public-key
provenance and independent Git publication timestamp verification. Therefore
**even its syntactically perfect input returns**:

```text
cryptographic_signature_integrity = PASS_WITH_SUPPLIED_PUBLIC_KEY
evidence_structural_and_claimed_cadence = PASS
trusted_key_identity_established = false
physical_clock_calibration_verified = false
external_rng_physical_independence_verified = false
hardware_gate = BLOCKED_PENDING_EXTERNAL_AUTHORITY_AND_REAL_DEVICE_EVIDENCE
physical_retrocausality_established = false
```

The unit tests generate synthetic statements and disposable keys marked
`FIXTURE` to test rejection and verification logic. They are **not** a run,
external attestation or evidence of special forecasting powers.

## 5. Statistical registration and interpretation

The published native forecast is never changed. Primary run contains exactly
100 scheduled targets; no optional stopping or selective rerun. Register
before drawing: top-1 exact hit count with null `Binomial(100, 0.1)`, one-sided
alpha = 0.01, plus mean log loss/Brier against uniform probabilities and
secondary calibration. Any unusual result is hypothesis-generating pending
independent blinded replication; consider variant multiplicity.

The presently frozen native model scored **0/20** on a historical holdout. No
evidence has yet shown that it can predict new independent randomness. The
CHRONOS-003 hardware test is only a prospective scientific question.

## 6. Next external handoff

Identify an independent laboratory or instrument operator who can (a)
document clock/RNG uncertainty and health tests, (b) retain control of signing
keys and hardware, and (c) publish results after inspecting a pre-existing
GitHub forecast commitment. Obtain calibration/evidence records and a
separately validated public key *before* scheduling the run. Until then the
research gate stays **BLOCKED_NO_HARDWARE**.
