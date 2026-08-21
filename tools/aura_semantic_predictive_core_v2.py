#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_𓀀-𓿿]+", re.UNICODE)
TOKEN_MIN = 2
DEFAULT_STREAM_THRESHOLD = 16 * 1024 * 1024
DEFAULT_BATCH = 512
UTF8_BOM = b"\xef\xbb\xbf"
STOP = {
    "the", "and", "for", "with", "from", "that", "this", "или", "это", "как", "для", "что",
    "она", "они", "его", "ему", "наш", "наша", "через", "при", "без", "будет", "быть", "так",
    "який", "яка", "для", "через", "але", "або", "цей", "ця", "це"
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tokens(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text) if len(t) >= TOKEN_MIN]


def flatten_scalars(value: Any, *, prefix: str = "$", max_fields: int = 256, max_text: int = 65536) -> str:
    parts: list[str] = []
    stack: list[tuple[str, Any]] = [(prefix, value)]
    while stack and len(parts) < max_fields:
        path, item = stack.pop()
        if item is None:
            continue
        if isinstance(item, dict):
            for key, child in reversed(list(item.items())):
                stack.append((f"{path}.{key}", child))
        elif isinstance(item, list):
            for i, child in reversed(list(enumerate(item[:max_fields]))):
                stack.append((f"{path}[{i}]", child))
        elif isinstance(item, (str, int, float, bool)):
            s = str(item).strip()
            if s:
                parts.append(f"{path}={s}")
        if sum(len(x) for x in parts) >= max_text:
            break
    return " | ".join(parts)[:max_text]


def first_nonspace(path: Path) -> str:
    with path.open("rb") as f:
        prefix = f.read(3)
        if prefix != UTF8_BOM:
            f.seek(0)
        while True:
            b = f.read(1)
            if not b:
                return ""
            c = b.decode("utf-8", errors="ignore")
            if c and not c.isspace():
                return c


