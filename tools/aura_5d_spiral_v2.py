#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from aura_semantic_predictive_core_v2 import AuraIndex, canonical_bytes, sha256_json, tokens

SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")
LATE_SCOPE = re.compile(r"\b(но|однако|обязательно|главное|важно|только|кроме|при этом|yet|but|must|important|only)\b", re.I)
QUESTION_RE = re.compile(r"[?？]$")
CONTRAST_RE = re.compile(r"\b(но|однако|вместо|против|versus|vs|but|however|instead)\b", re.I)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def split_segments(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_RE.split(text) if p.strip()]
    return parts or [text.strip()]


def base_graph(text: str) -> dict[str, Any]:
    segments = split_segments(text)
    nodes = []
    edges = []
    order = []
    for i, seg in enumerate(segments, 1):
        nid = f"S{i:04d}"
        order.append(nid)
        nodes.append({
            "id": nid,
            "kind": "SOURCE_SEGMENT",
            "label": seg,
            "origin": "USER_OR_EXTERNAL_TRIGGER",
            "source_segment_ids": [nid],
            "validation_status": "SOURCE",
        })
        if i > 1:
            edges.append({"source": f"S{i-1:04d}", "target": nid, "kind": "FORWARD_SEQUENCE"})
    return {"nodes": nodes, "edges": edges, "logical_order": order}


def add_node(graph: dict[str, Any], node: dict[str, Any]) -> None:
    ids = {n["id"] for n in graph["nodes"]}
    if node["id"] in ids:
        raise ValueError(f"DUPLICATE_NODE:{node['id']}")
    graph["nodes"].append(node)


