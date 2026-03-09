from __future__ import annotations

import argparse
import csv
import time
from datetime import date
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from btva.models import VotingScheme
from btva.happiness import HappinessMetric
from btva.parsing import load_input_file

from .atva1_collusion import run_atva1
from .atva2_counter_strategic import run_atva2
from .atva3_imperfect_knowledge import run_atva3
from .atva4_multiple_tactical import run_atva4


@dataclass(frozen=True)
class AtvaExperimentRow:
    """Result row for ATVA experiments."""
    
    scenario: str
    variant: str
    m: int
    n: int
    scheme: str
    baseline_outcome: str
    baseline_total_happiness: float
    baseline_mean_happiness: float
    
    # Variant-specific metrics
    # ATVA-1
    total_coalitions: int
    max_coalition_size_changes_winner: int
    fraction_coalitions_change_winner: float
    avg_coalition_gain: float
    
    # ATVA-2
    total_responses: int
    fraction_manip_with_response: float
    avg_sequence_length: float
    fraction_sequences_restore: float
    
    # ATVA-3
    total_options_under_uncertainty: int
    avg_expected_gain: float
    fraction_robust_options: float
    avg_regret: float
    
    # ATVA-4
    total_multi_voter_scenarios: int
    fraction_all_benefit: float
    fraction_some_hurt: float
    avg_happiness_change: float
    nash_equilibria_count: int
    
    time_seconds: float
    note: str


def _iter_scenario_files(
    scenarios_dir: Path,
    *,
    include_globs: list[str] | None = None,
    exclude_prefixes: tuple[str, ...] = (),
) -> list[Path]:
    if not include_globs:
        include_globs = ["*.abif"]

    seen: set[Path] = set()
    files: list[Path] = []
    for g in include_globs:
        if not any(ch in g for ch in "*?["):
            p = scenarios_dir / g
            if p.exists() and p.is_file() and p not in seen:
                seen.add(p)
                files.append(p)
            continue

        for p in scenarios_dir.glob(g):
            if p not in seen:
                seen.add(p)
                files.append(p)

    files = sorted(files)
    if exclude_prefixes:
        files = [
            p
            for p in files
            if not any(p.name.startswith(prefix) for prefix in exclude_prefixes)
        ]
    return files


