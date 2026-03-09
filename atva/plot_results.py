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
    df = df.sort_values(["scenario", "scheme", "variant"], kind="stable")

    return df


def _minmax_0_1(series: pd.Series) -> pd.Series:
    """Min-max normalize to [0, 1]."""
    s = pd.to_numeric(series, errors="coerce")
    vmin = s.min(skipna=True)
    vmax = s.max(skipna=True)
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        return s.where(s.isna(), 0.0)
    return (s - vmin) / (vmax - vmin)


def _plot_atva1_metrics(df: pd.DataFrame, *, out_dir: Path) -> None:
    """Plot ATVA-1 coalition analysis metrics."""
    df1 = df[df["variant"] == "atva1"].copy()
    if df1.empty:
        return

    rng = np.random.default_rng(0)
    jitter = 0.01

    # Plot Coalition size needed to change winner
    plt.figure(figsize=(7, 5))
    for scheme, g in df1.groupby("scheme", observed=True):
        x = pd.to_numeric(g["baseline_mean_happiness"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["max_coalition_size_changes_winner"], errors="coerce").to_numpy()
        
        xj = x + rng.normal(0.0, jitter, size=len(x))
        yj = y + rng.normal(0.0, jitter * 0.1, size=len(y))
        
        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)
    
    plt.title("ATVA-1: Baseline Happiness vs Min Coalition Size to Change Winner")
    plt.xlabel("Baseline Mean Happiness")
    plt.ylabel("Min Coalition Size to Change Winner")
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "atva1_coalition_size.png", dpi=200)
    plt.close()

    # Plot Coalition vulnerability
    plt.figure(figsize=(7, 5))
    for scheme, g in df1.groupby("scheme", observed=True):
        x = pd.to_numeric(g["fraction_coalitions_change_winner"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["avg_coalition_gain"], errors="coerce").to_numpy()
        
        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = y + rng.normal(0.0, jitter, size=len(y))
        
        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)
    
    plt.title("ATVA-1: Coalition Success Rate vs Average Coalition Gain")
    plt.xlabel("Fraction of Coalitions that Change Winner")
    plt.ylabel("Average Coalition Happiness Gain")
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    plt.savefig(out_dir / "atva1_coalition_vulnerability.png", dpi=200)
    plt.close()


def _plot_atva2_metrics(df: pd.DataFrame, *, out_dir: Path) -> None:
    """Plot ATVA-2 counter-strategic voting metrics."""
    df2 = df[df["variant"] == "atva2"].copy()
    if df2.empty:
        return

    rng = np.random.default_rng(0)
    jitter = 0.01

    # Plot Counter-response likelihood vs sequence length
    plt.figure(figsize=(7, 5))
    for scheme, g in df2.groupby("scheme", observed=True):
        x = pd.to_numeric(g["fraction_manip_with_response"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["avg_sequence_length"], errors="coerce").to_numpy()
        
        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = y + rng.normal(0.0, jitter * 0.1, size=len(y))
        
        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)
    
    plt.title("ATVA-2: Counter-Response Rate vs Average Sequence Length")
    plt.xlabel("Fraction of Manipulations with Counter-Response")
    plt.ylabel("Average Sequence Length")
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "atva2_counter_strategic.png", dpi=200)
    plt.close()


def _plot_atva3_metrics(df: pd.DataFrame, *, out_dir: Path) -> None:
    """Plot ATVA-3 imperfect knowledge metrics."""
    df3 = df[df["variant"] == "atva3"].copy()
    if df3.empty:
        return

    rng = np.random.default_rng(0)
    jitter = 0.01

    # Plot Robustness vs regret
    plt.figure(figsize=(7, 5))
    for scheme, g in df3.groupby("scheme", observed=True):
        x = pd.to_numeric(g["fraction_robust_options"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["avg_regret"], errors="coerce").to_numpy()
        
        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = y + rng.normal(0.0, jitter, size=len(y))
        
        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)
    
    plt.title("ATVA-3: Robustness vs Regret Under Uncertainty")
    plt.xlabel("Fraction of Robust Options")
    plt.ylabel("Average Regret")
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "atva3_uncertainty.png", dpi=200)
    plt.close()


