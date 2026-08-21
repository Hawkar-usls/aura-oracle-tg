#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any

from aura_semantic_predictive_core_v2 import AuraIndex, WORD_RE, tokens

USER_STYLE_SOURCE = "@USER_STYLE"


class AuraPredictiveInput:
    def __init__(self, db_path: str | Path) -> None:
        self.idx = AuraIndex(db_path)

    def close(self) -> None:
        self.idx.close()

    def learn_user_style(self, text: str) -> dict[str, Any]:
        toks = tokens(text)
        if not toks:
            return {"status": "NO_TOKENS", "raw_text_stored": False, "token_count": 0}
        vocab = Counter(toks)
        ng: Counter[tuple[int, str, str]] = Counter()
        for n in range(1, 5):
            ctx_len = n - 1
            for i in range(ctx_len, len(toks)):
                context = "\u001f".join(toks[i-ctx_len:i]) if ctx_len else ""
                ng[(n, context, toks[i])] += 1
        self.idx._flush_language_counts(USER_STYLE_SOURCE, vocab, ng)
        self.idx.db.commit()
        return {
            "status": "LEARNED_LOCAL_STYLE_COUNTS",
            "token_count": len(toks),
            "unique_tokens": len(vocab),
            "raw_text_stored": False,
            "world_predictive_head_updated": False,
            "source": USER_STYLE_SOURCE,
        }

    def suggest_tokens(self, text: str, limit: int = 8) -> list[dict[str, Any]]:
        raw = WORD_RE.findall(text.lower())
        ends_word = bool(text and WORD_RE.search(text[-1]))
        prefix = raw[-1] if raw and ends_word else ""
        context_tokens = raw[:-1] if prefix else raw
        candidates: dict[str, float] = {}
        reasons: dict[str, str] = {}

        for ctx_len in (3, 2, 1, 0):
            if len(context_tokens) < ctx_len:
                continue
            n = ctx_len + 1
            context = "\u001f".join(context_tokens[-ctx_len:]) if ctx_len else ""
            rows = self.idx.db.execute(
                "SELECT token,SUM(count * CASE WHEN source_path=? THEN 4 ELSE 1 END) AS weighted_c,"
                "SUM(CASE WHEN source_path=? THEN count ELSE 0 END) AS user_c "
                "FROM ngrams WHERE n=? AND context=? AND token LIKE ? GROUP BY token ORDER BY weighted_c DESC LIMIT ?",
                (USER_STYLE_SOURCE, USER_STYLE_SOURCE, n, context, f"{prefix}%", int(limit * 4)),
            ).fetchall()
            for row in rows:
                tok = row["token"]
                user_c = float(row["user_c"] or 0)
                score = math.log1p(float(row["weighted_c"])) + ctx_len * 1.35 + (1.0 if user_c > 0 else 0.0)
                if score > candidates.get(tok, -1e9):
                    candidates[tok] = score
                    reasons[tok] = f"{n}-gram" + (" + user-style" if user_c > 0 else "")

        if prefix:
            rows = self.idx.db.execute(
                "SELECT token,SUM(count * CASE WHEN source_path=? THEN 4 ELSE 1 END) AS weighted_c,"
                "SUM(CASE WHEN source_path=? THEN count ELSE 0 END) AS user_c "
                "FROM vocab WHERE token LIKE ? GROUP BY token ORDER BY weighted_c DESC LIMIT ?",
                (USER_STYLE_SOURCE, USER_STYLE_SOURCE, f"{prefix}%", int(limit * 4)),
            ).fetchall()
            for row in rows:
                tok = row["token"]
                user_c = float(row["user_c"] or 0)
                score = math.log1p(float(row["weighted_c"])) + (1.0 if user_c > 0 else 0.25)
                if score > candidates.get(tok, -1e9):
                    candidates[tok] = score
                    reasons[tok] = "prefix vocabulary" + (" + user-style" if user_c > 0 else "")

        ranked = sorted(candidates.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        return [
            {"suggestion": tok, "score": round(score, 6), "reason": reasons[tok], "auto_execute": False}
            for tok, score in ranked
        ]

    def suggest_phrases(self, text: str, limit: int = 5, max_new_tokens: int = 3) -> list[dict[str, Any]]:
        first = self.suggest_tokens(text, limit=max(limit, 8))
        phrases = []
        for candidate in first[:limit]:
            phrase_tokens = [candidate["suggestion"]]
            working = text
            if working and not working.endswith(" "):
                # Replace partial last token with the completed suggestion.
                match = list(WORD_RE.finditer(working))
                if match and match[-1].end() == len(working):
                    working = working[:match[-1].start()] + candidate["suggestion"] + " "
                else:
                    working += " " + candidate["suggestion"] + " "
            else:
                working += candidate["suggestion"] + " "
            for _ in range(max(0, max_new_tokens - 1)):
                nxt = self.suggest_tokens(working, limit=1)
                if not nxt:
                    break
                token = nxt[0]["suggestion"]
                if token in phrase_tokens[-2:]:
                    break
                phrase_tokens.append(token)
                working += token + " "
            phrases.append({
                "phrase": " ".join(phrase_tokens),
                "first_token_score": candidate["score"],
                "reason": candidate["reason"],
                "tap_to_accept": True,
                "auto_execute": False,
            })
        return phrases


def main() -> int:
    ap = argparse.ArgumentParser(description="Aura predictive input v2")
    ap.add_argument("--db", default=os.environ.get("AURA_INTELLIGENCE_DB", "state/aura_intelligence.sqlite3"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("learn-style"); p.add_argument("text")
    p = sub.add_parser("suggest"); p.add_argument("text"); p.add_argument("--limit", type=int, default=8)
    p = sub.add_parser("phrases"); p.add_argument("text"); p.add_argument("--limit", type=int, default=5); p.add_argument("--depth", type=int, default=3)
    args = ap.parse_args()
    pred = AuraPredictiveInput(args.db)
    try:
        if args.cmd == "learn-style": out = pred.learn_user_style(args.text)
        elif args.cmd == "suggest": out = pred.suggest_tokens(args.text, args.limit)
        else: out = pred.suggest_phrases(args.text, args.limit, args.depth)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    finally:
        pred.close()


if __name__ == "__main__":
    raise SystemExit(main())
