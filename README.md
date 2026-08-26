<div align="center">

# 🔮 AURA Oracle
### Semantic · Predictive · Sealed Oracle Peer for the JANUS ecosystem

[![Status](https://img.shields.io/badge/status-active%20prototype-6f42c1)](PROJECT_STATUS.json)
[![Spiral](https://img.shields.io/badge/engine-semantic%20predictive%20spiral%20v3-0ea5e9)](.janus/AURA_SEMANTIC_PREDICTIVE_SPIRAL_V3.json)
[![Fortune Cookie](https://img.shields.io/badge/sealed%20mode-Fortune%20Cookie-f59e0b)](docs/AURA_FORTUNE_COOKIE_PROTOCOL.md)
[![JANUS](https://img.shields.io/badge/ecosystem-JANUS-111827)](.janus/JANUS_ORGANISM_LINK.json)

**AURA is no longer only a tarot-style Telegram experiment.**  
It is an active JANUS peer for semantic retrieval, hypothesis discrimination, bounded forecasting, spiral state analysis, and cryptographically sealed pre-commitment.

[Open AURA interface](https://hawkar-usls.github.io/aura-oracle-tg/) · [Project status](PROJECT_STATUS.json) · [Fortune Cookie protocol](docs/AURA_FORTUNE_COOKIE_PROTOCOL.md)

</div>

---

## What AURA is now

AURA combines its original symbolic/oracle interface with a machine-readable analytical layer. The current repository contains:

- **Semantic / Predictive Spiral v3** — forward/reverse processing with stateful return rather than circular reset;
- **5D spiral analysis** with structural and associative projections;
- **HRain / iNaiHR views** while preserving disagreement instead of silently merging it into truth;
- **Meta Registry indexing** in read-only mode, including incremental and large-JSON processing;
- **information-gain questioning** for hypothesis discrimination;
- **predictive input** for typing completion, kept separate from world forecasting;
- **forecast ledgers** with external resolution and Brier / log-loss calibration bookkeeping;
- **Habitat, JANUS-SPI and Terminal bindings** as part of the wider JANUS organism;
- **Fortune Cookie sealed-oracle mode** for committing to an output before revealing it.

AURA can therefore act as a *reflection surface*, *semantic peer*, *question generator*, *forecast recorder*, and *sealed witness* — but never as an automatic authority on truth.

## 🍪 Fortune Cookie — «Печенье с предсказанием»

The new sealed-oracle primitive lets AURA form an output without immediately exposing the plaintext.

```text
QUESTION / INPUT
      │
      ▼
AURA SYNTHESIS
      │
      ├── SHA-256 ─────────────> public commitment
      │
      └── AES-256-GCM ─────────> sealed payload
                                   │
                                   └── explicit UNSEAL only
```

SHA-256 is used as a one-way commitment and integrity fingerprint. Reversible secrecy is provided by authenticated encryption using AES-256-GCM with an HKDF-SHA-256 derived per-artifact key. Master key material stays outside the repository.

The default state is:

```text
JANUS_LOCAL_SEALED_ONLY
```

No key means no artifact write. A wrong key or modified ciphertext is rejected. External disclosure requires an explicit release decision and a verified recipient public key.

This makes the mechanism useful not only for oracle-style readings, but also for **blind tests, forecasts, hypothesis commitments, machine-synthesis checkpoints, and any experiment where the answer must be frozen before the outcome is known**.

See [`docs/AURA_FORTUNE_COOKIE_PROTOCOL.md`](docs/AURA_FORTUNE_COOKIE_PROTOCOL.md) and [`tools/aura_fortune_cookie.py`](tools/aura_fortune_cookie.py).

## 🌀 Spiral model

AURA's current analytical path is not a loop that returns to the same state.

```text
ORIGINₙ
  → FORWARDₙ
  → REVERSEₙ
  → HRAIN_STRUCTURALₙ
  → INAIHR_ASSOCIATIVEₙ
  → INFORMATION_GAINₙ
  → PREDICTIVE_PRIORₙ
  → DEMIHEADₙ
  → RETURNₙ
  → ORIGIN′ₙ₊₁
```

The position may repeat; the state must advance. A semantic hit alone is not enough to promote a conclusion. A zero-delta return becomes a plateau/hold rather than fabricated progress.

## Predictive classes

AURA deliberately separates three different meanings of “prediction”:

| Class | Meaning | Authority |
|---|---|---|
| `TYPING_COMPLETION` | Predict likely next text/token sequences | assistive only |
| `HYPOTHESIS_DISCRIMINATION` | Ask/select questions that distinguish competing models | analytical only |
| `WORLD_FORECAST` | Record bounded probabilistic forecasts for later external resolution | not ground truth |

This separation is important: autocomplete success does not establish precognition, and a forecast probability does not become a future fact merely because AURA emitted it.

## Epistemic firewall

```text
AURA_OUTPUT != EVIDENCE
AURA_OUTPUT != PREDICTIVE_GROUND_TRUTH
ASSOCIATION != EVIDENCE
FORECAST_PROBABILITY != FUTURE_FACT
COMMITMENT != TRUTH
SEALED_OUTPUT != CORRECTNESS_PROOF
QUESTION_INFORMATION_GAIN != ANSWER_TRUTH
```

AURA may generate, preserve, compare, rank, or seal hypotheses. Independent evidence still decides what is true.

## Repository map

```text
.janus/      JANUS organism bindings and capability links
contracts/   machine-readable AURA contracts
 tools/       semantic, predictive, spiral and sealed-oracle engines
 deploy/      persistent runtime templates
 receipts/    runtime validation receipts
 ritual/      symbolic/oracle interaction artifacts
 artifacts/   generated research artifacts
 docs/        protocol and architecture documentation
 index.html   Telegram / GitHub Pages visual interface
```

## Local validation

```bash
python -m pip install -r requirements-aura-intelligence.txt
python tools/aura_fortune_cookie.py selftest
```

The Fortune Cookie workflow also verifies that sealing **fails closed** when no key is present.

## Maturity

**ACTIVE PROTOTYPE.** The repository contains executable and CI-validated components, but it is not presented as a production-certified forecasting system, a scientific authority, or evidence of supernatural prediction.

For the machine-readable capability ceiling and current runtime status, see [`PROJECT_STATUS.json`](PROJECT_STATUS.json).

---

<div align="center">

**AURA watches possibilities. JANUS decides nothing without evidence.**  
`REFLECT → DISCRIMINATE → COMMIT → SEAL → OBSERVE → VERIFY → RETURN′`

</div>
