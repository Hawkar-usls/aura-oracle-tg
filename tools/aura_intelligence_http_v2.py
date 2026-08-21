#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from aura_5d_spiral_v2 import run as run_5d
from aura_predictive_input_v2 import AuraPredictiveInput
from aura_semantic_predictive_core_v2 import AuraIndex


class AuraHandler(BaseHTTPRequestHandler):
    server_version = "AuraIntelligenceV2/1.1"

    def _json(self, status: int, value: object) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        allowed_origin = getattr(self.server, "allowed_origin", None)
        if allowed_origin:
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.end_headers()
        self.wfile.write(raw)

    def _db_path(self) -> str:
        return str(getattr(self.server, "db_path"))

    def _db(self) -> AuraIndex:
        return AuraIndex(self._db_path())

    def _predictive(self) -> AuraPredictiveInput:
        return AuraPredictiveInput(self._db_path())

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        q = (qs.get("q") or [""])[0]
        limit = min(32, max(1, int((qs.get("limit") or ["8"])[0])))
        try:
            if parsed.path == "/health":
                out = {
                    "status": "OK",
                    "service": "AURA_SEMANTIC_PREDICTIVE_SPIRAL_V2",
                    "db_exists": Path(self._db_path()).exists(),
                    "predictive_input": "TOKEN_AND_PHRASE_WITH_LOCAL_USER_STYLE",
                    "command_authority": False,
                }
            elif parsed.path == "/suggest":
                pred = self._predictive()
                try:
                    out = {
                        "query": q,
                        "token_suggestions": pred.suggest_tokens(q, limit),
                        "phrase_suggestions": pred.suggest_phrases(q, min(limit, 8), 3),
                        "tap_to_accept": True,
                        "auto_execute": False,
                        "user_style_weight_boost": 4,
                    }
                finally:
                    pred.close()
            elif parsed.path == "/search":
                idx = self._db()
                try:
                    out = {"query": q, "hits": idx.semantic_search(q, limit), "semantic_match_is_evidence": False}
                finally:
                    idx.close()
            elif parsed.path == "/question":
                idx = self._db()
                try:
                    out = idx.registry_discriminator(q, limit)
                finally:
                    idx.close()
            elif parsed.path == "/stats":
                idx = self._db()
                try:
                    out = idx.stats()
                finally:
                    idx.close()
            elif parsed.path == "/forecast-prior":
                idx = self._db()
                try:
                    out = idx.forecast_prior(q)
                finally:
                    idx.close()
            else:
                self._json(404, {"error": "NOT_FOUND"}); return
            self._json(200, out)
        except Exception as exc:
            self._json(400, {"error": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16 * 1024 * 1024:
                raise ValueError("POST_BODY_SIZE_INVALID")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("JSON_OBJECT_REQUIRED")
            if parsed.path == "/spiral":
                out = run_5d(payload, db_path=self._db_path())
            elif parsed.path == "/learn-style":
                if payload.get("explicit_human_input") is not True:
                    raise ValueError("EXPLICIT_HUMAN_INPUT_REQUIRED")
                text = str(payload.get("text", "")).strip()
                if not text:
                    raise ValueError("TEXT_REQUIRED")
                pred = self._predictive()
                try:
                    out = pred.learn_user_style(text)
                finally:
                    pred.close()
                out["explicit_human_input"] = True
                out["raw_text_stored"] = False
            elif parsed.path == "/forecast-open":
                idx = self._db()
                try:
                    out = idx.open_forecast(
                        str(payload["task_key"]),
                        float(payload["probability"]),
                        str(payload.get("horizon", "")),
                        payload.get("features", {}),
                        str(payload.get("model_version", "AURA_V2")),
                    )
                finally:
                    idx.close()
            elif parsed.path == "/forecast-resolve":
                idx = self._db()
                try:
                    out = idx.resolve_forecast(
                        str(payload["forecast_id"]), int(payload["outcome"]), resolver=str(payload["resolver"])
                    )
                finally:
                    idx.close()
            else:
                self._json(404, {"error": "NOT_FOUND"}); return
            self._json(200, out)
        except Exception as exc:
            self._json(400, {"error": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        if os.environ.get("AURA_HTTP_QUIET") != "1":
            super().log_message(fmt, *args)


def main() -> int:
    ap = argparse.ArgumentParser(description="Local HTTP surface for Aura predictive input, semantics and 5D spiral")
    ap.add_argument("--db", default=os.environ.get("AURA_INTELLIGENCE_DB", "state/aura_intelligence.sqlite3"))
    ap.add_argument("--host", default=os.environ.get("AURA_HTTP_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("AURA_HTTP_PORT", "8765")))
    ap.add_argument("--allowed-origin", default=os.environ.get("AURA_HTTP_ALLOWED_ORIGIN"))
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AuraHandler)
    server.db_path = args.db  # type: ignore[attr-defined]
    server.allowed_origin = args.allowed_origin  # type: ignore[attr-defined]
    print(json.dumps({
        "schema": "janus.aura.intelligence_http.start.v2",
        "host": args.host,
        "port": args.port,
        "db": str(Path(args.db).resolve()),
        "default_bind_is_localhost": args.host in {"127.0.0.1", "localhost", "::1"},
        "endpoints": [
            "/health", "/suggest", "/search", "/question", "/stats", "/forecast-prior",
            "/spiral", "/learn-style", "/forecast-open", "/forecast-resolve"
        ],
        "predictive_input": "TOKEN_AND_PHRASE_WITH_LOCAL_USER_STYLE",
        "command_authority": False,
    }, ensure_ascii=False), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