def iter_json_records(path: Path, *, stream_threshold: int = DEFAULT_STREAM_THRESHOLD) -> Iterator[tuple[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        with path.open("r", encoding="utf-8-sig") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                yield f"$line[{line_no}]", json.loads(line)
        return

    size = path.stat().st_size
    if size <= stream_threshold:
        with path.open("r", encoding="utf-8-sig") as f:
            root = json.load(f)
        if isinstance(root, list):
            for i, item in enumerate(root):
                yield f"$[{i}]", item
        elif isinstance(root, dict):
            # Split top-level objects so large registry artifacts become addressable records.
            for key, item in root.items():
                yield f"$.{key}", {key: item}
        else:
            yield "$", root
        return

    try:
        import ijson  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "OVERSIZED_JSON_REQUIRES_IJSON_OR_JSONL: install requirements-aura-intelligence.txt"
        ) from exc

    lead = first_nonspace(path)
    with path.open("rb") as f:
        prefix = f.read(3)
        if prefix != UTF8_BOM:
            f.seek(0)
        if lead == "[":
            for i, item in enumerate(ijson.items(f, "item")):
                yield f"$[{i}]", item
        elif lead == "{":
            for key, item in ijson.kvitems(f, ""):
                yield f"$.{key}", {key: item}
        else:
            raise ValueError("UNSUPPORTED_JSON_ROOT")


class AuraIndex:
    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS file_cache(
              source_path TEXT PRIMARY KEY,
              size_bytes INTEGER NOT NULL,
              mtime_ns INTEGER NOT NULL,
              sha256 TEXT NOT NULL,
              records INTEGER NOT NULL,
              indexed_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS docs(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_path TEXT NOT NULL,
              json_path TEXT NOT NULL,
              text TEXT NOT NULL,
              content_hash TEXT NOT NULL UNIQUE
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
              text,
              source_path UNINDEXED,
              json_path UNINDEXED,
              content_hash UNINDEXED,
              tokenize='unicode61 remove_diacritics 2'
            );
            CREATE TABLE IF NOT EXISTS ngrams(
              source_path TEXT NOT NULL,
              n INTEGER NOT NULL,
              context TEXT NOT NULL,
              token TEXT NOT NULL,
              count INTEGER NOT NULL,
              PRIMARY KEY(source_path,n,context,token)
            );
            CREATE INDEX IF NOT EXISTS idx_ngrams_lookup ON ngrams(n,context,token);
            CREATE TABLE IF NOT EXISTS vocab(
              source_path TEXT NOT NULL,
              token TEXT NOT NULL,
              count INTEGER NOT NULL,
              PRIMARY KEY(source_path,token)
            );
            CREATE INDEX IF NOT EXISTS idx_vocab_token ON vocab(token);
            CREATE TABLE IF NOT EXISTS forecasts(
              forecast_id TEXT PRIMARY KEY,
              task_key TEXT NOT NULL,
              created_at REAL NOT NULL,
              horizon TEXT,
              features_hash TEXT NOT NULL,
              probability REAL NOT NULL,
              model_version TEXT NOT NULL,
              status TEXT NOT NULL,
              outcome INTEGER,
              resolved_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_forecasts_task ON forecasts(task_key,status);
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def _drop_source(self, source_path: str) -> None:
        rows = self.db.execute("SELECT content_hash FROM docs WHERE source_path=?", (source_path,)).fetchall()
        for row in rows:
            self.db.execute("DELETE FROM docs_fts WHERE content_hash=?", (row["content_hash"],))
        self.db.execute("DELETE FROM docs WHERE source_path=?", (source_path,))
        self.db.execute("DELETE FROM ngrams WHERE source_path=?", (source_path,))
        self.db.execute("DELETE FROM vocab WHERE source_path=?", (source_path,))
        self.db.execute("DELETE FROM file_cache WHERE source_path=?", (source_path,))

    def _flush_language_counts(self, source_path: str, vocab: Counter[str], ng: Counter[tuple[int, str, str]]) -> None:
        if vocab:
            self.db.executemany(
                "INSERT INTO vocab(source_path,token,count) VALUES(?,?,?) "
                "ON CONFLICT(source_path,token) DO UPDATE SET count=count+excluded.count",
                [(source_path, token, count) for token, count in vocab.items()],
            )
        if ng:
            self.db.executemany(
                "INSERT INTO ngrams(source_path,n,context,token,count) VALUES(?,?,?,?,?) "
                "ON CONFLICT(source_path,n,context,token) DO UPDATE SET count=count+excluded.count",
                [(source_path, n, context, token, count) for (n, context, token), count in ng.items()],
            )

    def ingest_file(self, path: Path, *, stream_threshold: int = DEFAULT_STREAM_THRESHOLD, force: bool = False) -> dict[str, Any]:
        path = path.resolve()
        stat = path.stat()
        source_path = str(path)
        cached = self.db.execute("SELECT * FROM file_cache WHERE source_path=?", (source_path,)).fetchone()
        if cached and not force and cached["size_bytes"] == stat.st_size and cached["mtime_ns"] == stat.st_mtime_ns:
            return {"source_path": source_path, "status": "UNCHANGED_SKIPPED", "records": cached["records"]}

        file_hash = sha256_file(path)
        if cached and not force and cached["sha256"] == file_hash:
            self.db.execute(
                "UPDATE file_cache SET size_bytes=?,mtime_ns=?,indexed_at=? WHERE source_path=?",
                (stat.st_size, stat.st_mtime_ns, time.time(), source_path),
            )
            self.db.commit()
            return {"source_path": source_path, "status": "CONTENT_UNCHANGED_SKIPPED", "records": cached["records"]}

        self._drop_source(source_path)
        vocab_counts: Counter[str] = Counter()
        ngram_counts: Counter[tuple[int, str, str]] = Counter()
        records = 0
        inserted = 0

        for json_path, value in iter_json_records(path, stream_threshold=stream_threshold):
            text = flatten_scalars(value)
            if not text:
                continue
            record_hash = sha256_json({"source_path": source_path, "json_path": json_path, "text": text})
            try:
                cur = self.db.execute(
                    "INSERT INTO docs(source_path,json_path,text,content_hash) VALUES(?,?,?,?)",
                    (source_path, json_path, text, record_hash),
                )
            except sqlite3.IntegrityError:
                continue
            self.db.execute(
                "INSERT INTO docs_fts(rowid,text,source_path,json_path,content_hash) VALUES(?,?,?,?,?)",
                (cur.lastrowid, text, source_path, json_path, record_hash),
            )
            toks = tokens(text)
            vocab_counts.update(toks)
            for n in range(1, 5):
                if len(toks) < n:
                    continue
                context_len = n - 1
                for i in range(context_len, len(toks)):
                    context = "\u001f".join(toks[i-context_len:i]) if context_len else ""
                    ngram_counts[(n, context, toks[i])] += 1
            records += 1
            inserted += 1
            if records % DEFAULT_BATCH == 0:
                self._flush_language_counts(source_path, vocab_counts, ngram_counts)
                vocab_counts.clear()
                ngram_counts.clear()
                self.db.commit()

        self._flush_language_counts(source_path, vocab_counts, ngram_counts)
        self.db.execute(
            "INSERT OR REPLACE INTO file_cache(source_path,size_bytes,mtime_ns,sha256,records,indexed_at) VALUES(?,?,?,?,?,?)",
            (source_path, stat.st_size, stat.st_mtime_ns, file_hash, records, time.time()),
        )
        self.db.commit()
        return {"source_path": source_path, "status": "INDEXED", "records": records, "inserted": inserted, "sha256": file_hash}

    def ingest_paths(self, paths: Iterable[Path], *, stream_threshold: int = DEFAULT_STREAM_THRESHOLD, force: bool = False) -> dict[str, Any]:
        files: list[Path] = []
        for root in paths:
            root = root.expanduser()
            if root.is_dir():
                files.extend(sorted(p for p in root.rglob("*") if p.suffix.lower() in {".json", ".jsonl", ".ndjson"}))
            elif root.is_file():
                files.append(root)
        results = [self.ingest_file(p, stream_threshold=stream_threshold, force=force) for p in files]
        return {
            "schema": "janus.aura.registry_ingest.receipt.v2",
            "files_seen": len(files),
            "files_indexed": sum(r["status"] == "INDEXED" for r in results),
            "records_indexed": sum(int(r.get("records", 0)) for r in results if r["status"] == "INDEXED"),
            "results": results,
            "index_is_source_of_truth": False,
            "registry_write_performed": False,
        }

    def semantic_search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        qtokens = [t for t in tokens(query) if t not in STOP][:16]
        if not qtokens:
            return []
        match = " OR ".join(f'"{t.replace(chr(34), "")}"' for t in qtokens)
        rows = self.db.execute(
            "SELECT source_path,json_path,text,content_hash,bm25(docs_fts) AS rank "
            "FROM docs_fts WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, int(limit)),
        ).fetchall()
        qset = set(qtokens)
        out = []
        for row in rows:
            dset = set(tokens(row["text"]))
            overlap = len(qset & dset) / max(1, len(qset))
            out.append({
                "source_path": row["source_path"],
                "json_path": row["json_path"],
                "content_hash": row["content_hash"],
                "bm25": float(row["rank"]),
                "query_overlap": round(overlap, 6),
                "excerpt": row["text"][:1200],
                "evidence_authority": False,
            })
        return out

    def autocomplete(self, text: str, limit: int = 8) -> list[dict[str, Any]]:
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
            like = f"{prefix}%"
            rows = self.db.execute(
                "SELECT token,SUM(count) AS c FROM ngrams WHERE n=? AND context=? AND token LIKE ? "
                "GROUP BY token ORDER BY c DESC LIMIT ?",
                (n, context, like, int(limit * 3)),
            ).fetchall()
            for row in rows:
                tok = row["token"]
                score = math.log1p(float(row["c"])) + ctx_len * 1.25 + (0.5 if prefix else 0.0)
                if score > candidates.get(tok, -1e9):
                    candidates[tok] = score
                    reasons[tok] = f"{n}-gram context"

        if prefix:
            rows = self.db.execute(
                "SELECT token,SUM(count) AS c FROM vocab WHERE token LIKE ? GROUP BY token ORDER BY c DESC LIMIT ?",
                (f"{prefix}%", int(limit * 3)),
            ).fetchall()
            for row in rows:
                tok = row["token"]
                score = math.log1p(float(row["c"])) + 0.25
                if score > candidates.get(tok, -1e9):
                    candidates[tok] = score
                    reasons[tok] = "prefix vocabulary"

        ranked = sorted(candidates.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        return [
            {"suggestion": tok, "score": round(score, 6), "reason": reasons[tok], "auto_execute": False}
            for tok, score in ranked
        ]

    def registry_discriminator(self, query: str, limit: int = 8) -> dict[str, Any]:
        hits = self.semantic_search(query, limit=limit)
        if len(hits) < 2:
            return {"status": "INSUFFICIENT_CANDIDATES", "question": None, "candidates": hits}
        qset = set(tokens(query))
        doc_terms: list[set[str]] = []
        counts: Counter[str] = Counter()
        for hit in hits:
            terms = {t for t in tokens(hit["excerpt"]) if t not in STOP and t not in qset and len(t) >= 4}
            doc_terms.append(terms)
            counts.update(terms)
        n = len(hits)
        best = None
        for term, yes_n in counts.items():
            if yes_n == 0 or yes_n == n:
                continue
            p = yes_n / n
            # For deterministic presence/absence splits, maximum information gain is the split entropy.
            ig = -(p * math.log2(p) + (1-p) * math.log2(1-p))
            candidate = (ig, -abs(p - 0.5), term, yes_n)
            if best is None or candidate > best:
                best = candidate
        if best is None:
            return {"status": "NO_DISCRIMINATING_FEATURE", "question": None, "candidates": hits}
        ig, _, term, yes_n = best
        return {
            "status": "QUESTION_READY",
            "question": f"Связана ли искомая гипотеза с признаком «{term}»?",
            "feature": term,
            "information_gain_bits": round(float(ig), 6),
            "partition": {"yes": yes_n, "no": n - yes_n, "total": n},
            "candidates": [{"source_path": h["source_path"], "json_path": h["json_path"], "content_hash": h["content_hash"]} for h in hits],
            "question_is_truth": False,
        }

    def forecast_prior(self, task_key: str) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT probability,outcome FROM forecasts WHERE task_key=? AND status='RESOLVED' AND outcome IS NOT NULL",
            (task_key,),
        ).fetchall()
        success = sum(int(r["outcome"]) for r in rows)
        total = len(rows)
        posterior = (success + 1) / (total + 2)
        brier = None
        log_loss = None
        if rows:
            brier = sum((float(r["probability"]) - int(r["outcome"])) ** 2 for r in rows) / total
            eps = 1e-12
            log_loss = -sum(
                int(r["outcome"]) * math.log(max(eps, float(r["probability"]))) +
                (1-int(r["outcome"])) * math.log(max(eps, 1-float(r["probability"])))
                for r in rows
            ) / total
        return {
            "task_key": task_key,
            "resolved_count": total,
            "beta_prior": {"alpha": success + 1, "beta": total - success + 1},
            "empirical_probability": round(posterior, 6),
            "brier": None if brier is None else round(brier, 6),
            "log_loss": None if log_loss is None else round(log_loss, 6),
            "world_truth_authority": False,
        }

    def open_forecast(self, task_key: str, probability: float, horizon: str, features: Any, model_version: str = "AURA_V2") -> dict[str, Any]:
        if not (0.0 <= probability <= 1.0):
            raise ValueError("PROBABILITY_MUST_BE_0_TO_1")
        fid = f"aura-fc-{uuid.uuid4().hex}"
        features_hash = sha256_json(features)
        self.db.execute(
            "INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?,?,?)",
            (fid, task_key, time.time(), horizon, features_hash, probability, model_version, "OPEN", None, None),
        )
        self.db.commit()
        return {
            "forecast_id": fid,
            "task_key": task_key,
            "probability": probability,
            "horizon": horizon,
            "features_hash": features_hash,
            "status": "OPEN",
            "self_resolution_allowed": False,
        }

    def resolve_forecast(self, forecast_id: str, outcome: int, *, resolver: str) -> dict[str, Any]:
        if outcome not in {0, 1}:
            raise ValueError("OUTCOME_MUST_BE_0_OR_1")
        if resolver.upper().startswith("AURA"):
            raise ValueError("AURA_SELF_RESOLUTION_REJECT")
        row = self.db.execute("SELECT * FROM forecasts WHERE forecast_id=?", (forecast_id,)).fetchone()
        if row is None:
            raise ValueError("FORECAST_NOT_FOUND")
        if row["status"] != "OPEN":
            raise ValueError("FORECAST_ALREADY_RESOLVED")
        self.db.execute(
            "UPDATE forecasts SET status='RESOLVED',outcome=?,resolved_at=? WHERE forecast_id=?",
            (outcome, time.time(), forecast_id),
        )
        self.db.commit()
        return {
            "forecast_id": forecast_id,
            "status": "RESOLVED",
            "outcome": outcome,
            "resolver": resolver,
            "brier": round((float(row["probability"]) - outcome) ** 2, 6),
        }

    def stats(self) -> dict[str, Any]:
        docs = self.db.execute("SELECT COUNT(*) AS c FROM docs").fetchone()["c"]
        files = self.db.execute("SELECT COUNT(*) AS c FROM file_cache").fetchone()["c"]
        vocab = self.db.execute("SELECT COUNT(DISTINCT token) AS c FROM vocab").fetchone()["c"]
        forecasts = self.db.execute("SELECT COUNT(*) AS c FROM forecasts").fetchone()["c"]
        return {
            "schema": "janus.aura.intelligence.stats.v2",
            "indexed_files": files,
            "indexed_records": docs,
            "vocabulary_size": vocab,
            "forecast_records": forecasts,
            "primary_storage": "SQLite/WAL",
            "index_is_source_of_truth": False,
        }


def entropy(weights: list[float]) -> float:
    s = sum(weights)
    if s <= 0:
        return 0.0
    out = 0.0
    for w in weights:
        if w <= 0:
            continue
        p = w / s
        out -= p * math.log2(p)
    return out


def choose_question(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if len(candidates) < 2:
        return {"status": "INSUFFICIENT_CANDIDATES"}
    features = sorted({k for c in candidates for k in (c.get("features") or {}).keys()})
    weights = [max(0.0, float(c.get("weight", 1.0))) for c in candidates]
    h0 = entropy(weights)
    best: tuple[float, str, float] | None = None
    for feature in features:
        yes_weights = []
        no_weights = []
        p_yes_total = 0.0
        total_w = sum(weights) or 1.0
        for c, w in zip(candidates, weights):
            p = float((c.get("features") or {}).get(feature, 0.5))
            p = min(1.0, max(0.0, p))
            yes_weights.append(w * p)
            no_weights.append(w * (1-p))
            p_yes_total += w * p
        p_yes = p_yes_total / total_w
        expected = p_yes * entropy(yes_weights) + (1-p_yes) * entropy(no_weights)
        gain = h0 - expected
        cand = (gain, feature, p_yes)
        if best is None or cand > best:
            best = cand
    if best is None:
        return {"status": "NO_QUESTION"}
    gain, feature, p_yes = best
    return {
        "status": "QUESTION_READY",
        "feature": feature,
        "question": f"Верно ли свойство «{feature}»?",
        "information_gain_bits": round(gain, 6),
        "predicted_yes_probability": round(p_yes, 6),
        "proprietary_akinator_code_used": False,
    }


def update_candidates(candidates: list[dict[str, Any]], feature: str, answer: str) -> list[dict[str, Any]]:
    answer = answer.upper()
    answer_target = {"YES": 0.98, "PROBABLY": 0.75, "UNKNOWN": 0.5, "PROBABLY_NOT": 0.25, "NO": 0.02}
    if answer not in answer_target:
        raise ValueError("ANSWER_MUST_BE_YES_NO_PROBABLY_PROBABLY_NOT_UNKNOWN")
    target = answer_target[answer]
    updated = []
    for c in candidates:
        p = float((c.get("features") or {}).get(feature, 0.5))
        likelihood = p * target + (1-p) * (1-target)
        x = dict(c)
        x["weight"] = max(1e-12, float(c.get("weight", 1.0)) * likelihood)
        updated.append(x)
    total = sum(float(c["weight"]) for c in updated) or 1.0
    for c in updated:
        c["weight"] = float(c["weight"]) / total
    return sorted(updated, key=lambda c: -float(c["weight"]))


def parse_json_arg(value: str) -> Any:
    p = Path(value)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    return json.loads(value)


def main() -> int:
    ap = argparse.ArgumentParser(description="Aura semantic/predictive local core v2")
    ap.add_argument("--db", default=os.environ.get("AURA_INTELLIGENCE_DB", "state/aura_intelligence.sqlite3"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest")
    p.add_argument("paths", nargs="+")
    p.add_argument("--stream-threshold", type=int, default=DEFAULT_STREAM_THRESHOLD)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--limit", type=int, default=8)
    p = sub.add_parser("suggest"); p.add_argument("text"); p.add_argument("--limit", type=int, default=8)
    p = sub.add_parser("registry-question"); p.add_argument("query"); p.add_argument("--limit", type=int, default=8)
    p = sub.add_parser("question"); p.add_argument("candidates_json")
    p = sub.add_parser("answer"); p.add_argument("candidates_json"); p.add_argument("feature"); p.add_argument("answer")
    p = sub.add_parser("forecast-prior"); p.add_argument("task_key")
    p = sub.add_parser("forecast-open"); p.add_argument("task_key"); p.add_argument("probability", type=float); p.add_argument("horizon"); p.add_argument("features_json")
    p = sub.add_parser("forecast-resolve"); p.add_argument("forecast_id"); p.add_argument("outcome", type=int); p.add_argument("--resolver", required=True)
    sub.add_parser("stats")

    args = ap.parse_args()
    idx = AuraIndex(args.db)
    try:
        if args.cmd == "ingest":
            out = idx.ingest_paths([Path(x) for x in args.paths], stream_threshold=args.stream_threshold, force=args.force)
        elif args.cmd == "search": out = idx.semantic_search(args.query, args.limit)
        elif args.cmd == "suggest": out = idx.autocomplete(args.text, args.limit)
        elif args.cmd == "registry-question": out = idx.registry_discriminator(args.query, args.limit)
        elif args.cmd == "question": out = choose_question(parse_json_arg(args.candidates_json))
        elif args.cmd == "answer": out = update_candidates(parse_json_arg(args.candidates_json), args.feature, args.answer)
        elif args.cmd == "forecast-prior": out = idx.forecast_prior(args.task_key)
        elif args.cmd == "forecast-open": out = idx.open_forecast(args.task_key, args.probability, args.horizon, parse_json_arg(args.features_json))
        elif args.cmd == "forecast-resolve": out = idx.resolve_forecast(args.forecast_id, args.outcome, resolver=args.resolver)
        elif args.cmd == "stats": out = idx.stats()
        else: raise AssertionError(args.cmd)
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        idx.close()


if __name__ == "__main__":
    raise SystemExit(main())
