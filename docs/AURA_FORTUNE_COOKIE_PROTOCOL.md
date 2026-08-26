# AURA Fortune Cookie Protocol

**Русское имя:** «Печенье с предсказанием»  
**Schema:** `JANUS/AURA/FORTUNE-COOKIE/v1`

## Idea

AURA may produce an answer, forecast, interpretation, solver candidate, or other sensitive payload without immediately revealing it. The payload is canonicalized in memory, committed with SHA-256, sealed with authenticated encryption, and only then may a public artifact be written.

```text
AURA OUTPUT
   │
   ├─ SHA-256 ───────────────> public commitment
   │
   └─ AES-256-GCM(HKDF key) ─> sealed payload
                                │
                                └─ explicit UNSEAL only
```

The cookie is therefore split into two layers:

- **wrapper:** non-secret status, label, hashes, cipher metadata;
- **prediction inside:** encrypted bytes that are not committed in plaintext.

## Security semantics

SHA-256 is a one-way commitment and integrity fingerprint, not reversible encryption. Reversible secrecy is provided by AES-256-GCM. A fresh per-artifact key is derived using HKDF-SHA-256 from a 256-bit master key kept outside the repository.

The implementation is fail-closed:

- no key → no sealed artifact is written;
- wrong key → no plaintext;
- modified ciphertext/AAD → no plaintext;
- keys are never stored in the artifact;
- CI self-tests use ephemeral non-secret keys only.

## JANUS release gate

Default mode is `JANUS_LOCAL_SEALED_ONLY`.

A future external recipient is not enabled merely by naming an institution or country. Controlled disclosure requires a concrete recipient identity plus a verified public key and an explicit release decision. The JANUS meta-registry trust policy currently records the United States as the owner's preferred future external trust recipient, while cryptographic recipient binding remains disabled until such a key is supplied and verified.

## Epistemic firewall

Sealing changes who can read an output. It does **not** make the output true.

```text
COMMITMENT != TRUTH
SEALED_OUTPUT != EVIDENCE
FORECAST != FUTURE_FACT
ASSOCIATION != CAUSATION
ORACLE_OUTPUT != SCIENTIFIC_AUTHORITY
```

AURA may preserve a prediction before the outcome is known and later compare it with external evidence. This is useful for calibration because the original answer cannot be silently rewritten after the fact.

## Recommended lifecycle

`ASK → SYNTHESIZE_IN_MEMORY → CANONICALIZE → COMMIT → SEAL → PUBLISH_WRAPPER → EXTERNAL_RESOLUTION → OPTIONAL_UNSEAL`

The protocol is intentionally reusable beyond divination-style UI: hypothesis discrimination, blind tests, machine synthesis, forecasting, and any JANUS lane where pre-commitment before observation is scientifically useful.
