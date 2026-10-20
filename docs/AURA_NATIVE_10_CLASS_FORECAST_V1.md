# AURA NATIVE10 — CHRONOS-002 prospective forecasting head, v1

## Scope and honest status

This is a **native trained ten-class probabilistic head** for the AURA research
repository, replacing the arbitrary SHA-256 graph-to-digit decoder in the earlier
5D pilot. It directly emits `P(outcome=0)` … `P(outcome=9)` and the maximum-
probability digit. It is a separately implemented AURA module; it is **not** an
extension of the 5D semantic network with proven emergent prediction ability.

It uses only pre-event, public schedule features: a bias and sine/cosine of the
trial index with periods 10 and 100. Its outputs come from a learned 10×5
weight matrix and softmax, **not hashes or leaked random outcomes**. There is
no physical mechanism by which those schedule features should predict new
independent CSPRNG digits. The correct scientific null is chance performance.

## Frozen training and validation

The *previously completed* CHRONOS-002 baseline control contains 100
independent OS-CSPRNG digits. The historical dataset is accepted only if the
ordered outcomes match SHA-256
`2eda20d5d0fd3c368b7359562ebfd811941b0058394ca033a73cb9e6df80f529`;
each historic draw must precede training. The first 80 digits were used to fit
the weights; the last 20 were reserved for one out-of-sample check.

The v1 hyperparameters were locked in the source (400 full-batch epochs,
learning rate 0.3, non-bias L2 0.4, 50% shrinkage to the uniform distribution).
No retuning on the validation data is permitted for this v1 model. Training
itself is deterministic, including rounding the frozen weights to 12 places.

| Holdout metric (20 digits) | AURA NATIVE10 v1 | Uniform null |
| --- | ---: | ---: |
| Multiclass log loss, nats (lower is better) | 2.361538001409 | 2.302585092994 |
| Mean multiclass Brier / 10 (lower is better) | 0.091128306465 | 0.090000000000 |
| Top-1 exact hits | 0 / 20 | 2 / 20 expected |

This is a **negative** validation outcome. The 20-point holdout is small; these
numbers do not establish an intrinsic inability either. They only disallow any
claim that the presently frozen v1 head has shown predictive advantage.

## Prospectively frozen 100 forecasts

The committed artifacts are:

* `experiments/AURA-NATIVE10-model-v1.json` — 10×5 coefficients, source hash,
  training/heldout provenance, metrics and model SHA-256.
* `experiments/AURA-NATIVE10-forecast-v1-frozen.json` — 100 rows, each with the
  10 normalized class probabilities, one point digit, and model linkage.

The forecast contains **no future outcomes**. `commitment_sha256` is SHA-256
over canonical JSON of the immutable forecast payload. Git commit of the
forecast must predate the next independent entropy draw. Any second freeze or
changed forecast is a separate experiment, never a replacement for weak data.

Nominal offsets 1–100 ms are **relative to the start of a later independent
runner**, not relative to the time at which the forecast JSON was created.
The source is committed beforehand, so the forecast-to-draw horizon is much
longer than one millisecond. Reporting this as a demonstrated 1-ms
precognitive prediction would be false.

Run locally from the repository root (paths here are illustrative if you want
to train a *new* protocol version; the committed files are intentionally
write-once and must not be overwritten):

```bash
python tools/aura_native_digit_head_v1.py train \
  --history experiments/CHRONOS-002-baseline-result.json \
  --output /tmp/AURA-NATIVE10-new-model.json

python tools/aura_native_digit_head_v1.py forecast \
  --model experiments/AURA-NATIVE10-model-v1.json \
  --delay-ms 1 \
  --output /tmp/AURA-NATIVE10-new-forecast.json

python -m unittest discover -s tests -p 'test_aura_native_digit_head_v1.py' -v
```

The optional `--require-hardware-clock` currently **fails closed**. The
repository has no physical oscillator, PPS capture, PTP grandmaster validation,
uncertainty measurements or authenticated evidence chain. A flag in JSON is
not hardware proof.

## Future independent blind runner: preconditions

Do **not** treat a cloud-hosted OS clock as an attested atomic clock. Before
claiming hardware-controlled timing, a separate laboratory needs:

1. An independently controlled, sealed forecast Git SHA and signed receipt
   before any new target entropy is generated; prohibit forecast updates.
2. A separate source of independent uniform digits, ideally a hardware RNG,
   with entropy generation *after* the freeze and documented health tests.
3. Disciplined GNSS PPS / qualified PTP timebase and measurement of clock
   offset, uncertainty, monotonic timestamps, jitter and drift at both the
   event and forecast boundaries. Merely sleeping 1 ms proves none of this.
4. An external observer who signs per-trial event records, full outcomes,
   apparatus identification, configuration and evidence hashes, with a
   read-only evidence archive. The Python scorer currently **does not verify
   external signatures or attestation**: it reports evidence only as asserted.
5. One predeclared 100-trial primary run, no optional stopping; use the
   point-hit `Binomial(100, 0.1)` one-sided tail at alpha 0.01, alongside
   calibrated multiclass log loss and Brier compared with the uniform null.
   If an unusual result occurs, obtain independent replications and account
   for multiple testing across any model variants.

The scorer accepts only an explicit external observation record with schema
`janus.aura.native_digit_head.external_observation.v1`,
`forecast_commitment_sha256`, `resolver` (not AURA/JANUS), `evidence_refs`,
`observed_at_unix_ns`, and exactly 100 `outcomes` in trial order. It produces
descriptive scores; it **cannot authenticate the observer or certify physical
retrocausality**.

## Gate states

* `AURA_NATIVE10_IMPLEMENTATION = PASS`
* `HISTORICAL_HOLDOUT_ADVANTAGE = NOT_DETECTED`
* `NATIVE10_100_FORECASTS_PRECOMMITTED = YES` (once pushed to a Git commit)
* `NATIVE10_EXTERNAL_FUTURE_100 = PENDING`
* `ATOMIC_CLOCK_HARDWARE_ATTESTATION = BLOCKED_NO_DEVICE`
* `AURA_PRECOGNITION = NOT_ESTABLISHED`
* `PHYSICAL_RETROCAUSALITY = NOT_ESTABLISHED`

An AURA model can make probability forecasts; predicting independent future
randomness better than chance is a distinct empirical hypothesis, not a
capability already demonstrated by this software.
