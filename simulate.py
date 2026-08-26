"""
Run a simulated Flop-style network for N jobs across a miner population
with mixed strategies, under a given VerificationScheme, and report:

- detection rate per strategy
- net profitability per strategy (earnings - slashes - compute cost)
- verification overhead (% of jobs re-executed)
- whether current parameters are above the break-even slash multiplier
"""

import argparse
import random
from collections import defaultdict

from .miners import Miner
from .scheme import VerificationScheme


def build_population(rng: random.Random, n_honest=6, n_lazy=2, n_adversarial=2, stake=50.0):
    miners = []
    for i in range(n_honest):
        miners.append(Miner(miner_id=f"honest-{i}", strategy="honest", stake=stake))
    for i in range(n_lazy):
        miners.append(Miner(miner_id=f"lazy-{i}", strategy="lazy", stake=stake))
    for i in range(n_adversarial):
        miners.append(Miner(miner_id=f"adversarial-{i}", strategy="adversarial", stake=stake))
    rng.shuffle(miners)
    return miners


def run(n_jobs: int, difficulty: int, scheme: VerificationScheme,
        miners: list, seed: int = 0):
    rng = random.Random(seed)
    scheme.rng = rng
    results = []
    for job_id in range(n_jobs):
        miner = rng.choice(miners)
        others = [m for m in miners if m is not miner]
        r = scheme.run_job(job_id, difficulty, miner, others)
        results.append(r)
    return results


def summarize(miners: list, results: list, scheme: VerificationScheme, difficulty: int):
    by_strategy = defaultdict(lambda: {"jobs": 0, "caught": 0, "checked": 0})
    for r in results:
        s = by_strategy[r.strategy]
        s["jobs"] += 1
        s["checked"] += int(r.checked)
        s["caught"] += int(r.caught)

    print("=" * 62)
    print("FLOP PoUI VERIFICATION SIMULATION")
    print("=" * 62)
    print(f"jobs simulated:        {len(results)}")
    print(f"job difficulty:        {difficulty} (compute-cost proxy)")
    print(f"spot_check_rate:       {scheme.spot_check_rate:.1%}")
    print(f"redundancy_rate:       {scheme.redundancy_rate:.1%} (x{scheme.redundancy_n} miners)")
    print(f"slash_multiplier:      {scheme.slash_multiplier}x")
    print(f"verification overhead: {scheme.verification_overhead():.1%} of jobs re-computed")
    print()

    print(f"{'strategy':<14}{'jobs seen':>10}{'checked':>10}{'caught':>10}{'catch rate':>12}")
    for strat, s in by_strategy.items():
        rate = s["caught"] / s["checked"] if s["checked"] else 0.0
        print(f"{strat:<14}{s['jobs']:>10}{s['checked']:>10}{s['caught']:>10}{rate:>11.1%}")
    print()

    print(f"{'miner_id':<16}{'strategy':<14}{'jobs':>6}{'earned':>10}{'slashed':>10}{'net':>10}{'stake_left':>12}")
    for m in sorted(miners, key=lambda m: m.strategy):
        cost = m.compute_cost(difficulty) * m.jobs_done / max(m.jobs_done, 1)
        net = m.earnings - m.slashed
        print(f"{m.miner_id:<16}{m.strategy:<14}{m.jobs_done:>6}{m.earnings:>10.2f}"
              f"{m.slashed:>10.2f}{net:>10.2f}{m.stake:>12.2f}")
    print()

    # Economic security check
    cheat_savings_fraction = 0.5  # e.g. adversarial miner saves ~50% compute
    breakeven = scheme.break_even_slash_multiplier(cheat_savings_fraction)
    verdict = "SECURE" if scheme.slash_multiplier >= breakeven else "UNDER-SECURED"
    print("-" * 62)
    print(f"break-even slash_multiplier needed: {breakeven:.2f}x "
          f"(current: {scheme.slash_multiplier}x) -> {verdict}")
    if verdict == "UNDER-SECURED":
        print("  Cheating is currently profitable in expectation.")
        print("  Raise slash_multiplier, spot_check_rate, or redundancy_rate.")
    print("=" * 62)


def main():
    ap = argparse.ArgumentParser(description="Flop-style PoUI verification simulator")
    ap.add_argument("--jobs", type=int, default=2000)
    ap.add_argument("--difficulty", type=int, default=200)
    ap.add_argument("--spot-check-rate", type=float, default=0.10)
    ap.add_argument("--redundancy-rate", type=float, default=0.05)
    ap.add_argument("--redundancy-n", type=int, default=2)
    ap.add_argument("--slash-multiplier", type=float, default=5.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    miners = build_population(rng)
    scheme = VerificationScheme(
        spot_check_rate=args.spot_check_rate,
        redundancy_rate=args.redundancy_rate,
        redundancy_n=args.redundancy_n,
        slash_multiplier=args.slash_multiplier,
    )
    results = run(args.jobs, args.difficulty, scheme, miners, seed=args.seed)
    summarize(miners, results, scheme, args.difficulty)


if __name__ == "__main__":
    main()
