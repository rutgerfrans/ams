from __future__ import annotations

import argparse
from pathlib import Path

from .models import VotingScheme
from .analysis import compute_risk, run_btva, run_btva_with_strategies
from .happiness import HappinessMetric
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

    p.add_argument(
        "--happiness-metric",
        choices=[m.value for m in HappinessMetric],
        default=HappinessMetric.BORDA.value,
        help=(
            "Happiness metric to use. "
            "borda = (m-1)-rank (historical default); "
            "rank_normalized = 1 - rank/(m-1) (float in [0,1])."
        ),
    )
    # Scores, strategy enumeration and detailed strategy printing are enabled by default.
    p.add_argument(
        "--max-m",
        type=int,
        default=8,
        help="Safety cap for --enumerate-strategies: refuse enumeration when m > max-m (default: 8).",
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

    p.add_argument(
        "--risk-method",
        choices=["avg_gain_all_options", "fraction_change_winner"],
        default="avg_gain_all_options",
        help=(
            "Risk evaluation function to use. "
            "avg_gain_all_options averages (H~_i - H_i) across all options; "
            "fraction_change_winner returns the fraction of voters who can change the winner with some option."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    parsed = load_input_file(Path(args.input))
    scheme: VotingScheme = VotingScheme(args.scheme)
    happiness_metric = HappinessMetric(args.happiness_metric)

    # Always run the strategic analysis (enumerate strategies subject to max_m guard).
    result = run_btva_with_strategies(
        scheme,
        parsed.situation,
        max_m=args.max_m,
        happiness_metric=happiness_metric,
    )

    print(f"scheme: {result.outcome.scheme.value}")
    print(f"winner: {result.outcome.winner}")
    print(f"happiness_metric: {happiness_metric.value}")
    print(f"H_i: {[float(x) for x in result.happiness.per_voter]}")
    print(f"H: {float(result.happiness.total)}")

    # Print scores for the initial (non-strategic) outcome before listing strategies.
    for alt in sorted(result.outcome.scores):
        print(f"{alt}: {result.outcome.scores[alt]}")

    # Print strategic option summaries and the full option tuples (subject to --strategy-limit).
    assert result.strategic_options is not None
    # Option A (assignment-aligned): the strategic/tactical option sets S_i contain only
    # tactical options, i.e. options with H~_i > H_i for the deviating voter.
    tactical_options_by_voter: dict[int, list] = {
        voter_idx: [opt for opt in opts if opt.H_tilde_i > opt.H_i]
        for voter_idx, opts in result.strategic_options.items()
    }

    # The options we display are tactical by definition.
    shown_options_by_voter: dict[int, list] = {}
    for voter_idx, options in tactical_options_by_voter.items():
        filtered_options = options

        shown_options_by_voter[voter_idx] = filtered_options

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

    # Print risk summary based on tactical options S_i (independent of --profitable).
    risk = compute_risk(tactical_options_by_voter, method=args.risk_method)
    by_kind = risk.get("by_strategy_kind", {})
    if isinstance(by_kind, dict) and by_kind:
        breakdown = ", ".join(f"{k}={v:.4g}" for k, v in sorted(by_kind.items()))
        breakdown = f" ({breakdown})"
    else:
        breakdown = ""
    print(f"risk ({risk['method']}): {risk['overall']:.4g}{breakdown}")

    m = parsed.situation.m_alternatives
    if m > args.max_m:
        print(
            f"note: m={m} > max-m={args.max_m}, so compromising_burying enumeration was skipped (bullet options only)."
        )

    # scores already printed above (initial outcome)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())