def run_atva_experiments(
    *,
    scenario_files: Iterable[Path],
    schemes: Iterable[VotingScheme],
    variants: list[str] | None = None,
    max_coalition_size: int = 3,
    max_iterations: int = 5,
    n_scenarios: int = 5,
    noise_level: float = 0.3,
    max_tactical_voters: int = 3,
    max_ballots_per_voter: int = 3,
    find_equilibria: bool = False,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
    seed: int = 42,
) -> list[AtvaExperimentRow]:
    if variants is None:
        variants = ["atva1", "atva2", "atva3", "atva4"]
    
    rows: list[AtvaExperimentRow] = []
    
    scenario_files = list(scenario_files)
    schemes = list(schemes)
    total_jobs = len(scenario_files) * len(schemes) * len(variants)
    jobs_done = 0
    
    for s_idx, scenario_file in enumerate(scenario_files, start=1):
        try:
            parsed = load_input_file(scenario_file)
        except Exception as e:
            print(f"warning: skipping {scenario_file.name}: {type(e).__name__}: {e}")
            continue
        
        situation = parsed.situation
        
        for k_idx, scheme in enumerate(schemes, start=1):
            for v_idx, variant in enumerate(variants, start=1):
                t0 = time.perf_counter()
                
                # pprogress line
                if total_jobs > 0:
                    print(
                        f"[{jobs_done+1:>4}/{total_jobs}] scenario {s_idx}/{len(scenario_files)} {scenario_file.name} | "
                        f"scheme {k_idx}/{len(schemes)} {scheme.value} | "
                        f"variant {v_idx}/{len(variants)} {variant}",
                        flush=True,
                    )
                
                note_parts: list[str] = []
                
                row_data = {
                    "scenario": scenario_file.name,
                    "variant": variant,
                    "m": situation.m_alternatives,
                    "n": situation.n_voters,
                    "scheme": scheme.value,
                    "baseline_outcome": "",
                    "baseline_total_happiness": 0.0,
                    "baseline_mean_happiness": 0.0,
                    "total_coalitions": 0,
                    "max_coalition_size_changes_winner": 0,
                    "fraction_coalitions_change_winner": 0.0,
                    "avg_coalition_gain": 0.0,
                    "total_responses": 0,
                    "fraction_manip_with_response": 0.0,
                    "avg_sequence_length": 0.0,
                    "fraction_sequences_restore": 0.0,
                    "total_options_under_uncertainty": 0,
                    "avg_expected_gain": 0.0,
                    "fraction_robust_options": 0.0,
                    "avg_regret": 0.0,
                    "total_multi_voter_scenarios": 0,
                    "fraction_all_benefit": 0.0,
                    "fraction_some_hurt": 0.0,
                    "avg_happiness_change": 0.0,
                    "nash_equilibria_count": 0,
                    "time_seconds": 0.0,
                    "note": "",
                }
                
                try:
                    if variant == "atva1":
                        result = run_atva1(
                            scheme, situation,
                            max_coalition_size=max_coalition_size,
                            max_ballots_per_voter=max_ballots_per_voter,
                            happiness_metric=happiness_metric,
                        )
                        row_data["baseline_outcome"] = result.baseline_outcome
                        row_data["baseline_total_happiness"] = result.baseline_total_happiness
                        row_data["baseline_mean_happiness"] = result.baseline_total_happiness / max(1, situation.n_voters)
                        row_data["total_coalitions"] = sum(len(opts) for opts in result.coalition_options.values())
                        row_data["max_coalition_size_changes_winner"] = result.max_coalition_size_that_changes_winner
                        row_data["fraction_coalitions_change_winner"] = result.fraction_of_coalitions_that_change_winner
                        row_data["avg_coalition_gain"] = result.avg_coalition_gain
                    
                    elif variant == "atva2":
                        result = run_atva2(
                            scheme, situation,
                            max_iterations=max_iterations,
                            happiness_metric=happiness_metric,
                        )
                        row_data["baseline_outcome"] = result.baseline_outcome
                        row_data["baseline_total_happiness"] = result.baseline_total_happiness
                        row_data["baseline_mean_happiness"] = result.baseline_total_happiness / max(1, situation.n_voters)
                        row_data["total_responses"] = len(result.responses)
                        row_data["fraction_manip_with_response"] = result.fraction_manipulations_with_counter_response
                        row_data["avg_sequence_length"] = result.avg_sequence_length_until_convergence
                        row_data["fraction_sequences_restore"] = result.fraction_sequences_restore_original
                    
                    elif variant == "atva3":
                        # Use a unique seed per scenario for reproducibility
                        scenario_seed = seed + hash(scenario_file.name) % 10000
                        result = run_atva3(
                            scheme, situation,
                            n_scenarios=n_scenarios,
                            noise_level=noise_level,
                            happiness_metric=happiness_metric,
                            seed=scenario_seed,
                        )
                        row_data["baseline_outcome"] = result.true_baseline_outcome
                        row_data["baseline_total_happiness"] = result.true_baseline_happiness
                        row_data["baseline_mean_happiness"] = result.true_baseline_happiness / max(1, situation.n_voters)
                        row_data["total_options_under_uncertainty"] = sum(len(opts) for opts in result.options_under_uncertainty.values())
                        row_data["avg_expected_gain"] = result.avg_expected_gain
                        row_data["fraction_robust_options"] = result.fraction_robust_options
                        row_data["avg_regret"] = result.avg_regret
                    
                    elif variant == "atva4":
                        result = run_atva4(
                            scheme, situation,
                            max_tactical_voters=max_tactical_voters,
                            max_ballots_per_voter=max_ballots_per_voter,
                            find_equilibria=find_equilibria,
                            happiness_metric=happiness_metric,
                        )
                        row_data["baseline_outcome"] = result.baseline_outcome
                        row_data["baseline_total_happiness"] = result.baseline_total_happiness
                        row_data["baseline_mean_happiness"] = result.baseline_total_happiness / max(1, situation.n_voters)
                        row_data["total_multi_voter_scenarios"] = len(result.scenarios)
                        row_data["fraction_all_benefit"] = result.fraction_scenarios_all_benefit
                        row_data["fraction_some_hurt"] = result.fraction_scenarios_some_hurt
                        row_data["avg_happiness_change"] = result.avg_total_happiness_change
                        row_data["nash_equilibria_count"] = len(result.nash_equilibria)
                
                except Exception as e:
                    note_parts.append(f"Error: {type(e).__name__}: {e}")
                    print(f"  Error in {variant}: {e}")
                
                t1 = time.perf_counter()
                row_data["time_seconds"] = float(t1 - t0)
                row_data["note"] = "; ".join(note_parts)
                
                rows.append(AtvaExperimentRow(**row_data))
                jobs_done += 1
    
    return rows


