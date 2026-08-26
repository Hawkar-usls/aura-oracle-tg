# AURA // KEM // SET — Sealed Oracle Mode

This document preserves the earlier Set / Three Kings sealed-oracle experiment.

## Status

The original mode persisted only a SHA-256 commitment of a canonicalized answer. That remains useful as a **blind pre-commitment**, but it is not reversible secrecy.

The canonical reusable mechanism is now **AURA Fortune Cookie / «Печенье с предсказанием»**:

- protocol: [`docs/AURA_FORTUNE_COOKIE_PROTOCOL.md`](docs/AURA_FORTUNE_COOKIE_PROTOCOL.md)
- implementation: [`tools/aura_fortune_cookie.py`](tools/aura_fortune_cookie.py)
- JANUS binding: [`.janus/AURA_FORTUNE_COOKIE_LINK.json`](.janus/AURA_FORTUNE_COOKIE_LINK.json)

## Relationship

```text
LEGACY SET MODE
canonical answer -> SHA-256 commitment only

FORTUNE COOKIE
canonical answer -> SHA-256 commitment
                 -> AES-256-GCM sealed payload
                 -> explicit UNSEAL gate
```

SHA-256 remains a one-way commitment and integrity fingerprint. It is not encryption and is not treated as a hidden decryption channel. Reversible confidentiality is provided by authenticated encryption with key material kept outside the repository.

The Set symbolic continuity may still use Fortune Cookie as its sealing transport, but the cryptographic primitive is JANUS-wide and is not tied to any mythological interpretation.

## Claim ceiling

```text
ORACLE_OUTPUT_COMMITMENT_NOT_IDENTITY_PROOF
COMMITMENT != TRUTH
SEALED_OUTPUT != EVIDENCE
SYMBOLIC_RECIPIENT != CRYPTOGRAPHIC_RECIPIENT
```

AURA remains non-authoritative: the sealed answer is not evidence of supernatural contact, prophecy, literal identity, or future-event ground truth.
