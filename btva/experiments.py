from __future__ import annotations
import argparse
import csv
import time
from datetime import date
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from .analysis import compute_risk, run_btva_with_strategies
from .happiness import HappinessMetric
from .models import VotingScheme
from .parsing import load_input_file

@dataclass(frozen=True)
class ExperimentRow:
    scenario: str
    m: int
    n: int
    scheme: str
    winner: str
    H_total: float
    H_mean: float
    H_total_tactical: float
    H_mean_tactical: float
    avg_individual_gain_over_tactics: float
    avg_delta_H_total_over_tactics: float
    tactical_options_total: int
    risk_avg_gain_all_options: float
    risk_fraction_change_winner: float
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


def run_experiments(
    *,
    scenario_files: Iterable[Path],
    schemes: Iterable[VotingScheme],
    max_m: int = 8,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[ExperimentRow]:
    rows: list[ExperimentRow] = []

    scenario_files = list(scenario_files)
    schemes = list(schemes)
    total_jobs = len(scenario_files) * len(schemes)
    jobs_done = 0
    t_start = time.perf_counter()

    for s_idx, scenario_file in enumerate(scenario_files, start=1):
        try:
            parsed = load_input_file(scenario_file)
        except Exception as e:
            print(f"warning: skipping {scenario_file.name}: {type(e).__name__}: {e}")
            continue

        situation = parsed.situation

        if situation.m_alternatives > max_m:
            print(
                f"note: {scenario_file.name}: m={situation.m_alternatives}>max_m={max_m} => "
                "skipping compromising/burying permutation enumeration (bullet only)",
                flush=True,
            )

        for k_idx, scheme in enumerate(schemes, start=1):
            t0 = time.perf_counter()

            if total_jobs > 0:
                print(
                    f"[{jobs_done+1:>4}/{total_jobs}] scenario {s_idx}/{len(scenario_files)} {scenario_file.name} | "
                    f"scheme {k_idx}/{len(schemes)} {scheme.value}",
                    flush=True,
                )

            result = run_btva_with_strategies(scheme, situation, max_m=max_m, happiness_metric=happiness_metric)

            assert result.strategic_options is not None
            tactical_options_by_voter = {
                i: [opt for opt in opts if opt.H_tilde_i > opt.H_i]
                for i, opts in result.strategic_options.items()
            }

            risk_gain = compute_risk(tactical_options_by_voter, method="avg_gain_all_options")
            risk_change = compute_risk(tactical_options_by_voter, method="fraction_change_winner")

            tactical_total = sum(len(opts) for opts in tactical_options_by_voter.values())

            tactical_gains = [
                (opt.H_tilde_i - opt.H_i)
                for opts in tactical_options_by_voter.values()
                for opt in opts
            ]

            tactical_delta_total = [
                (opt.H_tilde - opt.H)
                for opts in tactical_options_by_voter.values()
                for opt in opts
            ]

            avg_tactical_gain = (sum(tactical_gains) / len(tactical_gains) if tactical_gains else 0.0)

            avg_delta_H_total = (
                sum(tactical_delta_total) / len(tactical_delta_total)
                if tactical_delta_total
                else 0.0
            )

            H_mean_tactical = (float(result.happiness.total) / max(1, situation.n_voters)) + float(avg_tactical_gain)
            H_total_tactical = H_mean_tactical * max(1, situation.n_voters)

            t1 = time.perf_counter()

            note_parts: list[str] = []
            if situation.m_alternatives > max_m:
                note_parts.append(
                    f"m={situation.m_alternatives}>max_m={max_m}: compromising_burying permutation enumeration skipped (bullet only)"
                )

            rows.append(
                ExperimentRow(
                    scenario=scenario_file.name,
                    m=situation.m_alternatives,
                    n=situation.n_voters,
                    scheme=scheme.value,
                    winner=result.outcome.winner,
                    H_total=float(result.happiness.total),
                    H_mean=float(result.happiness.total) / max(1, situation.n_voters),
                    H_total_tactical=float(H_total_tactical),
                    H_mean_tactical=float(H_mean_tactical),
                    avg_individual_gain_over_tactics=float(avg_tactical_gain),
                    avg_delta_H_total_over_tactics=float(avg_delta_H_total),
                    tactical_options_total=int(tactical_total),
                    risk_avg_gain_all_options=float(risk_gain["overall"]),
                    risk_fraction_change_winner=float(risk_change["overall"]),
                    time_seconds=float(t1 - t0),
                    note="; ".join(note_parts),
                )
            )
            jobs_done += 1
    return rows


def write_csv(rows: list[ExperimentRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else [])
        if rows:
            writer.writeheader()
            for r in rows:
                writer.writerow(asdict(r))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="btva.experiments",
        description=("Run BTVA experiments over a set of .abif scenarios and voting schemes and write a CSV."))

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
            "Glob for scenario files to include (repeatable). Default: sv_poll_*.abif. "
            "Example: --include 'sv_poll_*_small.abif' --include 'sv_poll_*_medium.abif'"
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
        "--max-m",
        type=int,
        default=8,
        help=(
            "Safety cap for compromising_burying enumeration used during strategy analysis. "
            "If m > max-m, only bullet options are enumerated (default: 8)."
        ),
    )
    p.add_argument(
        "--happiness-metric",
        type=str,
        choices=[m.value for m in HappinessMetric],
        default=HappinessMetric.BORDA.value,
        help=(
            "How to compute voter happiness when evaluating outcomes. "
            "Choices: borda, rank_normalized (default: borda)."
        ),
    )
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "Output CSV path. Default: experiments/results_<YYYY-MM-DD>.csv "
            "(based on local date)."
        ),
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    include_globs = args.include if args.include else ["sv_poll_*.abif"]

    scenarios_dir = Path(args.scenarios_dir)
    scenario_files = _iter_scenario_files(
        scenarios_dir,
        include_globs=list(include_globs),
        exclude_prefixes=tuple(args.exclude_prefix),
    )

    schemes = list(VotingScheme)

    rows = run_experiments(
        scenario_files=scenario_files,
        schemes=schemes,
        max_m=args.max_m,
        happiness_metric=HappinessMetric(args.happiness_metric),
    )

    out_path = Path(
        args.out
        if args.out
        else f"experiments/results_{date.today().isoformat()}.csv"
    )
    write_csv(rows, out_path)

    print(f"wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
