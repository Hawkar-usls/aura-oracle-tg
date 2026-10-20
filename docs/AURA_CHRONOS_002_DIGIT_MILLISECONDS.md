# AURA CHRONOS-002 — 100 digit trials, millisecond timing

**Scope:** check whether an independently identified AURA forecast source predicts future random digits more accurately than the uniform chance baseline. This script is an integrity and statistical harness **not a precognition model**.

1. Choose source **before** testing. `oracle-file` requires the real Oracle to supply exactly 100 integer guesses, 0 through 9, as a JSON list. The runner has no direct digit-forecast endpoint in AURA R0. `baseline` creates a public fixed 0–9 cycle and is **not AURA**.
2. `prepare` freezes all 100 guesses, source, outcome-generation procedure, timing and statistical stopping rule into a canonical SHA-256 commitment. No draws happen in this phase.
3. `reveal` verifies the commitment and only then asks the operating system's CSPRNG (`secrets.randbelow(10)`) for each outcome, after waiting at least 1 ms per trial measured with a monotonic high-resolution clock.
4. The result records each guess, outcome, actual wait time, and a one-sided *exact* Binomial(n=100, p=0.1) tail probability. One predeclared analysis: p ≤ 0.01 merits independent prospective replication; it does **not** prove retrocausality.

## Commands

```bash
# Control baseline, explicitly NOT Oracle predictions.
python tools/aura_chronos_002.py prepare --provider baseline --delay-ms 1 --output baseline-frozen.json
python tools/aura_chronos_002.py reveal --frozen baseline-frozen.json --output baseline-result.json

# Only when 100 genuine oracle guesses already exist, before any outcomes.
python tools/aura_chronos_002.py prepare --provider oracle-file --predictions genuine-aura-guesses.json --delay-ms 1 --output aura-frozen.json
python tools/aura_chronos_002.py reveal --frozen aura-frozen.json --output aura-result.json
```

**Timing meaning.** `perf_counter_ns` provides high-resolution *local elapsed-time measurement*, not the absolute accuracy of an atomic clock. The millisecond here is the minimum interval from a trial's local start to its draw, **not** guaranteed ±1 ms synchronization to global UTC. A genuine atomic-clock-grade test requires a disciplined hardware time source (for example GNSS PPS/PTP), documented offset, uncertainty and an external independent timestamp for the precommitment. `time.time_ns` timestamps have nanosecond *units*, not nanosecond *accuracy*. The exact measured intervals, including scheduler jitter, are logged.

**Boundaries.** A SHA-256 hash saved on the same machine cannot independently prove that guesses existed before draws. The RNG here is a CSPRNG, not an independently observed quantum-random source, and the code/operator can access both phases. For a blind physical hypothesis use separate machines/operators, an externally witnessed precommitment before any random data, an independent source of unpredictable outcomes, blinded scoring, repeated studies, and a registered stopping rule. These results must never be treated as automatic JANUS authority or physical time travel.
