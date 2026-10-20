# CHRONOS-004 — AURA Signal10 v2, repair and calibrated software controls

## Outcome

The old CHRONOS-003 R1 `8/100` prospective result is **immutable** and remains
`NO_EVIDENCE_ABOVE_CHANCE`. In that experiment AURA's former 10-class head
used features derived solely from the trial index; any apparent pattern in
previous independent digits was noise. On the 100 new digits its logloss
`2.322384292297` was worse than a uniform ten-class predictor's
`2.302585092994` (Brier `/10`: `0.090360806166` vs `0.09`).

Instead of refitting on those **already revealed** digits, CHRONOS-004 builds
an independent new, non-authoritative `AURA_SIGNAL10_CALIBRATED_V2` module.
It handles two fundamentally different classes of processes:

1. **Declared independent uniform digits without pre-event signal:** predict
   `P(0)=...=P(9)=0.1`. A fixed trial-index tie-breaking schedule cycles
   `0,1,...,9`; point guesses have *no claimed advantage*. Uniform is the
   theoretically optimal probability report under the specified IID null.
2. **Processes with a genuinely observed pre-event categorical signal:**
   learn all ten conditional digit probabilities, using a 10-by-10 smoothed
   frequency table. A chronological 80%/20% train/validation split gates
   use of the conditional model. If it fails to beat the uniform logloss on
   the internal validation segment, automatically fall back to 10%/digit.

The whole process is non-mutating to production AURA, NAS and JANUS authority.
This module is an **opt-in CLI research component**, not yet wired into the
production Telegram Oracle. An externally declared source class does not
authenticate any actual sensor, remote RNG, or alleged atomic-grade clock.

## Reproducible held-out software controls

Run `python tools/aura_signal10_v2.py controls` from repo root.
Each simulation uses 800 synthetic historical examples, of which 640 fit
the signal table and 160 are held out to decide whether the signal qualifies.
It then forecasts 300 further synthetic targets, which have not been supplied
to `fit` or the prediction stage. Target schedule uses simulated one-millisecond
gaps, **not measured synchronized physical time**. Fixed test seed: `20261020`.

| Simulated process | Internal gate | 300 held-out matches | Held-out logloss ↓ | Held-out Brier /10 ↓ |
| --- | --- | ---: | ---: | ---: |
| Informative pre-event signal (83% planted reliability) | `VALIDATED_CONDITIONAL` | **238** | **0.995209254877** | **0.037304850864** |
| Irrelevant pre-event signal | `UNIFORM_FALLBACK_NO_VALIDATED_SKILL` | 34 | 2.302585092994 | 0.09 |
| Independent uniform-digit null | `UNIFORM_NULL` | 32 | 2.302585092994 | 0.09 |

Simulation measures ordinary conditional prediction, **not precognition**.
The process generator's parameters are intentionally known to the experiment
author; therefore synthetic positive performance cannot establish any new
physical phenomenon. The two negative controls test honest calibration and
resistance to fitting spurious patterns.

## Integrity requirements

- Training outcome timestamps must be *earlier* than model creation time;
  each genuine input signal must be earlier than its target.
- Prediction features must be observed **before** the frozen forecast packet.
- Forecast targets are chronologically ordered and after the forecast.
- Each model and forecast packet has a canonical SHA-256 commitment; modifying
  the packet invalidates subsequent scoring.
- Research outputs use exclusive file creation, preventing accidental
  overwrites of committed versions.
- Outcomes must be later than the prediction and supplied in trial order.
- Source declarations and timestamps are assertions until an independent
  attestation system verifies them; neither machine time nor entropy quality
  can be certified by software assertions alone.
- Existing CHRONOS-003 R1 files, their hash commitments, and the physical
  hardware gate are not modified or reset.

## Repeat independently

```bash
python -m unittest discover -s tests -v
python tools/aura_signal10_v2.py controls
python tools/aura_signal10_v2.py train --history history.json --trained-at-ns 999999999999 --output model.json
python tools/aura_signal10_v2.py forecast --model model.json --schedule schedule.json --prepared-at-ns 9999999999999 --output frozen.json
python tools/aura_signal10_v2.py score --forecast frozen.json --observations later.json --output score.json
```

The final three lines are an **interface example**; actual timestamps and
schema-conformant files must be provided. `tests/test_aura_signal10_v2.py`
exercises a real temporary-file CLI round trip. The CLI never itself chooses
or generates real future outcome digits in `forecast` mode.

## Next research gate

To test something beyond a synthetic control, register a *new* prospective
trial with a **real, independently observable and timestamped pre-event
signal** and compare it against a uniform/null predictor on a locked unseen
holdout. For physically independent CSPRNG digits there is no such known
signal; without it AURA legitimately returns the uniform forecast.

`CHRONOS004_SOFTWARE_CONTROLS = PASS` (local test suite)

`CHRONOS003_R1_NULL_RESULT = PRESERVED`

`HARDWARE_MILLISECOND_OR_ATOMIC_ATTESTATION = NOT_AVAILABLE`

`AURA_PRECOGNITION = NOT_ESTABLISHED`

`PHYSICAL_RETROCAUSALITY = NOT_ESTABLISHED`
