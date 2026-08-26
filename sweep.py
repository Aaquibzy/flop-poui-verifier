"""
Sweep spot_check_rate x slash_multiplier to find the cheapest
verification overhead that still keeps the network economically
secure (break-even satisfied). This is the actual design question
a real Flop Network parameter choice would need to answer:

  "What's the minimum re-computation overhead we need to pay for,
   given a slashing stake size we're willing to require from miners?"

Redundancy is held fixed at a modest rate for this sweep; spot-checking
is the cheaper lever so it's swept most finely.
"""

import argparse
from .scheme import VerificationScheme


def sweep(cheat_savings_fraction: float, redundancy_rate: float, redundancy_n: int):
    print(f"{'spot_check':>12}{'slash_mult':>12}{'overhead':>12}{'breakeven':>12}{'status':>16}")
    rows = []
    for spot in [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]:
        for slash in [1.0, 2.0, 3.0, 5.0, 8.0, 10.0]:
            scheme = VerificationScheme(
                spot_check_rate=spot,
                redundancy_rate=redundancy_rate,
                redundancy_n=redundancy_n,
                slash_multiplier=slash,
            )
            breakeven = scheme.break_even_slash_multiplier(cheat_savings_fraction)
            secure = slash >= breakeven
            overhead = scheme.verification_overhead()
            rows.append((spot, slash, overhead, breakeven, secure))

    # find the cheapest (lowest overhead) secure configuration
    secure_rows = [r for r in rows if r[4]]
    secure_rows.sort(key=lambda r: r[2])  # by overhead ascending

    for spot, slash, overhead, breakeven, secure in rows:
        status = "SECURE" if secure else "under-secured"
        marker = " <== cheapest secure" if secure_rows and (spot, slash) == (secure_rows[0][0], secure_rows[0][1]) else ""
        print(f"{spot:>11.0%} {slash:>11.1f}x {overhead:>11.1%} {breakeven:>11.2f}x {status:>15}{marker}")

    if secure_rows:
        best = secure_rows[0]
        print()
        print(f"Cheapest secure config: spot_check_rate={best[0]:.0%}, "
              f"slash_multiplier={best[1]:.1f}x -> only {best[2]:.1%} of jobs "
              f"need re-computation.")


def main():
    ap = argparse.ArgumentParser(description="Sweep PoUI parameters for cheapest secure config")
    ap.add_argument("--cheat-savings-fraction", type=float, default=0.5,
                     help="fraction of compute cost a cheater saves by cheating")
    ap.add_argument("--redundancy-rate", type=float, default=0.02)
    ap.add_argument("--redundancy-n", type=int, default=2)
    args = ap.parse_args()
    sweep(args.cheat_savings_fraction, args.redundancy_rate, args.redundancy_n)


if __name__ == "__main__":
    main()
