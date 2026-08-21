#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, io, json, tarfile
from pathlib import Path

def safe_extract(tf: tarfile.TarFile, dest: Path) -> list[str]:
    root = dest.resolve(); names=[]
    for m in tf.getmembers():
        target=(root/m.name).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f'UNSAFE_TAR_PATH:{m.name}')
        names.append(m.name)
    tf.extractall(root)
    return names

def materialize(repo: Path, dest: Path) -> dict:
    parts=sorted((repo/'.janus/bootstrap').glob('aura_v3_payload.part*'))
    if not parts: raise FileNotFoundError('AURA_V3_PAYLOAD_PARTS_NOT_FOUND')
    encoded=''.join(p.read_text(encoding='ascii').strip() for p in parts)
    raw=base64.b64decode(encoded, validate=True)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tf:
        names=safe_extract(tf,dest)
    return {'schema':'janus.aura.v3.materialize.receipt.v1','status':'MATERIALIZED','parts':len(parts),'bytes':len(raw),'files':sorted(names),'dest':str(dest.resolve())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',default='.'); ap.add_argument('--dest',default='.'); ap.add_argument('--receipt')
    a=ap.parse_args(); out=materialize(Path(a.repo),Path(a.dest)); text=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
    if a.receipt: Path(a.receipt).write_text(text,encoding='utf-8')
    print(text,end=''); return 0
if __name__=='__main__': raise SystemExit(main())
