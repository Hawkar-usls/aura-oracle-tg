# CHRONOS-002 — AURA 5D derived decoder prospective pilot

**State:** experimental forced-choice adapter attached to real AURA `aura_5d_spiral_v2.run`, with no independent evidence that AURA can predict future random digits.

The current AURA model does **not** natively output a prediction of a future 0–9 digit. The registered `AURA_5D_DERIVED_DIGIT_DECODER_PILOT` calls the real 5D analysis for each of 100 prospectively defined trial prompts, then maps selected AURA graph fingerprints deterministically to a digit by SHA-256 with rejection-sampled modulo 10. The mapping is arbitrary, not trained and not an independent AURA digit-classification head. The forecast tests *this adapter*, not an already-established AURA precognition function.

## Frozen before the outcome

```bash
python tools/aura_chronos_002.py prepare --provider aura-5d --delay-ms 1 --output experiments/CHRONOS-002-aura-5d-frozen.json
```

Each forecast contains the 100 digits, source model identification, actual AURA module source hashes, adapter hash, input prompt hash, the deterministic projection trace commitment, exact hypothesis, stopping rule and measurement spec. A GitHub commit is then required **before any new outcome RNG draw**. Source code and first frozen forecast must be immutable within the run.

## Independent outcome-runner separation

`.github/workflows/aura-chronos-002-blind.yml` is deliberately `push`-only and triggered only by the specifically named frozen forecast file. In the fresh GitHub-hosted runner, it verifies the forecast commitment, re-executes the real AURA 5D adapter and compares the hash/provenance against the frozen record **before calling the OS CSPRNG**. The runner then performs 100 minimum-1-ms delayed digit draws and uploads per-trial evidence as an Actions artifact. The workflow has read-only repository permissions; it does not modify forecasts, merge a PR, or execute JANUS production actions.

**Stopping rule:** first successful outcome run corresponding to the first freeze commit is the primary trial. Any rerun or second commitment is labelled post-hoc/replication, never substituted to improve the result. Threshold for a one-sided binomial test is p ≤ 0.01; an apparently anomalous count only warrants truly independent replication.

**Not an atomic clock.** GitHub's hosted runner supplies local `perf_counter_ns` elapsed time with measured jitter. It does not attest GPS PPS, disciplined UTC offset, or traceability to an atomic timescale. The elapsed delay for each draw is at least ~1 ms, but the forecast-to-outcome horizon is longer because the forecast is committed and a runner must start. This design tests **blindness and independence of execution**, not exact one-millisecond foresight. An OS CSPRNG is not a certified external quantum source; GitHub-hosted infrastructure is not an independent scientific laboratory.

**Limits:** semantic graph hash decoding is a methodological pilot. It is not a scientific demonstration of precognition, physical retrocausality, backward communication, human behaviour manipulation or any power to influence present reality. Genuine physical claims require independently implemented hardware time discipline, third-party sealed precommitment, independent RNG/observer and preregistered replication.
