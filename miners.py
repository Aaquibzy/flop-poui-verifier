"""
Miner models for the Proof-of-Useful-Inference (PoUI) simulation.

Each miner receives an inference job (a deterministic function of a seed)
and returns an output. Honest miners compute it correctly. Dishonest
miners try to save compute cost by cheating in different ways, each
representing a realistic attack a real GPU provider might attempt.
"""

import hashlib
import random
from dataclasses import dataclass, field


def ground_truth(job_seed: int, job_difficulty: int) -> str:
    """
    Stand-in for 'run the actual model inference'.
    Deterministic, expensive-to-fake, cheap-to-verify-if-you-redo-it.
    In a real system this would be a forward pass through a committed
    model checkpoint on a committed input. Here we simulate it with a
    hash chain of configurable length (difficulty = compute cost proxy).
    """
    h = f"seed:{job_seed}".encode()
    for _ in range(job_difficulty):
        h = hashlib.sha256(h).digest()
    return h.hex()


@dataclass
class Miner:
    miner_id: str
    strategy: str  # "honest", "lazy", "adversarial"
    stake: float
    reputation: float = 1.0
    jobs_done: int = 0
    caught_cheating: int = 0
    earnings: float = 0.0
    slashed: float = 0.0

    def compute(self, job_seed: int, job_difficulty: int, rng: random.Random) -> str:
        """Return the miner's claimed output for a job."""
        truth = ground_truth(job_seed, job_difficulty)

        if self.strategy == "honest":
            return truth

        if self.strategy == "lazy":
            # Doesn't run the job at all — returns a plausible-looking
            # but wrong hash (e.g. cached/copied from a past unrelated job).
            fake = hashlib.sha256(f"lazy:{job_seed}:{rng.random()}".encode()).hexdigest()
            return fake

        if self.strategy == "adversarial":
            # Runs a *cheaper* approximation (e.g. fewer rounds) hoping
            # spot checks miss it, or flips output only occasionally to
            # stay under detection thresholds.
            if rng.random() < 0.5:
                return truth  # behaves honestly most of the time
            # subtle tamper: truncate difficulty to cut cost
            cheaper = ground_truth(job_seed, max(1, job_difficulty // 2))
            return cheaper

        raise ValueError(f"unknown strategy {self.strategy}")

    def compute_cost(self, job_difficulty: int) -> float:
        """Rough compute cost this miner actually pays, by strategy."""
        if self.strategy == "honest":
            return job_difficulty
        if self.strategy == "lazy":
            return 0.0
        if self.strategy == "adversarial":
            return job_difficulty * 0.5
        return job_difficulty
