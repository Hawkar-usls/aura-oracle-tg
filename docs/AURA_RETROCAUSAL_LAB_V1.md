# AURA Retrocausal Lab v1 — обратный ход от цели к действию

**Status:** experimental scenario planning, not physical retrocausality or precognition.  
**Русское имя:** «Ретрокаузальная лаборатория AURA».

The future **cannot send evidence to the past** in this module. A desired future outcome is used as a planning constraint: work backward to candidate decisions available today; project each candidate forward with explicit probabilities. Any real-world impact on the future must happen through an ordinary, authorized action in the present.

## Four lanes, kept separate

1. **BACKWARD GOAL:** define `target_at`, mutually exclusive outcomes and utility, and reversible candidate actions.
2. **FORWARD SCENARIOS:** enter conditional probabilities for each action. These are **assumptions**, not learned or identified causal effects.
3. **FREEZE:** compute SHA-256 over canonical JSON; optionally encrypt the entire forecast with existing Fortune Cookie AES-256-GCM. A file hash alone does **not** provide an independent timestamp. For a preregistered study, commit a wrapper/hash to a timestamped external log **before** the event.
4. **EXTERNAL RESOLUTION:** after target date, an independent resolver supplies the actually selected action, observed outcome, and evidence references. Score only the observed-action forecast using multiclass Brier and log loss; all unobserved counterfactuals stay unknown.

## Local CLI

```bash
python tools/aura_retrocausal_lab_v1.py plan examples/AURA_RETROCAUSAL_DEMO_REQUEST.json --output my-plan.json
```

To keep forecasts confidential use the existing Fortune Cookie primitive. Do not commit the master key:

```bash
# Set AURA_FORTUNE_COOKIE_KEY_B64 to a secure random 32-byte key, base64 encoded.
python tools/aura_retrocausal_lab_v1.py plan examples/AURA_RETROCAUSAL_DEMO_REQUEST.json --seal --output my-plan.sealed.json
```

No key → **no sealed artifact**. Explicit unseal is required before scoring. Existing `tools/aura_fortune_cookie.py unseal ...` handles that step. Outputs are created exclusively and never silently overwritten.

Once externally observed, prepare a resolution JSON:

```json
{
  "schema": "janus.aura.retrocausal_lab.resolution.v1",
  "resolver": "INDEPENDENT_OBSERVER",
  "resolved_at": "2026-11-02T00:00:00Z",
  "actual_action_id": "PILOT",
  "observed_outcome_id": "SUCCESS",
  "evidence_refs": ["external:observation-id"]
}
```

```bash
python tools/aura_retrocausal_lab_v1.py resolve my-plan.json resolution.json --output score.json
```

The resolver identifier and evidence references are *asserted*, not authenticated by this prototype. There is no automatic verification of external sources. Historical runs prepared **after** `target_at` are labeled `RETROSPECTIVE_SIMULATION_ONLY` and are never counted as prospective evidence.

## How to test a genuine anomalous retrocausal hypothesis

If one wants to investigate a physical claim, pre-register a **separate** experiment with randomization, a prospective external timestamp, blinded outcome collection, leak-free inputs, independent replication, negative controls, and a declared statistical stopping rule. The present planning engine is **not** a test of backward-in-time signaling.

### Hard boundaries

`SIMULATION != FUTURE_FACT` · `CONDITIONAL_FORECAST != CAUSAL_EFFECT` · `LOCAL_SHA256 != TRUSTED_TIMESTAMP` · `OUTCOME_RESOLUTION != COUNTERFACTUAL_PROOF` · `RECOMMENDATION != AUTOMATIC_ACTION`.

For safety, no registry writes, autonomous calls, physical actuator commands, or JANUS authority promotion are performed.
