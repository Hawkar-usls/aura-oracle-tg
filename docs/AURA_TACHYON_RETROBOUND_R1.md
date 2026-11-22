# AURA Oracle ↔ JANUS TACHYON (RETROBOUND R1)

**State:** opt-in, read-only research peer. No live production coupling and
no claim about physical retrocausality.

## Real cross-repository chain

1. TACHYON in \`Hawkar-usls/Demi_Head\` produced R1 synthetic validation
   on source commit \`a6f84e3707828f59946be3848e0bc128d9e2b8cc\`.
2. AURA reads the exact upstream JSON research receipt, byte-matched to
   Git blob \`44f422bd450e1a29d4927235502868c49955002c\`.
3. AURA checks the exact normal-causal, two-boundary and forward-postselection
   models. It returns a **question/hypotheses packet**, not a forecast of the world.
4. The reciprocal DemiHead import is proposed at
   https://github.com/Hawkar-usls/Demi_Head/pull/119 as a stacked review on
   https://github.com/Hawkar-usls/Demi_Head/pull/118.
5. DemiHead is not allowed to automatically update any model, schedule an
   experiment, change external clocks or publish a retrocausal claim.

AURA proposal:
https://github.com/Hawkar-usls/aura-oracle-tg/pull/14

The five AURA D-axes are a convenient **analysis vocabulary**:
temporal-order assumptions, model fit, early observable, provenance and
evidence state. This is not a five-spacetime-dimension physical model.
AURA's existing spiral engine is not retrained or automatically invoked
by this bridge.

## Usage (manual, opt-in)

    python tools/aura_tachyon_retrobound_bridge.py \
      --input tests/fixtures/tachyon_retrobound_r1_validation_20261123.json \
      --output /tmp/aura_tachyon_advisory.json

The GitHub Actions workflow tests the bridge and uploads the output as a
CI artifact. It has **contents: read** and does not use tokens, deployment
secrets, continuous cross-repository write permissions or auto-seal keys.

The companion DemiHead receiver is used similarly:

    python tools/tachyon_aura_oracle_ingress.py \
      --input tests/fixtures/aura_tachyon_r1_advisory_ci_20261123.json \
      --output /tmp/tachyon_aura_ack.json

No service runs these CLIs automatically. No live external random source
is connected.

## Evidence boundaries

- Conditioned hidden histories can depend on a future boundary in the
  classical R1 mathematical model.
- The same law arises by **ordinary forward postselection**.
- The specified *public* parity record was chosen to be invariant by
  a global sign symmetry. That is not an empirical physical finding.
- The source Git hash or AURA SHA-256 packet digest checks content
  integrity, not independently confirmed time order or sensor truth.
- AURA cannot assign a calibrated probability that physical
  retrocausality is true; no independent physical experiment exists.
- AURA's Fortune Cookie sealing is *not* activated, and a commitment
  would not by itself establish prediction or retrocausality.

For a meaningful prospective R2, a new hypothesis must predict an
accessible early physical record different from the strong forward
causal/postselection alternatives. Freeze and independently timestamp
**every** early trial before independently generating the late setting,
and pre-register leakage controls, multiple comparisons, missing trials
and a blinded external custodian. Otherwise report HOLD.

## No permission escalation

Zero autonomous downstream effects, no change to TACHYON R5F original
algorithm, RETROBOUND simulation, model weights, production services,
AURA forecast ledgers or sealed output. This is an evidence-disciplined
cross-repository research communication contract only.
