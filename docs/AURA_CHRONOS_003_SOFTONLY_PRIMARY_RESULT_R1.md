# CHRONOS-003 SOFTONLY — primary run R1, final checkpoint

**Verdict: `NO_EVIDENCE_ABOVE_CHANCE`.** The first and only primary software
blind run completed successfully on a separate GitHub-hosted Actions runner.
It tested the *previously frozen* native AURA 10-class probabilistic model,
not a new model tuned to revealed outcomes.

## Immutable sequence

1. Old 100 forecasts committed at SHA
   `4162f4beb5a927ef45eacbf109aefdb6dad1cfc8`, canonical SHA-256
   `c1dd23d52fc283b53f300a9b349845491d8a56a0ad024ff773cd9bf71741e129`.
2. Independent reader/scorer, synthetic negative controls, and one-time
   read-only GitHub Actions workflow committed *later*, without outcome draws.
3. A marker-only commit
   `37685513fee9a1127822c71b5590681431b178c4` then triggered the
   one-shot workflow. Its job explicitly checked git ancestry and bit-for-bit
   equality with the original frozen forecast, source SHA, coefficients and
   all 100 probability vectors before calling the OS CSPRNG.
4. [GitHub Actions run 39404642253](https://github.com/Hawkar-usls/aura-oracle-tg/actions/runs/39404642253)
   `run_attempt=1` **succeeded**, producing 100 previously unseen digits at
   measured monotonic waits and a separate independent score file.
5. Original [raw+audit artifact](https://github.com/Hawkar-usls/aura-oracle-tg/actions/runs/39404642253/artifacts/12256259183)
   has ZIP SHA-256
   `1086712b261e8ec7974dfeaeea7472362aac8b2d3115b862dc6fe55f05fd7834`.
   Its 100-observation record's canonical SHA-256 is
   `cd133b32ef0632bec8259ef51bf509fbdcc686320219325b93401212ab53097c`.
6. The artifact was retrieved again, its ZIP digest matched GitHub's, and its
   raw observations were rescored locally without generating any more random
   targets. The local audit JSON was **byte-identical** to the separate
   GitHub-runner audit. Both raw data and original independent audit have been
   copied verbatim into the repo for future reproducibility.

## Scientific numbers

| Preregistered outcome | AURA NATIVE10 | Independent uniform chance reference |
| --- | ---: | ---: |
| Exact top-1 matches in 100 new trials | **8** | 10 expected |
| One-sided `P(Binomial(100, 0.1) ≥ 8)` | **0.793949138196** | Threshold ≤0.01 |
| Mean multiclass log loss, nats ↓ | **2.322384292297** | 2.302585092994 |
| Mean multiclass Brier / 10 ↓ | **0.090360806166** | 0.09 |

Observed top-1 hit fraction: 8%; approximate 95% Wilson interval 4.11–15.00%.
The distribution of the 100 OS-CSPRNG digits, 0–9, was
`[8, 8, 8, 10, 14, 10, 10, 12, 11, 9]`.

Actual monotonic wait durations were **1.025299–1.069374 ms**, each ≥1 ms.
The specific timed waits are NOT a precise 1-ms future-looking prediction
horizon and are not atomic/GNSS/PTP synchronized. There is **no externally
attested hardware entropy source, trusted absolute timebase or independent
laboratory signature** in this software run.

## No post-hoc promotion

The null was not rejected. The AURA head does not outperform the uniform
predictor by either proper probability score on these independent draws.
The recorded result is frozen, **not** relabeled as a model success or
discarded for a favorable rerun. Any new model would need a newly preregistered
dataset and prospective trial; original 100 labels are now public and cannot
be treated as unseen validation for that model.

Statuses:

```text
CHRONOS003_SOFTWARE_PRIMARY_RUN = PASS
FORECAST_PRECOMMIT_AND_SOURCE_REPLAY = PASS
INDEPENDENT_SCORE_REPRODUCTION = PASS
GITHUB_ARTIFACT_INTEGRITY = PASS
POINT_PREDICTIVE_ADVANTAGE = NOT_DETECTED
PROBABILISTIC_SCORE_ADVANTAGE = NOT_DETECTED
HARDWARE_TIME_ATTESTATION = NOT_TESTED
PHYSICAL_RETROCAUSALITY = NOT_ESTABLISHED
```
