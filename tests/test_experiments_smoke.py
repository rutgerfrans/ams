# !!!for convenience tests were generated with llm support.!!!
from __future__ import annotations

import csv
from pathlib import Path

from btva.experiments import run_experiments, write_csv
from btva.models import VotingScheme


def test_experiments_smoke_writes_csv(tmp_path: Path) -> None:
    scenarios_dir = Path(__file__).parent.parent / "voting_scenarios"

    scenario_files = [
        scenarios_dir / "sv_poll_1_small.abif",
        scenarios_dir / "edge_case_tie_all.abif",
    ]

    rows = run_experiments(
        scenario_files=scenario_files,
        schemes=[VotingScheme.PLURALITY, VotingScheme.BORDA],
        max_m=8,
    )

    # 2 scenarios * 2 schemes
    assert len(rows) == 4

    out_path = tmp_path / "results.csv"
    write_csv(rows, out_path)

    assert out_path.exists()

    with out_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        got = list(reader)

    assert len(got) == 4

    # Basic headers we rely on for plotting.
    for key in [
        "scenario",
        "m",
        "n",
        "scheme",
        "winner",
        "H_total",
        "H_mean",
        "H_total_tactical",
        "H_mean_tactical",
        "avg_individual_gain_over_tactics",
        "avg_delta_H_total_over_tactics",
        "risk_avg_gain_all_options",
        "risk_fraction_change_winner",
        "tactical_options_total",
    ]:
        assert key in reader.fieldnames
