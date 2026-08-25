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
from aura_semantic_predictive_core_v2 import AuraIndex, sha256_file


_PARSE_ERROR_TYPES = {
    "JSONDecodeError",
    "IncompleteJSONError",
    "UnexpectedSymbol",
    "UnicodeDecodeError",
}


def _registry_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".ndjson"}
    )


def _resilient_ingest(idx: AuraIndex, root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    files = _registry_files(root)
    results: list[dict[str, object]] = []
    quarantine: list[dict[str, object]] = []

    for path in files:
        try:
            results.append(idx.ingest_file(path, force=False))
        except Exception as exc:
            # Quarantine malformed source records, but never swallow unrelated runtime faults.
            if type(exc).__name__ not in _PARSE_ERROR_TYPES and not isinstance(exc, ValueError):
                raise
            source_path = str(path.resolve())
            # A streaming parser may have inserted a prefix before discovering corruption.
            # Remove that partial local index state; the source registry itself remains read-only.
            idx._drop_source(source_path)
            idx.db.commit()
            quarantine.append({
                "source_path": source_path,
                "status": "QUARANTINED_INVALID_JSON",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "sha256": sha256_file(path),
                "registry_write_performed": False,
            })

    ingest: dict[str, object] = {
        "schema": "janus.aura.registry_ingest.receipt.v2-resilient",
        "files_seen": len(files),
        "files_indexed": sum(r.get("status") == "INDEXED" for r in results),
        "records_indexed": sum(int(r.get("records", 0)) for r in results if r.get("status") == "INDEXED"),
        "files_quarantined": len(quarantine),
        "results": results,
        "index_is_source_of_truth": False,
        "registry_write_performed": False,
    }
    return ingest, quarantine


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed full Janus Meta Registry gate for Aura v2")
    ap.add_argument("registry_root")
    ap.add_argument("--db", default="runtime/aura_full_registry.sqlite3")
    ap.add_argument("--receipt", default="runtime/full-registry-receipt.json")
    args = ap.parse_args()

    started = time.time()
    registry_root = Path(args.registry_root).resolve()
    receipt: dict[str, object] = {
        "schema": "janus.aura.full_meta_registry.gate_receipt.v2",
        "status": "REJECT_UNFINISHED",
        "github_actor": os.environ.get("GITHUB_ACTOR"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "registry_root": str(registry_root),
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
            ingest, quarantine = _resilient_ingest(idx, registry_root)
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
        d5 = spiral["axes"]["D5_SPIRAL_ABSTRACTION"]
        candidate = d5["origin_prime_candidate"]

        checks = {
            "files_seen_positive": int(ingest["files_seen"]) > 0,
            "valid_registry_records_positive": int(stats["indexed_records"]) > 0,
            "malformed_json_isolated": int(ingest["files_quarantined"]) < int(ingest["files_seen"]),
            "semantic_hits_positive": len(hits) > 0,
            "spiral_candidate_advanced": spiral["spiral_status"] == "CANDIDATE_STATE_ADVANCE",
            "origin_prime_candidate_exists": bool(candidate),
            "origin_prime_candidate_generation_2": bool(candidate and int(candidate["generation"]) == 2),
            "origin_state_changed": bool(candidate and spiral["origin_state_hash"] != candidate["candidate_state_hash"]),
            "candidate_not_final_promotion": bool(candidate and candidate.get("promotion_status") == "CANDIDATE_NOT_VERIFIED_RETURN"),
            "final_origin_prime_authority_false": d5["final_origin_prime_authority"] is False,
            "source_immutable": spiral["integrity"]["source_text_mutated"] is False,
            "hrain_projection": spiral["axes"]["D3_HRAIN_STRUCTURAL"]["hemisphere"] == "LEFT_HRAIN",
            "inaihr_projection": spiral["axes"]["D4_INAIHR_ASSOCIATIVE"]["hemisphere"] == "RIGHT_INAIHR",
        }
        passed = all(checks.values())
        pass_status = "PASS_FULL_META_REGISTRY_REFERENCE_RUNTIME_WITH_QUARANTINE" if quarantine else "PASS_FULL_META_REGISTRY_REFERENCE_RUNTIME"
        receipt.update({
            "status": pass_status if passed else "REJECT_INVARIANT_FAILURE",
            "checks": checks,
            "registry_files_seen": ingest["files_seen"],
            "registry_files_indexed_this_run": ingest["files_indexed"],
            "registry_files_quarantined": ingest["files_quarantined"],
            "registry_indexed_files_total": stats["indexed_files"],
            "registry_records_indexed": stats["indexed_records"],
            "vocabulary_size": stats["vocabulary_size"],
            "semantic_search_hits": len(hits),
            "predictive_token_suggestions": len(suggestions),
            "predictive_phrase_suggestions": len(phrases),
            "information_gain_status": question.get("status") if isinstance(question, dict) else None,
            "recovered_at_origin_count": len(spiral["recovered_at_origin"]),
            "spiral_generation_in": 1,
            "spiral_generation_out": candidate.get("generation") if candidate else None,
            "origin_state_changed": checks["origin_state_changed"],
            "source_mutated": False,
            "aura_predictive_label_authority": False,
            "quarantine": quarantine,
            "elapsed_seconds": round(time.time() - started, 6),
            "claim_ceiling": "REFERENCE_RUNTIME_PASS_NOT_SCIENTIFIC_TRUTH_NOT_FINAL_ORIGIN_PRIME_PROMOTION",
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