def _plot_atva4_metrics(df: pd.DataFrame, *, out_dir: Path) -> None:
    """Plot ATVA-4 multiple tactical voters metrics."""
    df4 = df[df["variant"] == "atva4"].copy()
    if df4.empty:
        return

    rng = np.random.default_rng(0)
    jitter = 0.01

    # Plot Mutual benefit vs harm
    plt.figure(figsize=(7, 5))
    for scheme, g in df4.groupby("scheme", observed=True):
        x = pd.to_numeric(g["fraction_all_benefit"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["fraction_some_hurt"], errors="coerce").to_numpy()
        
        xj = np.clip(x + rng.normal(0.0, jitter, size=len(x)), 0.0, 1.0)
        yj = np.clip(y + rng.normal(0.0, jitter, size=len(y)), 0.0, 1.0)
        
        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)
    
    plt.title("ATVA-4: Tactical Voters Benefiting vs Hurting Themselves")
    plt.xlabel("Fraction Where All Tactical Voters Benefit")
    plt.ylabel("Fraction Where Some Tactical Voters Hurt Themselves")
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "atva4_tactical_interference.png", dpi=200)
    plt.close()

    # Plot Total happiness impact
    plt.figure(figsize=(7, 5))
    for scheme, g in df4.groupby("scheme", observed=True):
        x = pd.to_numeric(g["baseline_mean_happiness"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["avg_happiness_change"], errors="coerce").to_numpy()
        
        xj = x + rng.normal(0.0, jitter, size=len(x))
        yj = y + rng.normal(0.0, jitter, size=len(y))
        
        plt.scatter(xj, yj, label=str(scheme), alpha=0.6, s=30)
    
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.title("ATVA-4: Baseline Happiness vs Average Total Happiness Change")
    plt.xlabel("Baseline Mean Happiness")
    plt.ylabel("Average Total Happiness Change (Multi-Tactical)")
    plt.legend(title="scheme", loc="best")
    plt.tight_layout()
    plt.savefig(out_dir / "atva4_happiness_impact.png", dpi=200)
    plt.close()


def _plot_variant_comparison(df: pd.DataFrame, *, out_dir: Path) -> None:
    """Compare all variants side-by-side."""
    if df.empty:
        return

    # Bar chart Average execution time by variant
    plt.figure(figsize=(8, 5))
    variant_times = df.groupby("variant", observed=True)["time_seconds"].mean()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    variant_times.plot(kind='bar', color=colors[:len(variant_times)])
    
    plt.title("Average Execution Time by ATVA Variant")
    plt.xlabel("ATVA Variant")
    plt.ylabel("Average Time (seconds)")
    plt.xticks(rotation=0)
    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "variant_comparison_time.png", dpi=200)
    plt.close()

    # Compare baseline happiness across variants (should be identical)
    plt.figure(figsize=(8, 5))
    for variant, g in df.groupby("variant", observed=True):
        scheme_happiness = g.groupby("scheme", observed=True)["baseline_mean_happiness"].mean()
        plt.plot(scheme_happiness.index, scheme_happiness.values, marker='o', label=str(variant), alpha=0.7)
    
    plt.title("Baseline Mean Happiness by Scheme (Across Variants)")
    plt.xlabel("Voting Scheme")
    plt.ylabel("Mean Baseline Happiness")
    plt.legend(title="variant", loc="best")
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(out_dir / "variant_comparison_baseline.png", dpi=200)
    plt.close()


def _plot_scheme_comparison(df: pd.DataFrame, *, out_dir: Path) -> None:
    """Compare schemes across key ATVA metrics."""
    if df.empty:
        return

    # Get average metrics by scheme across all variants
    metrics_by_scheme = {}
    
    for scheme in df["scheme"].unique():
        scheme_df = df[df["scheme"] == scheme]
        metrics_by_scheme[scheme] = {
            # ATVA-1
            "coalition_vulnerability": scheme_df[scheme_df["variant"] == "atva1"]["fraction_coalitions_change_winner"].mean(),
            # ATVA-2
            "counter_response_rate": scheme_df[scheme_df["variant"] == "atva2"]["fraction_manip_with_response"].mean(),
            # ATVA-3
            "robust_fraction": scheme_df[scheme_df["variant"] == "atva3"]["fraction_robust_options"].mean(),
            # ATVA-4
            "mutual_benefit": scheme_df[scheme_df["variant"] == "atva4"]["fraction_all_benefit"].mean(),
        }
    
    # Create radar chart
    categories = ["Coalition\nVulnerability", "Counter-Response\nRate", "Robust\nOptions", "Mutual\nBenefit"]
    N = len(categories)
    
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    colors = {'plurality': '#1f77b4', 'vote_for_two': '#ff7f0e', 
              'anti_plurality': '#2ca02c', 'borda': '#d62728'}
    
    for scheme, metrics in metrics_by_scheme.items():
        values = [
            metrics["coalition_vulnerability"],
            metrics["counter_response_rate"],
            metrics["robust_fraction"],
            metrics["mutual_benefit"],
        ]
        values += values[:1]
        
        ax.plot(angles, values, 'o-', linewidth=2, label=scheme, 
                color=colors.get(scheme, '#888888'), alpha=0.7)
        ax.fill(angles, values, alpha=0.15, color=colors.get(scheme, '#888888'))
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 1)
    ax.set_title("Scheme Comparison Across ATVA Metrics", y=1.08, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.grid(True)
    
    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "scheme_comparison_radar.png", dpi=200, bbox_inches='tight')
    plt.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plot ATVA experiment CSV results")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to results CSV (default: newest experiments/atva_results_*.csv if present)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("experiments/atva_plots"),
        help="Directory to write PNG plots into",
    )
    args = parser.parse_args(argv)

    csv_path = args.csv if args.csv else _default_results_csv()
    
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        print("Run experiments first: python -m atva.experiments [options]")
        return 1
    
    print(f"Reading results from: {csv_path}")
    df = _read_results(csv_path)
    
    print(f"Found {len(df)} rows with {df['variant'].nunique()} variants, "
          f"{df['scheme'].nunique()} schemes, {df['scenario'].nunique()} scenarios")

    print("Creating ATVA-1 plots...")
    _plot_atva1_metrics(df, out_dir=args.out_dir)
    
    print("Creating ATVA-2 plots...")
    _plot_atva2_metrics(df, out_dir=args.out_dir)
    
    print("Creating ATVA-3 plots...")
    _plot_atva3_metrics(df, out_dir=args.out_dir)
    
    print("Creating ATVA-4 plots...")
    _plot_atva4_metrics(df, out_dir=args.out_dir)
    
    print("Creating variant comparison plots...")
    _plot_variant_comparison(df, out_dir=args.out_dir)
    
    print("Creating scheme comparison plots...")
    _plot_scheme_comparison(df, out_dir=args.out_dir)
    
    print(f"\nPlots saved to: {args.out_dir}")
    print("\nGenerated plots:")
    for plot_file in sorted(args.out_dir.glob("*.png")):
        print(f"  - {plot_file.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
