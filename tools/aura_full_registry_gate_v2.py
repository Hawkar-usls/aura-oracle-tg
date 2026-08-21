#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

from aura_5d_spiral_v2 import run as run_5d
from aura_predictive_input_v2 import AuraPredictiveInput
from aura_semantic_predictive_core_v2 import AuraIndex


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed full Janus Meta Registry gate for Aura v2")
    ap.add_argument("registry_root")
    ap.add_argument("--db", default="runtime/aura_full_registry.sqlite3")
    ap.add_argument("--receipt", default="runtime/full-registry-receipt.json")
    args = ap.parse_args()

    started = time.time()
    receipt: dict[str, object] = {
        "schema": "janus.aura.full_meta_registry.gate_receipt.v2",
        "status": "REJECT_UNFINISHED",
        "github_actor": os.environ.get("GITHUB_ACTOR"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "registry_root": str(Path(args.registry_root).resolve()),
        "registry_write_performed": False,
        "index_is_source_of_truth": False,
        "world_truth": False,
        "errors": [],
    }
    out_path = Path(args.receipt)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        idx = AuraIndex(args.db)
        try:
            ingest = idx.ingest_paths([Path(args.registry_root)], force=False)
            stats = idx.stats()
            hits = idx.semantic_search("ORIGIN_PRIME reverse tranception", 8)
            question = idx.registry_discriminator("ORIGIN_PRIME reverse tranception", 8)
        finally:
            idx.close()

        pred = AuraPredictiveInput(args.db)
        try:
            suggestions = pred.suggest_tokens("janus ", 8)
            phrases = pred.suggest_phrases("janus ", 5, 3)
        finally:
            pred.close()

        spiral = run_5d({
            "generation": 1,
            "intent_id": "a" * 64,
            "source_ref": "AURA_FULL_META_REGISTRY_GATE_V2",
            "text": "Пройди JANUS Meta Registry через Reverse и Tranception. Но обязательно верни найденное к истоку и продолжи как спираль, а не круг. Следующий виток должен стать ORIGIN_PRIME."
        }, db_path=args.db)
        op = spiral["axes"]["D5_SPIRAL_ABSTRACTION"]["origin_prime"]

        checks = {
            "files_seen_positive": int(ingest["files_seen"]) > 0,
            "files_indexed_or_cached": int(stats["indexed_files"]) > 0,
            "records_positive": int(stats["indexed_records"]) > 0,
            "semantic_hits_positive": len(hits) > 0,
            "spiral_advanced": spiral["spiral_status"] == "ADVANCED_TO_ORIGIN_PRIME",
            "origin_prime_exists": bool(op),
            "origin_prime_generation_2": bool(op and int(op["generation"]) == 2),
            "origin_state_changed": bool(op and spiral["origin_state_hash"] != op["origin_prime_state_hash"]),
            "source_immutable": spiral["integrity"]["source_text_mutated"] is False,
            "hrain_projection": spiral["axes"]["D3_HRAIN_STRUCTURAL"]["hemisphere"] == "LEFT_HRAIN",
            "inaihr_projection": spiral["axes"]["D4_INAIHR_ASSOCIATIVE"]["hemisphere"] == "RIGHT_INAIHR",
        }
        passed = all(checks.values())
        receipt.update({
            "status": "PASS_FULL_META_REGISTRY_REFERENCE_RUNTIME" if passed else "REJECT_INVARIANT_FAILURE",
            "checks": checks,
            "registry_files_seen": ingest["files_seen"],
            "registry_files_indexed_this_run": ingest["files_indexed"],
            "registry_indexed_files_total": stats["indexed_files"],
            "registry_records_indexed": stats["indexed_records"],
            "vocabulary_size": stats["vocabulary_size"],
            "semantic_search_hits": len(hits),
            "predictive_token_suggestions": len(suggestions),
            "predictive_phrase_suggestions": len(phrases),
            "information_gain_status": question.get("status") if isinstance(question, dict) else None,
            "recovered_at_origin_count": len(spiral["recovered_at_origin"]),
            "spiral_generation_in": 1,
            "spiral_generation_out": op.get("generation") if op else None,
            "origin_state_changed": checks["origin_state_changed"],
            "source_mutated": False,
            "aura_predictive_label_authority": False,
            "elapsed_seconds": round(time.time() - started, 6),
            "claim_ceiling": "REFERENCE_RUNTIME_PASS_NOT_SCIENTIFIC_TRUTH",
        })
    except Exception as exc:
        receipt.update({
            "status": "REJECT_RUNTIME_EXCEPTION",
            "errors": [str(exc)],
            "exception_type": type(exc).__name__,
            "traceback_tail": traceback.format_exc().splitlines()[-12:],
            "elapsed_seconds": round(time.time() - started, 6),
        })
    finally:
        out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if str(receipt["status"]).startswith("PASS_") else 3


if __name__ == "__main__":
    raise SystemExit(main())
