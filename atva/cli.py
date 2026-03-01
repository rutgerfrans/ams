"""Command-line interface for ATVA variants.

Usage:
    python -m atva.cli <variant> <input_file> [options]

Where variant is one of: atva1, atva2, atva3, atva4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from btva.models import VotingScheme
from btva.happiness import HappinessMetric
from btva.parsing import load_input_file

from .atva1_collusion import run_atva1
from .atva2_counter_strategic import run_atva2
from .atva3_imperfect_knowledge import run_atva3
from .atva4_multiple_tactical import run_atva4


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atva",
        description="Advanced Tactical Voting Analyst (ATVA) — analyze strategic voting beyond BTVA limitations.",
    )

    p.add_argument(
        "variant",
        choices=["atva1", "atva2", "atva3", "atva4"],
        help=(
            "ATVA variant: "
            "atva1 (voter collusion), "
            "atva2 (counter-strategic voting), "
            "atva3 (imperfect knowledge), "
            "atva4 (multiple tactical voters)"
        ),
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
        help="Voting scheme to apply.",
    )

    p.add_argument(
        "--happiness-metric",
        choices=[m.value for m in HappinessMetric],
        default=HappinessMetric.BORDA.value,
        help="Happiness metric to use (default: borda).",
    )

    # ATVA-1 specific options
    p.add_argument(
        "--max-coalition-size",
        type=int,
        default=3,
        help="[ATVA-1] Maximum coalition size to analyze (default: 3).",
    )

    # ATVA-2 specific options
    p.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="[ATVA-2] Maximum iterations for counter-strategic sequences (default: 5).",
    )

    # ATVA-3 specific options
    p.add_argument(
        "--n-scenarios",
        type=int,
        default=5,
        help="[ATVA-3] Number of belief scenarios per voter (default: 5).",
    )

    p.add_argument(
        "--noise-level",
        type=float,
        default=0.3,
        help="[ATVA-3] Uncertainty level (0=perfect knowledge, 1=maximal) (default: 0.3).",
    )

    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="[ATVA-3] Random seed for reproducibility (default: 42).",
    )

    # ATVA-4 specific options
    p.add_argument(
        "--max-tactical-voters",
        type=int,
        default=3,
        help="[ATVA-4] Maximum number of tactical voters to consider (default: 3).",
    )

    p.add_argument(
        "--find-equilibria",
        action="store_true",
        help="[ATVA-4] Compute Nash equilibria (can be slow).",
    )

    # Common options
    p.add_argument(
        "--max-ballots-per-voter",
        type=int,
        default=5,
        help="Limit on strategic ballots to enumerate per voter (default: 5).",
    )

    return p


def run_atva1_cli(args, parsed_input, scheme, happiness_metric):
    """Run ATVA-1 and print results."""
    result = run_atva1(
        scheme,
        parsed_input.situation,
        max_coalition_size=args.max_coalition_size,
        max_ballots_per_voter=args.max_ballots_per_voter,
        happiness_metric=happiness_metric,
    )

    print("=" * 60)
    print("ATVA-1: Voter Collusion Analysis")
    print("=" * 60)
    print(f"Scheme: {result.scheme.value}")
    print(f"Baseline outcome: {result.baseline_outcome}")
    print(f"Baseline total happiness: {result.baseline_total_happiness:.3f}")
    print()

    total_coalitions = sum(len(opts) for opts in result.coalition_options.values())
    print(f"Total coalitions found: {total_coalitions}")
    print(f"Max coalition size that changes winner: {result.max_coalition_size_that_changes_winner}")
    print(f"Fraction of coalitions that change winner: {result.fraction_of_coalitions_that_change_winner:.3f}")
    print(f"Average coalition gain: {result.avg_coalition_gain:.3f}")
    print()

    for size in sorted(result.coalition_options.keys()):
        opts = result.coalition_options[size]
        print(f"Coalition size {size}: {len(opts)} options")
        if opts:
            changes_winner = sum(1 for opt in opts if opt.changes_winner)
            print(f"  - {changes_winner} change the winner")
            print(f"  - Avg coalition gain: {sum(opt.coalition_gain for opt in opts) / len(opts):.3f}")


def run_atva2_cli(args, parsed_input, scheme, happiness_metric):
    """Run ATVA-2 and print results."""
    result = run_atva2(
        scheme,
        parsed_input.situation,
        max_iterations=args.max_iterations,
        happiness_metric=happiness_metric,
    )

    print("=" * 60)
    print("ATVA-2: Counter-Strategic Voting Analysis")
    print("=" * 60)
    print(f"Scheme: {result.scheme.value}")
    print(f"Baseline outcome: {result.baseline_outcome}")
    print(f"Baseline total happiness: {result.baseline_total_happiness:.3f}")
    print()

    print(f"Counter-responses found: {len(result.responses)}")
    print(f"Fraction of manipulations with counter-response: {result.fraction_manipulations_with_counter_response:.3f}")
    print()

    print(f"Iterative sequences: {len(result.iterative_sequences)}")
    print(f"Average sequence length: {result.avg_sequence_length_until_convergence:.2f}")
    print(f"Fraction that restore original outcome: {result.fraction_sequences_restore_original:.3f}")
    print()

    if result.responses:
        print("Sample counter-responses:")
        for resp in result.responses[:5]:
            print(f"  Voter {resp.responding_voter} responds to voter {resp.original_manipulator}")
            print(f"    Baseline → Manipulation → Response: {resp.baseline_outcome} → {resp.after_manipulation_outcome} → {resp.after_response_outcome}")
            print(f"    Responder happiness: {resp.baseline_happiness:.2f} → {resp.after_manipulation_happiness:.2f} → {resp.after_response_happiness:.2f}")


def run_atva3_cli(args, parsed_input, scheme, happiness_metric):
    """Run ATVA-3 and print results."""
    result = run_atva3(
        scheme,
        parsed_input.situation,
        n_scenarios=args.n_scenarios,
        noise_level=args.noise_level,
        happiness_metric=happiness_metric,
        seed=args.seed,
    )

    print("=" * 60)
    print("ATVA-3: Imperfect Knowledge Analysis")
    print("=" * 60)
    print(f"Scheme: {result.scheme.value}")
    print(f"True baseline outcome: {result.true_baseline_outcome}")
    print(f"True baseline happiness: {result.true_baseline_happiness:.3f}")
    print()

    total_options = sum(len(opts) for opts in result.options_under_uncertainty.values())
    print(f"Strategic options under uncertainty: {total_options}")
    print(f"Average expected gain: {result.avg_expected_gain:.3f}")
    print(f"Fraction of robust options: {result.fraction_robust_options:.3f}")
    print(f"Average regret: {result.avg_regret:.3f}")
    print()

    for voter_idx, opts in result.options_under_uncertainty.items():
        if opts:
            print(f"Voter {voter_idx}: {len(opts)} options")
            best = max(opts, key=lambda o: o.expected_gain)
            print(f"  Best option: expected gain = {best.expected_gain:.3f}, variance = {best.happiness_variance:.3f}")


def run_atva4_cli(args, parsed_input, scheme, happiness_metric):
    """Run ATVA-4 and print results."""
    result = run_atva4(
        scheme,
        parsed_input.situation,
        max_tactical_voters=args.max_tactical_voters,
        max_ballots_per_voter=args.max_ballots_per_voter,
        find_equilibria=args.find_equilibria,
        happiness_metric=happiness_metric,
    )

    print("=" * 60)
    print("ATVA-4: Multiple Simultaneous Tactical Voters Analysis")
    print("=" * 60)
    print(f"Scheme: {result.scheme.value}")
    print(f"Baseline outcome: {result.baseline_outcome}")
    print(f"Baseline total happiness: {result.baseline_total_happiness:.3f}")
    print()

    print(f"Multi-voter tactical scenarios: {len(result.scenarios)}")
    print(f"Fraction where all tactical voters benefit: {result.fraction_scenarios_all_benefit:.3f}")
    print(f"Fraction where some tactical voters hurt: {result.fraction_scenarios_some_hurt:.3f}")
    print(f"Average total happiness change: {result.avg_total_happiness_change:.3f}")
    print(f"Max tactical voters observed: {result.max_tactical_voters_observed}")
    print()

    if result.nash_equilibria:
        print(f"Nash equilibria found: {len(result.nash_equilibria)}")
        for i, eq in enumerate(result.nash_equilibria[:3]):
            print(f"  Equilibrium {i+1}:")
            print(f"    Tactical voters: {eq.n_tactical_voters}")
            print(f"    Outcome: {eq.outcome}")
            print(f"    Sincere: {eq.is_sincere_equilibrium}")


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Load input file
    parsed_input = load_input_file(Path(args.input))
    scheme = VotingScheme(args.scheme)
    happiness_metric = HappinessMetric(args.happiness_metric)

    # Run the appropriate variant
    if args.variant == "atva1":
        run_atva1_cli(args, parsed_input, scheme, happiness_metric)
    elif args.variant == "atva2":
        run_atva2_cli(args, parsed_input, scheme, happiness_metric)
    elif args.variant == "atva3":
        run_atva3_cli(args, parsed_input, scheme, happiness_metric)
    elif args.variant == "atva4":
        run_atva4_cli(args, parsed_input, scheme, happiness_metric)
    else:
        print(f"Unknown variant: {args.variant}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
