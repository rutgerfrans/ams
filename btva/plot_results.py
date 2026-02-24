"""Plot experiment results (trade-off plots only).

This script reads the CSV produced by `python -m btva.experiments` and writes
ONLY two publication-friendly trade-off scatter plots comparing voting schemes.

We compare schemes on:
- baseline mean happiness (H_mean)
- tactical-voting risk under two definitions:
  - winner-change risk: risk_fraction_change_winner
  - avg-gain risk: risk_avg_gain_all_options (risk defined as strength of incentives to manipulate)

Usage:
    .venv/bin/python -m btva.plot_results --csv experiments/results.csv

Outputs by default to:
    experiments/plots/
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _default_results_csv() -> Path:
    """Pick a sensible default CSV.

    Prefer the newest experiments/results_*.csv (dated runs). If none exist,
    fall back to experiments/results.csv for backward compatibility.
    """

    experiments_dir = Path("experiments")
    candidates = sorted(experiments_dir.glob("results_*.csv"))
    if candidates:
        # Lexicographic sort works for ISO dates: results_YYYY-MM-DD.csv
        return candidates[-1]
    return experiments_dir / "results.csv"


def _read_results(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    required = {"scenario", "scheme"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"CSV missing required columns: {sorted(missing)}")

    # Keep plotting stable; users sometimes re-run experiments with different order.
    df["scenario"] = df["scenario"].astype(str)
    df["scheme"] = df["scheme"].astype(str)

    # Prefer stable ordering: scenario name ascending, then a sensible scheme order.
    scheme_order = ["plurality", "vote_for_two", "anti_plurality", "borda"]
    df["scheme"] = pd.Categorical(df["scheme"], categories=scheme_order, ordered=True)
    df = df.sort_values(["scenario", "scheme"], kind="stable")

    return df


def _minmax_0_1(series: pd.Series) -> pd.Series:
    """Min-max normalize to [0, 1].

    If all values are equal (or the column is all-NaN), returns 0.0 for
    non-NaN entries.
    """

    s = pd.to_numeric(series, errors="coerce")
    vmin = s.min(skipna=True)
    vmax = s.max(skipna=True)
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        # Keep NaNs as NaN so plot can drop them naturally.
        return s.where(s.isna(), 0.0)
    return (s - vmin) / (vmax - vmin)


def _plot_tradeoff_scatter(df: pd.DataFrame, *, out_path: Path) -> None:
    """Scatter: each point is a scenario under a scheme (H_mean vs risk).

    This makes the happiness vs risk trade-off visual, while still comparing
    schemes through their clouds of points.
    """

    needed = {"scheme", "scenario", "H_mean", "risk_fraction_change_winner"}
    if not needed.issubset(df.columns):
        return

    rng = np.random.default_rng(0)
    jitter = 0.01

    plt.figure(figsize=(7, 5))
    for scheme, g in df.groupby("scheme", observed=True):
        x = pd.to_numeric(g["risk_fraction_change_winner"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["H_mean"], errors="coerce").to_numpy()

        # Common academic visualization trick: add a tiny, reproducible jitter
        # so coincident points don't fully overlap.
        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = np.clip(y + rng.normal(0.0, jitter, size=len(y)), 0.0, 1.0)

        plt.scatter(
            xj,
            yj,
            label=str(scheme),
            alpha=0.6,
            s=30,
        )

    plt.title("Happiness vs. Tactical-Voting Risk (normalized 0–1)")
    plt.xlabel("risk_fraction_change_winner")
    plt.ylabel("H_mean")
    plt.xlim(0.0, 1.0)
    plt.ylim(0.0, 1.0)
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()


def _plot_happiness_vs_avg_gain_scatter(df: pd.DataFrame, *, out_path: Path) -> None:
    """Scatter: H_mean vs risk_avg_gain_all_options (both normalized).

    Each point is (scenario, scheme). This compares schemes on baseline
    happiness versus tactical-voting risk where "risk" is defined as the
    strength of incentives to manipulate (avg gain over tactical options).
    """

    needed = {"scheme", "scenario", "H_mean", "risk_avg_gain_all_options"}
    if not needed.issubset(df.columns):
        return

    rng = np.random.default_rng(0)
    jitter = 0.01

    plt.figure(figsize=(7, 5))
    for scheme, g in df.groupby("scheme", observed=True):
        x = pd.to_numeric(g["risk_avg_gain_all_options"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["H_mean"], errors="coerce").to_numpy()

        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = np.clip(y + rng.normal(0.0, jitter, size=len(y)), 0.0, 1.0)

        plt.scatter(
            xj,
            yj,
            label=str(scheme),
            alpha=0.6,
            s=30,
        )

    plt.title("Happiness vs Tactical-Voting Risk (Normalized 0–1)")
    plt.xlabel("risk_avg_gain")
    plt.ylabel("H_mean")
    plt.xlim(0.0, 1.0)
    plt.ylim(0.0, 1.0)
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plot btva experiment CSV results")
    parser.add_argument(
        "--csv",
        type=Path,
        default=_default_results_csv(),
        help="Path to results CSV (default: newest experiments/results_*.csv if present)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("experiments/plots"),
        help="Directory to write PNG plots into",
    )
    args = parser.parse_args(argv)

    df_raw = _read_results(args.csv)

    # Normalize only the metrics we need for the tradeoff plots.
    for col in ["H_mean", "risk_fraction_change_winner", "risk_avg_gain_all_options"]:
        if col in df_raw.columns:
            df_raw[f"{col}_norm"] = _minmax_0_1(df_raw[col])

    if "H_mean_norm" in df_raw.columns and "risk_fraction_change_winner_norm" in df_raw.columns:
        df_trade = df_raw.copy()
        df_trade["H_mean"] = df_trade["H_mean_norm"]
        df_trade["risk_fraction_change_winner"] = df_trade[
            "risk_fraction_change_winner_norm"
        ]
        _plot_tradeoff_scatter(
            df_trade,
            out_path=args.out_dir / "tradeoff_h_mean_vs_risk_fraction.png",
        )

    if "H_mean_norm" in df_raw.columns and "risk_avg_gain_all_options_norm" in df_raw.columns:
        df_gain = df_raw.copy()
        df_gain["H_mean"] = df_gain["H_mean_norm"]
        df_gain["risk_avg_gain_all_options"] = df_gain["risk_avg_gain_all_options_norm"]
        _plot_happiness_vs_avg_gain_scatter(
            df_gain,
            out_path=args.out_dir / "tradeoff_h_mean_vs_risk_avg_gain.png",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