def apply_patch(graph: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    op = patch["op"]
    order = graph["logical_order"]
    node = dict(patch.get("node") or {})
    if op in {"INSERT_BEFORE", "INSERT_AFTER", "INSERT_CHILD", "INSERT_SIBLING", "SPLICE_BETWEEN", "FORK_BRANCH", "PROMOTE_TO_ABSTRACTION", "DEMOTE_TO_INSTANCE"}:
        if not node.get("id"):
            raise ValueError("PATCH_NODE_ID_REQUIRED")
        node.setdefault("kind", "INFERRED")
        node.setdefault("origin", "AURA_5D_PATCH")
        node.setdefault("validation_status", "HYPOTHESIS")
        add_node(graph, node)

    if op == "INSERT_BEFORE":
        anchor = patch["anchor_id"]
        order.insert(order.index(anchor), node["id"])
    elif op == "INSERT_AFTER":
        anchor = patch["anchor_id"]
        order.insert(order.index(anchor) + 1, node["id"])
    elif op == "SPLICE_BETWEEN":
        left, right = patch["left_id"], patch["right_id"]
        li, ri = order.index(left), order.index(right)
        if ri != li + 1:
            raise ValueError("SPLICE_REQUIRES_ADJACENT_LOGICAL_NODES")
        order.insert(ri, node["id"])
        graph["edges"] = [e for e in graph["edges"] if not (e["source"] == left and e["target"] == right and e["kind"] == "FORWARD_SEQUENCE")]
        graph["edges"].append({"source": left, "target": node["id"], "kind": "SPLICE_FORWARD"})
        graph["edges"].append({"source": node["id"], "target": right, "kind": "SPLICE_FORWARD"})
    elif op in {"INSERT_CHILD", "FORK_BRANCH"}:
        anchor = patch["anchor_id"]
        graph["edges"].append({"source": anchor, "target": node["id"], "kind": "CHILD" if op == "INSERT_CHILD" else "FORK"})
    elif op == "INSERT_SIBLING":
        anchor = patch["anchor_id"]
        idx = order.index(anchor) + 1
        order.insert(idx, node["id"])
        graph["edges"].append({"source": anchor, "target": node["id"], "kind": "SIBLING_RELATION"})
    elif op == "LINK_DISTANT_NODES":
        graph["edges"].append({"source": patch["source_id"], "target": patch["target_id"], "kind": patch.get("edge_kind", "DISTANT_RELATION")})
    elif op in {"PROMOTE_TO_ABSTRACTION", "DEMOTE_TO_INSTANCE"}:
        anchor = patch["anchor_id"]
        graph["edges"].append({"source": anchor, "target": node["id"], "kind": op})
    elif op == "ANNOTATE_NODE":
        target = patch["node_id"]
        for n in graph["nodes"]:
            if n["id"] == target:
                n.setdefault("annotations", []).append(patch["annotation"])
                break
        else:
            raise ValueError("ANNOTATE_NODE_TARGET_NOT_FOUND")
    elif op == "ANNOTATE_EDGE":
        source, target = patch["source_id"], patch["target_id"]
        for e in graph["edges"]:
            if e["source"] == source and e["target"] == target:
                e.setdefault("annotations", []).append(patch["annotation"])
                break
        else:
            raise ValueError("ANNOTATE_EDGE_TARGET_NOT_FOUND")
    else:
        raise ValueError(f"UNKNOWN_PATCH_OP:{op}")
    return graph


def structural_projection(graph: dict[str, Any]) -> dict[str, Any]:
    term_counts = Counter()
    for n in graph["nodes"]:
        if n["kind"] == "SOURCE_SEGMENT":
            term_counts.update(tokens(n["label"]))
    repeats = [t for t, c in term_counts.most_common(20) if c >= 2]
    return {
        "schema": "janus.demihead.hemisphere_packet.v3-compatible-projection",
        "hemisphere": "LEFT_HRAIN",
        "role": "STRUCTURAL_CONTEXT",
        "graph": graph,
        "structural_signals": {"repeated_terms": repeats, "node_count": len(graph["nodes"]), "edge_count": len(graph["edges"])},
        "control": {"read_only_transfer": True, "direct_cross_hemisphere_mutation": False, "authority_delta": 0, "mass_effect_budget_delta": 0},
    }


def reverse_recoveries(text: str, graph: dict[str, Any]) -> list[dict[str, Any]]:
    source_nodes = [n for n in graph["nodes"] if n["kind"] == "SOURCE_SEGMENT"]
    recovered = []
    for node in reversed(source_nodes):
        if LATE_SCOPE.search(node["label"]) and node["id"] != "S0001":
            recovered.append({
                "kind": "BACKWARD_SCOPE",
                "finding": f"Late constraint at {node['id']} may scope earlier segments and must be reconsidered at origin.",
                "source_segment_ids": ["S0001", node["id"]],
                "confidence": "MEDIUM",
            })
        if CONTRAST_RE.search(node["label"]):
            recovered.append({
                "kind": "CONTRAST_BACKPROPAGATION",
                "finding": f"Contrast in {node['id']} creates an alternative interpretation for prior context.",
                "source_segment_ids": [node["id"]],
                "confidence": "MEDIUM",
            })
        if QUESTION_RE.search(node["label"]):
            recovered.append({
                "kind": "QUESTION_TARGET",
                "finding": f"Terminal question at {node['id']} defines what earlier context should be selected as relevant evidence/context.",
                "source_segment_ids": [node["id"]],
                "confidence": "HIGH",
            })
    seen = set()
    out = []
    for r in recovered:
        key = (r["kind"], tuple(r["source_segment_ids"]))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def run(payload: dict[str, Any], *, db_path: str | Path | None = None, patches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text = str(payload.get("text") or payload.get("trigger_text") or "").strip()
    if not text:
        raise ValueError("TEXT_REQUIRED")
    generation = int(payload.get("generation", 1))
    origin = {
        "generation": generation,
        "text_sha256": sha256_json(text),
        "intent_id": payload.get("intent_id"),
        "source_ref": payload.get("source_ref") or payload.get("source"),
    }
    origin_state_hash = digest(origin)
    graph = base_graph(text)
    recovered = reverse_recoveries(text, graph)
    applied = []

    # RECOVERED_AT_ORIGIN belongs before the source origin. It must not break the
    # original S0001 -> S0002 adjacency needed by later non-tail reasoning patches.
    # Insert in reverse order so rendered order matches the recovery list.
    for i, finding in reversed(list(enumerate(recovered, 1))):
        anchors = finding["source_segment_ids"]
        nid = f"R{i:04d}"
        node = {
            "id": nid,
            "kind": "RECOVERED_AT_ORIGIN",
            "label": finding["finding"],
            "origin": "D2_REVERSE",
            "source_segment_ids": anchors,
            "confidence": finding["confidence"],
            "validation_status": "SUPPORTED_INFERENCE_NOT_WORLD_TRUTH",
        }
        patch = {"op": "INSERT_BEFORE", "anchor_id": "S0001", "node": node, "reason": finding["kind"]}
        apply_patch(graph, patch)
        applied.append(patch)

    if patches:
        for patch in patches:
            apply_patch(graph, patch)
            applied.append(patch)

    semantic_hits = []
    autocomplete = []
    registry_question = None
    if db_path and Path(db_path).exists():
        idx = AuraIndex(db_path)
        try:
            semantic_hits = idx.semantic_search(text, 6)
            autocomplete = idx.autocomplete(text, 6)
            registry_question = idx.registry_discriminator(text, 6)
        finally:
            idx.close()

    inaihr_graph = {
        "nodes": [
            {"id": f"A{i:04d}", "label": h["excerpt"][:500], "origin": "AURA_REGISTRY_SEMANTIC_RETRIEVAL", "source_ref": f"{h['source_path']}#{h['json_path']}"}
            for i, h in enumerate(semantic_hits, 1)
        ],
        "links": [],
    }
    for i in range(1, len(inaihr_graph["nodes"])):
        inaihr_graph["links"].append({"source": inaihr_graph["nodes"][0]["id"], "target": inaihr_graph["nodes"][i]["id"]})

    structural = structural_projection(graph)
    associative = {
        "schema": "janus.demihead.hemisphere_packet.v3-compatible-projection",
        "hemisphere": "RIGHT_INAIHR",
        "role": "ASSOCIATIVE_CONTEXT",
        "graph": inaihr_graph,
        "semantic_hits": semantic_hits,
        "control": {"read_only_transfer": True, "direct_cross_hemisphere_mutation": False, "authority_delta": 0, "mass_effect_budget_delta": 0},
        "association_is_evidence": False,
    }
    state_delta = {
        "recovered_at_origin": recovered,
        "semantic_candidate_count": len(semantic_hits),
        "non_tail_patch_count": len(applied),
        "autocomplete": autocomplete,
        "registry_question": registry_question,
    }
    delta_hash = digest(state_delta)
    advanced = bool(recovered or semantic_hits or applied)
    origin_prime = None
    if advanced:
        origin_prime = {
            "generation": generation + 1,
            "parent_origin_state_hash": origin_state_hash,
            "state_delta_sha256": delta_hash,
            "graph_sha256": digest(graph),
            "rule": "POSITION_MAY_REPEAT_BUT_STATE_MUST_ADVANCE",
        }
        origin_prime["origin_prime_state_hash"] = digest(origin_prime)

    return {
        "schema": "janus.aura.spiral_5d.analysis.v2",
        "analysis_mode": "SPIRAL_5D",
        "origin_n": origin,
        "origin_state_hash": origin_state_hash,
        "recovered_at_origin": recovered,
        "axes": {
            "D1_FORWARD": {"segment_order": [n["id"] for n in graph["nodes"] if n["kind"] == "SOURCE_SEGMENT"]},
            "D2_REVERSE": {"recovered_count": len(recovered), "findings": recovered},
            "D3_HRAIN_STRUCTURAL": structural,
            "D4_INAIHR_ASSOCIATIVE": associative,
            "D5_SPIRAL_ABSTRACTION": {"state_delta_sha256": delta_hash, "advanced": advanced, "origin_prime": origin_prime},
        },
        "graph": graph,
        "patch_receipts": applied,
        "predictive_input": {"suggestions": autocomplete, "auto_execute": False},
        "information_gain": registry_question,
        "demihead": {
            "automatic_merge": False,
            "agreement_is_truth": False,
            "disagreement_is_error": False,
            "requires_same_intent": True,
        },
        "spiral_status": "ADVANCED_TO_ORIGIN_PRIME" if advanced else "HOLD_STALL_NO_STATE_DELTA",
        "integrity": {
            "source_text_mutated": False,
            "source_text_sha256": sha256_json(text),
            "graph_sha256": digest(graph),
            "raw_private_chain_of_thought_stored": False,
        },
        "claim_ceiling": "STRUCTURED_REASONING_GRAPH_AND_SEARCH_PRIORS_NOT_WORLD_TRUTH",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Aura Oracle 5D JANUS spiral adapter v2")
    ap.add_argument("input_json")
    ap.add_argument("--db", default=os.environ.get("AURA_INTELLIGENCE_DB"))
    ap.add_argument("--patch")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    patches = json.loads(Path(args.patch).read_text(encoding="utf-8")) if args.patch else None
    out = run(payload, db_path=args.db, patches=patches)
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        import sys
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
