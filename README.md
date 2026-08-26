# Flop PoUI Verifier: a concrete Proof-of-Useful-Inference verification scheme.

An independent, prototype exploring one of the open technical
questions in Arthur Hayes' [Flop Network](https://flop.finance) announcement
(Aug 2026): **how do you actually verify a miner's inference was computed
correctly, without re-running all of it?**

As of this writing, Flop Labs has published a landing page and a one-line
description of "Proof-of-Useful-Inference," but no whitepaper and no
verification spec-correctness checking, randomness handling, and
slashing rules are explicitly undecided. This project is a proposal for
that missing piece, plus a simulator that tests whether the proposal
actually holds up economically.

**This is not affiliated with Flop Labs.** It's an
independent technical exploration meant as a real contribution to the
open design problem, not a token farming or airdrop eligibility task.

## The scheme

Three primitives combined so no single one carries all the weight:

1. **Commit-reveal** - miners commit `hash(output)` before revealing,
   so no one can copy another miner's answer for the same job.
2. **Probabilistic spot-checking** - a tunable fraction of jobs get
   fully re-executed by a validator (optimistic-rollup style: assume
   correct unless caught).
3. **Targeted redundancy** - a smaller fraction of (typically
   higher-value) jobs are sent to 2+ miners independently; disagreement
   triggers a validator tie-break.

Detection is never 100%. The scheme is only sound if being caught is
*expensive enough, weighted by the odds of getting caught*, to make
cheating unprofitable in expectation; a standard optimistic-verification
argument, not a novel one. What's useful here is making that condition
explicit and computable:

```
break_even_slash_multiplier = cheat_savings_fraction / P(caught)
```

If your actual `slash_multiplier` is below that number, cheating pays.
The simulator computes both sides from your chosen parameters instead of
leaving it as a hand-wave.

## What's in this repo

```
verifier/
  miners.py     - honest / lazy / adversarial miner models
  scheme.py     - the verification scheme + break-even math
  simulate.py   - run N jobs across a mixed miner population, report results
  sweep.py      - find the cheapest (lowest-overhead) parameter combo
                  that's still economically secure
```

## Running it

```bash
# Simulate 3000 jobs under a given verification config
python3 -m verifier.simulate --jobs 3000 --spot-check-rate 0.10 \
    --redundancy-rate 0.05 --slash-multiplier 5.0

# Try weak parameters to see cheating become profitable
python3 -m verifier.simulate --jobs 3000 --spot-check-rate 0.02 \
    --redundancy-rate 0.01 --slash-multiplier 2.0

# Sweep parameters to find the cheapest secure configuration
python3 -m verifier.sweep --cheat-savings-fraction 0.5
```

No dependencies beyond the Python 3 standard library.

## Example finding

With adversarial miners saving ~50% of compute cost by cheating, the
sweep finds that **5% spot-checking + an 8x slash multiplier** is the
cheapest tested configuration that stays economically secure; meaning
only ~9% of total network compute needs to be redundantly verified to
deter cheating, rather than something much larger. That's the kind of
concrete number a real network parameter choice needs, instead of
picking a spot-check rate arbitrarily.

## Honest limitations

- `ground_truth()` here is a stand-in (a hash chain used as a
  compute-cost proxy) for "run the actual model forward pass" - it
  captures the verification *economics*, not real inference determinism,
  floating-point non-reproducibility across hardware, or model-weight
  commitment, all of which a real deployment has to solve separately.
- Miner strategies are simplified archetypes, not an adversarial-ML
  search for the most profitable cheat.
- Reputation is tracked but not yet fed back into job routing or stake
  requirements.
- This assumes honest, rational validators. Validator collusion is a
  separate attack surface this prototype doesn't model.

## Why this and not something else

Flop's own materials list four participant types - miners, validators,
agents, KOLs for the verification layer.
Content/social contributions are already being solicited directly
by the project; this instead targets the specific unsolved technical gap,
built independently and generically enough to be checked, argued with, or
thrown away on its own merits.
