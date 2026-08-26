#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
except ImportError as exc:
    raise SystemExit("cryptography package required; fail-closed") from exc

SCHEMA = "JANUS/AURA/FORTUNE-COOKIE/v1"
INFO = b"AURA-FORTUNE-COOKIE-v1"
DEFAULT_KEY_ENV = "AURA_FORTUNE_COOKIE_KEY_B64"


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


def load_master_key(env_name: str = DEFAULT_KEY_ENV) -> bytes:
    raw = os.environ.get(env_name)
    if not raw:
        raise RuntimeError(f"missing {env_name}; refusing to seal or unseal")
    key = b64d(raw)
    if len(key) != 32:
        raise RuntimeError(f"{env_name} must decode to exactly 32 bytes")
    return key


def derive_key(master_key: bytes, salt: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=INFO).derive(master_key)


def canonical_aad(label: str, commitment: str, public_status: str) -> bytes:
    obj = {
        "schema": SCHEMA,
        "label": label,
        "plaintext_commitment_sha256": commitment,
        "public_status": public_status,
    }
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal_bytes(plaintext: bytes, master_key: bytes, *, label: str, public_status: str) -> dict:
    commitment = hashlib.sha256(plaintext).hexdigest()
    salt = secrets.token_bytes(32)
    nonce = secrets.token_bytes(12)
    aad = canonical_aad(label, commitment, public_status)
    ciphertext = AESGCM(derive_key(master_key, salt)).encrypt(nonce, plaintext, aad)
    return {
        "schema": SCHEMA,
        "mechanic": "FORTUNE_COOKIE__PECHENYE_S_PREDSKAZANIEM",
        "label": label,
        "public_status": public_status,
        "cipher": "AES-256-GCM",
        "kdf": "HKDF-SHA-256",
        "salt_b64": b64e(salt),
        "nonce_b64": b64e(nonce),
        "aad_b64": b64e(aad),
        "plaintext_commitment_sha256": commitment,
        "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
        "ciphertext_b64": b64e(ciphertext),
        "key_material_in_artifact": False,
        "recipient": {
            "mode": "JANUS_LOCAL_SEALED_ONLY",
            "external_recipient": None,
            "policy": "EXPLICIT_OWNER_UNSEAL_OR_VERIFIED_RECIPIENT_KEY_WRAP",
        },
        "epistemic_boundary": {
            "commitment_is_not_truth": True,
            "oracle_output_is_not_evidence": True,
            "sealed_state_is_not_correctness_proof": True,
        },
    }


def unseal_object(obj: dict, master_key: bytes) -> bytes:
    if obj.get("schema") != SCHEMA:
        raise RuntimeError("unsupported fortune-cookie schema")
    ciphertext = b64d(obj["ciphertext_b64"])
    if hashlib.sha256(ciphertext).hexdigest() != obj["ciphertext_sha256"]:
        raise RuntimeError("ciphertext SHA-256 mismatch")
    aad = b64d(obj["aad_b64"])
    expected = canonical_aad(obj["label"], obj["plaintext_commitment_sha256"], obj["public_status"])
    if aad != expected:
        raise RuntimeError("associated-data mismatch")
    plaintext = AESGCM(derive_key(master_key, b64d(obj["salt_b64"]))).decrypt(
        b64d(obj["nonce_b64"]), ciphertext, aad
    )
    if hashlib.sha256(plaintext).hexdigest() != obj["plaintext_commitment_sha256"]:
        raise RuntimeError("plaintext commitment mismatch")
    return plaintext


def write_json_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def cmd_seal(args: argparse.Namespace) -> int:
    key = load_master_key(args.key_env)
    plaintext = sys.stdin.buffer.read() if args.input == "-" else Path(args.input).read_bytes()
    obj = seal_bytes(plaintext, key, label=args.label, public_status=args.public_status)
    write_json_atomic(Path(args.output), obj)
    print(json.dumps({"status": "SEALED", "commitment": obj["plaintext_commitment_sha256"]}, sort_keys=True))
    return 0


def cmd_unseal(args: argparse.Namespace) -> int:
    key = load_master_key(args.key_env)
    obj = json.loads(Path(args.input).read_text(encoding="utf-8"))
    plaintext = unseal_object(obj, key)
    if args.output == "-":
        sys.stdout.buffer.write(plaintext)
    else:
        Path(args.output).write_bytes(plaintext)
    return 0


def cmd_selftest(_: argparse.Namespace) -> int:
    key = secrets.token_bytes(32)
    payload = b"AURA Fortune Cookie selftest payload"
    obj = seal_bytes(payload, key, label="SELFTEST", public_status="HELD")
    assert unseal_object(obj, key) == payload
    try:
        unseal_object(obj, secrets.token_bytes(32))
    except Exception:
        pass
    else:
        raise AssertionError("wrong key accepted")
    tampered = json.loads(json.dumps(obj))
    raw = bytearray(b64d(tampered["ciphertext_b64"]))
    raw[0] ^= 1
    tampered["ciphertext_b64"] = b64e(bytes(raw))
    tampered["ciphertext_sha256"] = hashlib.sha256(bytes(raw)).hexdigest()
    try:
        unseal_object(tampered, key)
    except Exception:
        pass
    else:
        raise AssertionError("tampered ciphertext accepted")
    print("PASS: AURA Fortune Cookie authenticated sealing")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AURA Fortune Cookie sealed-oracle primitive")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--label", required=True)
    s.add_argument("--public-status", default="HELD")
    s.add_argument("--key-env", default=DEFAULT_KEY_ENV)
    s.set_defaults(func=cmd_seal)
    u = sub.add_parser("unseal")
    u.add_argument("input")
    u.add_argument("output")
    u.add_argument("--key-env", default=DEFAULT_KEY_ENV)
    u.set_defaults(func=cmd_unseal)
    t = sub.add_parser("selftest")
    t.set_defaults(func=cmd_selftest)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
