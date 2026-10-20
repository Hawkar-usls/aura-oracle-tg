# CHRONOS-003 SOFTONLY — independent, no-hardware native AURA 100-digit test

**Preregistered primary hypothesis:** the already frozen AURA NATIVE10 head
predicts new uniform OS-CSPRNG digits better than chance in exactly 100 trials.
**Context:** historical 20-digit holdout was negative (0/20 top-1 hits). This
new run is a genuinely prospective independent draw, not a second training set.

## Absolute prior commitment

The native 10-class model and all 100 future distributions were frozen before
the new outcome source was invoked:

* Forecast Git freeze commit:
  `4162f4beb5a927ef45eacbf109aefdb6dad1cfc8`
* Forecast canonical SHA-256:
  `c1dd23d52fc283b53f300a9b349845491d8a56a0ad024ff773cd9bf71741e129`
* Model canonical SHA-256:
  `c0525ea5c052f8e2c255ff2ade9be66be11e94af034176263c39187d9656f66e`

The full 10 probabilities and selected digit for trial 1–100 are already in
`experiments/AURA-NATIVE10-forecast-v1-frozen.json`. There is **no forecast
adaptation or calibration from this run's outcomes**. Source SHA and full file
byte hashes are checked before any new RNG operation. A separately implemented
softmax reconstruction independently checks the 100 probabilities.

## Independent *software* execution and scoring

Two separately written modules have no imports from the AURA model:

1. `tools/chronos003_software_blind_runner.py`: replays the coefficients and
   immutable forecast, then calls `secrets.randbelow(10)` **only after** the
   historical Git freeze and all source commitments pass; performs 100 nominal
   1-ms waits, logs monotonic elapsed ns and UTC wall ns for each draw.
2. `tools/chronos003_independent_verify.py`: checks both SHA-256 wrappers,
   event chronology, 100 digits, probability normalization, independent
   exact `Binomial(100,0.1)` one-sided tail, multiclass log loss, scaled
   multiclass Brier, and observed timing ranges.

The GitHub Actions job runs on a fresh Linux cloud runner with read-only repo
permissions. It first proves the frozen file matches the ancestor commit,
executes synthetic integrity/tamper tests, then draws the real 100 new digits,
checks them using independent scoring code, and saves both raw results and
the computed audit in a retained Actions artifact.

The initial primary run is triggered **only once** by a separate commit that
adds `experiments/CHRONOS-003-NATIVE10-software-trigger-v1.json`; any other
change in that commit fails the guard. Only `GITHUB_RUN_ATTEMPT=1` executes
entropy draws. Reruns are disallowed as replacement primary samples; if the
primary fails, record failure/incompleteness instead of cherry-picking a better
result. The job must not push scores into the repository, promote to `main`,
connect real JANUS permissions, or alter the frozen weights/predictions.

## Decision rule fixed before drawing

* Top-1 exact hit count in 100 trials, null chance `p = 0.1` per trial.
* Exact **one-sided** binomial probability of ≥ observed hits. Alpha = 0.01.
* Log loss and class-normalized Brier vs the uniform reference: 2.30258509
  nats and 0.09, respectively, are also recorded.
* No optional stopping. A statistically unusual result needs independently
  preregistered replication, accounting for prior experiments/model searches.
* A negative or inconclusive result remains permanent evidence; do not refit
  this v1 head to the new target digits and then call that a fresh prediction.

## What this run **cannot** demonstrate

1. The Linux kernel's OS CSPRNG is independently executed relative to AURA's
   earlier frozen prediction, **but not attested by an external scientific
   laboratory and not independently hardware-certified**. Entropy health and
   GitHub trust are not physically verified by this workflow.
2. `perf_counter_ns` records monotonic delays with real measured jitter. It is
   **not** atomic/PPS/GNSS/PTP attestation, does not certify UTC error, and
   cannot demonstrate a 1-ms prediction-to-event lead. The forecast has existed
   much longer than one millisecond.
3. SHA-256/CI logs provide reproducible ordering and an audit trail, not proof
   that physical retrocausality, time travel or influence on the present exists.
4. Unit tests use deterministic **synthetic** digits and timestamps only;
   they are not counted as the primary experiment.

The separate CHRONOS-003 hardware evidence gate remains `BLOCKED_NO_DEVICE`
regardless of this software experiment's scores.
