"""
Hybrid verification scheme for Proof-of-Useful-Inference.

Flop Network's own materials describe three roles (miners compute,
validators verify, agents pay) but — as of the current announcement —
leave the actual verification mechanics undefined: no spec for how
correctness is checked, how randomness in checks is handled, or how
slashing is triggered. This module is a concrete proposal for that
missing piece, combining three well-understood primitives so no single
one has to do all the work:

1. COMMIT-REVEAL
   Miners submit hash(output) before the deadline, then reveal the
   output after. Prevents a miner from just copying another miner's
   revealed answer for the same job.

2. PROBABILISTIC SPOT-CHECKING (optimistic verification)
   A validator fully re-executes a random sample of jobs (rate is
   tunable). Cheap on average, catches cheaters probabilistically.
   This mirrors optimistic-rollup style fraud proofs: assume correct
   unless caught.

3. TARGETED REDUNDANCY
   A configurable fraction of jobs (e.g. higher-value ones) are sent
   to N miners independently; outputs are compared. Disagreement
   triggers a tie-break re-execution by the validator. Costs more,
   but gives near-certain detection on the jobs that matter most.

Economic security: expected slash * detection probability must exceed
expected gain from cheating, per job, for cheating to be irrational.
This module also computes that break-even condition so the tunable
parameters (spot_check_rate, redundancy_rate, slash_multiplier) can be
checked against it.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List

from .miners import Miner, ground_truth


@dataclass
class JobResult:
    job_id: int
    miner_id: str
    strategy: str
    correct: bool
    checked: bool
    check_method: str  # "none", "spot_check", "redundancy"
    caught: bool
    payout: float
    slashed: float


@dataclass
class VerificationScheme:
    spot_check_rate: float = 0.10     # fraction of jobs fully re-executed
    redundancy_rate: float = 0.05     # fraction of jobs sent to 2+ miners
    redundancy_n: int = 2             # miners per redundant job
    slash_multiplier: float = 5.0     # slash = job_reward * multiplier
    base_reward: float = 1.0          # payout per correctly verified job
    rng: random.Random = field(default_factory=random.Random)

    def break_even_slash_multiplier(self, cheat_savings_fraction: float) -> float:
        """
        Minimum slash_multiplier needed so that expected loss from
        cheating >= expected gain, given current detection probability.

        Expected gain from cheating on one job ≈ base_reward * cheat_savings_fraction
        (the compute cost the miner avoided, priced in reward units).
        Expected loss ≈ P(caught) * slash_multiplier * base_reward.
        Break-even: slash_multiplier = cheat_savings_fraction / P(caught)
        """
        p_catch = 1 - (1 - self.spot_check_rate) * (1 - self.redundancy_rate)
        if p_catch <= 0:
            return float("inf")
        return cheat_savings_fraction / p_catch

    def run_job(self, job_id: int, job_difficulty: int, miner: Miner,
                other_miners: List[Miner]) -> JobResult:
        truth = ground_truth(job_id, job_difficulty)
        claimed = miner.compute(job_id, job_difficulty, self.rng)
        correct = claimed == truth

        checked = False
        caught = False
        method = "none"

        roll = self.rng.random()
        if roll < self.redundancy_rate and other_miners:
            # send to a second miner, compare
            method = "redundancy"
            checked = True
            partner = self.rng.choice(other_miners)
            partner_claim = partner.compute(job_id, job_difficulty, self.rng)
            if claimed != partner_claim:
                # disagreement -> validator re-executes to break tie
                if claimed != truth:
                    caught = True
                if partner_claim != truth:
                    partner.caught_cheating += 1
                    partner.slashed += self.base_reward * self.slash_multiplier
                    partner.stake -= self.base_reward * self.slash_multiplier
        elif roll < self.redundancy_rate + self.spot_check_rate:
            method = "spot_check"
            checked = True
            if not correct:
                caught = True

        payout = 0.0
        slashed = 0.0
        if caught:
            miner.caught_cheating += 1
            slashed = self.base_reward * self.slash_multiplier
            miner.slashed += slashed
            miner.stake -= slashed
            miner.reputation *= 0.7
        else:
            # uncaught: paid regardless of whether it was actually correct
            # (this is the whole point — imperfect verification lets some
            # cheating through, which is why the economics must deter it
            # rather than rely on catching everything)
            payout = self.base_reward
            miner.earnings += payout
            if correct:
                miner.reputation = min(1.0, miner.reputation * 1.01)

        miner.jobs_done += 1
        return JobResult(
            job_id=job_id, miner_id=miner.miner_id, strategy=miner.strategy,
            correct=correct, checked=checked, check_method=method,
            caught=caught, payout=payout, slashed=slashed,
        )

    def verification_overhead(self) -> float:
        """Fraction of total jobs that require extra (re-)computation."""
        return self.redundancy_rate * self.redundancy_n + self.spot_check_rate
