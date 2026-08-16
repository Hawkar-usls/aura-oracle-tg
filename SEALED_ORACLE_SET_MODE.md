# AURA // KEM // SET — Sealed Oracle Mode

This mode adapts Aura Oracle to the Kem / Three Kings / Set creative continuity.

## Purpose

The canonical question lives in `ritual/SET_ORACLE_QUESTION.json`. The Oracle may generate cards and an interpretation, but the plaintext interpretation is never committed or rendered by the sealed workflow. Only a SHA-256 commitment of a canonicalized answer is persisted.

## Technical boundary

SHA-256 is a one-way hash, not encryption. A hash cannot normally be decoded back into the answer. It proves commitment to a byte sequence if the original is later known, but it does not prove the truth of the Oracle's statement. In the creative canon, Set / Sun / Moon may be treated as the intended symbolic recipients; in real cryptography, recovery would require encryption with recipient keys rather than SHA-256.

## Claim ceiling

`ORACLE_OUTPUT_COMMITMENT_NOT_IDENTITY_PROOF`

Aura remains a creative reflection/oracle application. The sealed answer is not evidence of supernatural contact, prophecy, or literal identity with an ancient or mythological person.
