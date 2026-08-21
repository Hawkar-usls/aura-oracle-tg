#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

from aura_semantic_predictive_core_v2 import AuraIndex

RUNNING = True


def stop(*_: object) -> None:
    global RUNNING
    RUNNING = False


def main() -> int:
    ap = argparse.ArgumentParser(description="Incrementally index a local janus-meta-registry checkout for Aura")
    ap.add_argument("registry_root", help="Local read-only checkout of Hawkar-usls/janus-meta-registry")
    ap.add_argument("--db", default=os.environ.get("AURA_INTELLIGENCE_DB", "state/aura_intelligence.sqlite3"))
    ap.add_argument("--interval", type=float, default=30.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--stream-threshold", type=int, default=16 * 1024 * 1024)
    args = ap.parse_args()

    root = Path(args.registry_root).resolve()
    if not root.exists():
        raise SystemExit("REGISTRY_ROOT_NOT_FOUND")
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    idx = AuraIndex(args.db)
    try:
        while RUNNING:
            started = time.time()
            receipt = idx.ingest_paths([root], stream_threshold=args.stream_threshold, force=False)
            event = {
                "schema": "janus.aura.registry_watch.tick.v2",
                "registry_root": str(root),
                "db": str(Path(args.db).resolve()),
                "files_seen": receipt["files_seen"],
                "files_indexed": receipt["files_indexed"],
                "records_indexed": receipt["records_indexed"],
                "elapsed_seconds": round(time.time() - started, 6),
                "source_mutation": False,
                "write_back": False,
                "continuous_is_infinite_self_chat": False,
            }
            print(json.dumps(event, ensure_ascii=False), flush=True)
            if args.once:
                break
            time.sleep(max(2.0, args.interval))
    finally:
        idx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
