from __future__ import annotations

import argparse
from pathlib import Path

from .models import VotingScheme
from .analysis import run_btva, run_btva_with_strategies
from .parsing import load_input_file


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="btva",
        description="Basic Tactical Voting Analyst (BTVA) — tally positional voting rules.",
    )

    p.add_argument(
        "input",
        type=str,
        help="Path to an .abif input file.",
    )
    p.add_argument(
        "--scheme",
        required=True,
        choices=[s.value for s in VotingScheme],
        help="Voting scheme to apply (required because .abif inputs do not include the scheme).",
    )
    # Scores, strategy enumeration and detailed strategy printing are enabled by default.
    p.add_argument(
        "--max-m",
        type=int,
        default=8,
        help="Safety cap for --enumerate-strategies: refuse enumeration when m > max-m (default: 8).",
    )

    p.add_argument(
        "--profitable1",
        action="store_true",
        help="Filter S_i to options with H~_i > H_i (strictly profitable for the voter).",
    )
    p.add_argument(
        "--profitable2",
        action="store_true",
        help="Filter S_i to options with H~_i >= H_i (profitable or non-worsening for the voter).",
    )
    p.add_argument(
        "--strategy-limit",
        type=int,
        default=-1,
        help=(
            "Max number of strategic options to print per voter when --show-strategies is enabled. "
            "Use -1 for no limit (default: -1)."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate profitable flags: not both at the same time.
    if args.profitable1 and args.profitable2:
        parser.error("--profitable1 and --profitable2 are mutually exclusive; pick one.")

    parsed = load_input_file(Path(args.input))
    scheme: VotingScheme = VotingScheme(args.scheme)

    # Always run the strategic analysis (enumerate strategies subject to max_m guard).
    result = run_btva_with_strategies(scheme, parsed.situation, max_m=args.max_m)

    print(f"scheme: {result.outcome.scheme.value}")
    print(f"winner: {result.outcome.winner}")
    print(f"H_i: {list(result.happiness.per_voter)}")
    print(f"H: {result.happiness.total}")

    # Print scores for the initial (non-strategic) outcome before listing strategies.
    for alt in sorted(result.outcome.scores):
        print(f"{alt}: {result.outcome.scores[alt]}")

    # Print strategic option summaries and the full option tuples (subject to --strategy-limit).
    assert result.strategic_options is not None
    for voter_idx, options in result.strategic_options.items():
        # Optionally filter to profitable options for the voter.
        if args.profitable1:
            # Strictly profitable
            filtered_options = [opt for opt in options if opt.H_tilde_i > opt.H_i]
        elif args.profitable2:
            # Non-worsening or profitable
            filtered_options = [opt for opt in options if opt.H_tilde_i >= opt.H_i]
        else:
            filtered_options = options

        by_kind: dict[str, int] = {}
        for opt in filtered_options:
            by_kind[opt.strategy_kind] = by_kind.get(opt.strategy_kind, 0) + 1

        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items()))
        if breakdown:
            breakdown = f" ({breakdown})"
        print(f"S_{voter_idx}: {len(filtered_options)} options{breakdown}")

        limit = args.strategy_limit
        if limit is None or limit < 0:
            shown = filtered_options
        else:
            shown = filtered_options[:limit]

        for j, opt in enumerate(shown):
            # Print in the naming of the assignment tuple:
            # s_ij = (v~_ij, O~, H~_i, H_i, H~, H)
            print(
                f"  s_{voter_idx},{j}: kind={opt.strategy_kind} v~={list(opt.tactical_ballot.preferences)} "
                f"O~={opt.strategic_outcome} H~_i={opt.H_tilde_i} H_i={opt.H_i} H~={opt.H_tilde} H={opt.H}"
            )

    m = parsed.situation.m_alternatives
    if m > args.max_m:
        print(
            f"note: m={m} > max-m={args.max_m}, so permutation enumeration was skipped (bullet options only)."
        )

    # scores already printed above (initial outcome)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())