def write_csv(rows: list[AtvaExperimentRow], out_path: Path) -> None:
    """Write experiment results to CSV."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, 
            fieldnames=list(asdict(rows[0]).keys()) if rows else []
        )
        if rows:
            writer.writeheader()
            for r in rows:
                writer.writerow(asdict(r))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atva.experiments",
        description="Run ATVA experiments over scenarios and voting schemes and write a CSV.",
    )
    
    p.add_argument(
        "--scenarios-dir",
        type=str,
        default="voting_scenarios",
        help="Directory containing .abif scenario files (default: voting_scenarios).",
    )
    p.add_argument(
        "--include",
        type=str,
        action="append",
        default=None,
        help=(
            "Glob for scenario files to include (repeatable). "
            "Example: --include 'sv_poll_*_small.abif'"
        ),
    )
    p.add_argument(
        "--exclude-prefix",
        type=str,
        action="append",
        default=[],
        help="Exclude files whose name starts with this prefix (repeatable).",
    )
    p.add_argument(
        "--variants",
        type=str,
        nargs="+",
        choices=["atva1", "atva2", "atva3", "atva4"],
        default=None,
        help="Which ATVA variants to run (default: all).",
    )
    
    # ATVA-1 options
    p.add_argument(
        "--max-coalition-size",
        type=int,
        default=3,
        help="[ATVA-1] Maximum coalition size (default: 3).",
    )
    
    # ATVA-2 options
    p.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="[ATVA-2] Maximum iterations for counter-strategic sequences (default: 5).",
    )
    
    # ATVA-3 options
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
        help="[ATVA-3] Uncertainty level 0-1 (default: 0.3).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="[ATVA-3] Random seed base (default: 42).",
    )
    
    # ATVA-4 options
    p.add_argument(
        "--max-tactical-voters",
        type=int,
        default=3,
        help="[ATVA-4] Maximum number of tactical voters (default: 3).",
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
        default=3,
        help="Limit on strategic ballots per voter (default: 3).",
    )
    p.add_argument(
        "--happiness-metric",
        type=str,
        choices=[m.value for m in HappinessMetric],
        default=HappinessMetric.BORDA.value,
        help="Happiness metric (default: borda).",
    )
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "Output CSV path. Default: experiments/atva_results_<YYYY-MM-DD>.csv"
        ),
    )
    
    return p


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ATVA experiments."""
    args = build_parser().parse_args(argv)
    
    include_globs = args.include if args.include else ["sv_poll_*_small.abif"]
    
    scenarios_dir = Path(args.scenarios_dir)
    scenario_files = _iter_scenario_files(
        scenarios_dir,
        include_globs=list(include_globs),
        exclude_prefixes=tuple(args.exclude_prefix),
    )
    
    schemes = list(VotingScheme)
    
    rows = run_atva_experiments(
        scenario_files=scenario_files,
        schemes=schemes,
        variants=args.variants,
        max_coalition_size=args.max_coalition_size,
        max_iterations=args.max_iterations,
        n_scenarios=args.n_scenarios,
        noise_level=args.noise_level,
        max_tactical_voters=args.max_tactical_voters,
        max_ballots_per_voter=args.max_ballots_per_voter,
        find_equilibria=args.find_equilibria,
        happiness_metric=HappinessMetric(args.happiness_metric),
        seed=args.seed,
    )
    
    out_path = Path(
        args.out
        if args.out
        else f"experiments/atva_results_{date.today().isoformat()}.csv"
    )
    write_csv(rows, out_path)
    
    print(f"wrote {len(rows)} rows to {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
