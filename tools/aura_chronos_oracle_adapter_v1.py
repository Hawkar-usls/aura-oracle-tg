#!/usr/bin/env python3
"""Transparent forced-choice adapter over the *real* AURA 5D spiral computation.

AURA 5D does not natively forecast random digits. This decoder maps deterministic
AURA graph features into 0..9; it must not be described as a learned digit head.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from aura_5d_spiral_v2 import run as aura_5d_run
from aura_semantic_predictive_core_v2 import canonical_bytes

MODEL_NAME = "AURA_5D_DERIVED_DIGIT_DECODER_PILOT"
PROMPT_TEMPLATE = (
    "AURA CHRONOS-002: trial {trial:03d} of 100. Before any future random data, "
    "analyse a prospective single uniform digit 0 through 9 at least 1 ms ahead. "
    "The outcome is unknown. No previous trial outcomes or future random seed are provided. "
    "Return a structured 5D analysis, with no authority to claim physical precognition."
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_digit(aura_result: dict[str, Any]) -> tuple[int, str]:
    """Registered deterministic extraction; not an AURA-native classification."""
    axes = aura_result["axes"]
    features = {
        "origin_state_hash": aura_result["origin_state_hash"],
        "graph_sha256": aura_result["integrity"]["graph_sha256"],
        "state_delta_sha256": axes["D5_SPIRAL_ABSTRACTION"]["state_delta_sha256"],
        "structural_signals": axes["D3_HRAIN_STRUCTURAL"]["structural_signals"],
        "reverse_findings": axes["D2_REVERSE"]["findings"],
        "spiral_status": aura_result["spiral_status"],
    }
    digest = hashlib.sha256(canonical_bytes(features)).digest()
    # Unbiased modulo reduction, with rejection (extremely unlikely) specified.
    bound = ((1 << 256) // 10) * 10
    while int.from_bytes(digest, "big") >= bound:
        digest = hashlib.sha256(digest).digest()
    return int.from_bytes(digest, "big") % 10, hashlib.sha256(canonical_bytes(features)).hexdigest()


def predict_batch() -> tuple[list[int], dict[str, Any]]:
    digits: list[int] = []
    trace_hashes: list[str] = []
    for i in range(1, 101):
        prompt = PROMPT_TEMPLATE.format(trial=i)
        result = aura_5d_run({"text": prompt, "generation": 1,
                              "intent_id": "CHRONOS-002-FROZEN-DIGITS",
                              "source_ref": "FIXED_PREREGISTERED_PROMPT"}, db_path=None)
        digit, trace_sha = decode_digit(result)
        digits.append(digit)
        trace_hashes.append(trace_sha)
    tool_root = Path(__file__).resolve().parent
    return digits, {
        "source_model": MODEL_NAME,
        "native_aura_digit_head": False,
        "aura_5d_algorithm_executed": True,
        "db_or_future_outcomes_used": False,
        "feature_decoder": "sha256(canonical AURA 5D feature projection) with rejection-sampled modulo 10",
        "prompt_template_sha256": hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest(),
        "aura_5d_source_sha256": sha256_file(tool_root / "aura_5d_spiral_v2.py"),
        "aura_core_source_sha256": sha256_file(tool_root / "aura_semantic_predictive_core_v2.py"),
        "adapter_source_sha256": sha256_file(Path(__file__)),
        "all_trace_hashes_sha256": hashlib.sha256(canonical_bytes(trace_hashes)).hexdigest(),
        "epistemic_boundary": "REAL_AURA_COMPUTATION_BUT_ARBITRARY_DECODER_NOT_NATIVE_DIGIT_PREDICTION",
    }
