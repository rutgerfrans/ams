from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

#Pick a sensible default CSV.
def _default_results_csv() -> Path:
    experiments_dir = Path("experiments")
    candidates = sorted(experiments_dir.glob("atva_results_*.csv"))
    if candidates:
        return candidates[-1]
    return experiments_dir / "atva_results.csv"


def _read_results(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    required = {"scenario", "scheme", "variant"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"CSV missing required columns: {sorted(missing)}")

    df["scenario"] = df["scenario"].astype(str)
    df["scheme"] = df["scheme"].astype(str)
    df["variant"] = df["variant"].astype(str)

    scheme_order = ["plurality", "vote_for_two", "anti_plurality", "borda"]
    df["scheme"] = pd.Categorical(df["scheme"], categories=scheme_order, ordered=True)

    variant_order = ["atva1", "atva2", "atva3", "atva4"]
    df["variant"] = pd.Categorical(df["variant"], categories=variant_order, ordered=True)

    return df.sort_values(["scenario", "scheme", "variant"], kind="stable")

#helper functions
#Min-max normalize to [0, 1]
def _minmax_0_1(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    vmin = s.min(skipna=True)
    vmax = s.max(skipna=True)
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        return s.where(s.isna(), 0.0)
    return (s - vmin) / (vmax - vmin)


def _sanitize_metric_for_filename(metric: str) -> str:
    return (
        metric.strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("__", "_")
    )

#Reduce raw ATVA results to one point per (scenario, scheme) for a variant."""
def _prepare_variant_tradeoff_rows(
    df: pd.DataFrame,
    *,
    variant: str,
    x_fraction_col: str,
    x_gain_col: str,
) -> pd.DataFrame:

    needed = {"scenario", "scheme", "variant", "baseline_mean_happiness", x_fraction_col, x_gain_col}
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(
            f"CSV missing required columns for {variant} tradeoff plots: {sorted(missing)}"
        )

    dfv = df[df["variant"] == variant].copy()
    if dfv.empty:
        raise SystemExit(f"No rows found in CSV for variant '{variant}'.")

    agg = (
        dfv.groupby(["scenario", "scheme"], observed=True)
        .agg(
            baseline_mean_happiness=("baseline_mean_happiness", "mean"),
            x_fraction=(x_fraction_col, "mean"),
            x_gain=(x_gain_col, "mean"),
        )
        .reset_index()
    )

    agg["H_mean"] = _minmax_0_1(agg["baseline_mean_happiness"])
    agg["x_fraction_norm"] = _minmax_0_1(agg["x_fraction"])
    agg["x_gain_norm"] = _minmax_0_1(agg["x_gain"])

    return agg


def _plot_tradeoff_scatter(
    df: pd.DataFrame,
    *,
    out_path: Path,
    title: str,
    x_label: str,
) -> None:
    rng = np.random.default_rng(0)
    jitter = 0.01

    plt.figure(figsize=(7, 5))
    for scheme, g in df.groupby("scheme", observed=True):
        x = pd.to_numeric(g["risk_fraction_change_winner"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["H_mean"], errors="coerce").to_numpy()

        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = np.clip(y + rng.normal(0.0, jitter, size=len(y)), 0.0, 1.0)

        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("H_mean (normalized)")
    plt.xlim(0.0, 1.0)
    plt.ylim(0.0, 1.0)
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()


def _plot_happiness_vs_avg_gain_scatter(
    df: pd.DataFrame,
    *,
    out_path: Path,
    title: str,
    x_label: str,
) -> None:
    rng = np.random.default_rng(0)
    jitter = 0.01

    plt.figure(figsize=(7, 5))
    for scheme, g in df.groupby("scheme", observed=True):
        x = pd.to_numeric(g["risk_avg_gain_all_options"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["H_mean"], errors="coerce").to_numpy()

        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = np.clip(y + rng.normal(0.0, jitter, size=len(y)), 0.0, 1.0)

        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("H_mean (normalized)")
    plt.xlim(0.0, 1.0)
    plt.ylim(0.0, 1.0)
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()


def _maybe_rename_legacy_outputs(out_dir: Path) -> None:
    legacy = {
        "tradeoff_h_mean_vs_risk_fraction.png": "tradeoff_atva1_h_mean_vs_fraction_coalitions_change_winner.png",
        "tradeoff_h_mean_vs_risk_avg_gain.png": "tradeoff_atva1_h_mean_vs_avg_coalition_gain.png",
    }

    for src, dst in legacy.items():
        src_path = out_dir / src
        dst_path = out_dir / dst
        if src_path.exists() and not dst_path.exists():
            src_path.rename(dst_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plot ATVA trade-off figures from an ATVA results CSV")
    parser.add_argument(
        "--csv",
        type=Path,
        default=_default_results_csv(),
        help="Path to ATVA results CSV (default: newest experiments/atva_results_*.csv)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("experiments/atva_plots"),
        help="Directory to write trade-off PNG plots into",
    )
    args = parser.parse_args(argv)

    if not args.csv.exists():
        raise SystemExit(f"CSV file not found: {args.csv}")

    df_raw = _read_results(args.csv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _maybe_rename_legacy_outputs(args.out_dir)

    variant_defs: dict[str, tuple[str, str]] = {
        # ATVA-1 (collusion)
        "atva1": ("fraction_coalitions_change_winner", "avg_coalition_gain"),
        # ATVA-2 (counter-strategic)
        "atva2": ("fraction_manip_with_response", "avg_sequence_length"),
        # ATVA-3 (imperfect knowledge)
        "atva3": ("fraction_robust_options", "avg_expected_gain"),
        # ATVA-4 (multiple tactical)
        "atva4": ("fraction_some_hurt", "avg_happiness_change"),
    }

    for variant, (x_fraction_col, x_gain_col) in variant_defs.items():
        df_trade = _prepare_variant_tradeoff_rows(
            df_raw,
            variant=variant,
            x_fraction_col=x_fraction_col,
            x_gain_col=x_gain_col,
        )
        df_trade["H_mean"] = _minmax_0_1(df_trade["baseline_mean_happiness"])
        df_trade["risk_fraction_change_winner"] = _minmax_0_1(df_trade["x_fraction"])
        df_trade["risk_avg_gain_all_options"] = _minmax_0_1(df_trade["x_gain"])

        frac_name = _sanitize_metric_for_filename(x_fraction_col)
        gain_name = _sanitize_metric_for_filename(x_gain_col)

        _plot_tradeoff_scatter(
            df_trade,
            out_path=args.out_dir / f"tradeoff_{variant}_h_mean_vs_risk_fraction__{frac_name}.png",
            title=f"{variant.upper()}: Happiness vs Tactical-Voting Risk (Normalized 0–1)",
            x_label=f"risk_fraction (={x_fraction_col}) normalized",
        )
        _plot_happiness_vs_avg_gain_scatter(
            df_trade,
            out_path=args.out_dir / f"tradeoff_{variant}_h_mean_vs_risk_avg_gain__{gain_name}.png",
            title=f"{variant.upper()}: Happiness vs Tactical-Voting Risk (Normalized 0–1)",
            x_label=f"risk_avg_gain (={x_gain_col}) normalized",
        )

    print(f"Wrote trade-off plots to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
