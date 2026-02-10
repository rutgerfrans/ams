from __future__ import annotations

from pathlib import Path

from btva.cli import main


def test_cli_smoke_abif(tmp_path: Path, capsys) -> None:
    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
1:0>1>2
1:1>2>0
1:2>0>1
"""
    p = tmp_path / "x.abif"
    p.write_text(content, encoding="utf-8")

    rc = main([str(p), "--scheme", "plurality"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "scheme: plurality" in out
    # Everyone gets 1 first-place, so lexicographic winner is "0".
    assert "winner: 0" in out
    # m=3, winner=0. Happiness per voter is Borda-based: top=2, mid=1, last=0.
    # V1: 0>1>2 => 2
    # V2: 1>2>0 => 0
    # V3: 2>0>1 => 1
    assert "H_i: [2, 0, 1]" in out
    assert "H: 3" in out


def test_cli_enumerate_strategies_m3(tmp_path: Path, capsys) -> None:
    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
1:0>1>2
1:1>2>0
1:2>0>1
"""
    p = tmp_path / "x.abif"
    p.write_text(content, encoding="utf-8")

    rc = main([str(p), "--scheme", "plurality", "--max-m", "3"])
    assert rc == 0

    out = capsys.readouterr().out
    # Under Option A, S_i contains only tactical options (H~_i > H_i), so counts can be
    # smaller than the raw number of enumerated deviations.
    assert "S_0:" in out
    assert "S_1:" in out
    assert "S_2:" in out
    # At least one voter should have at least one tactical option in this profile.
    assert "S_1: 0 options" not in out


def test_cli_show_strategies_prints_option_lines(tmp_path: Path, capsys) -> None:
    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
1:0>1>2
1:1>2>0
1:2>0>1
"""
    p = tmp_path / "x.abif"
    p.write_text(content, encoding="utf-8")

    rc = main(
        [
            str(p),
            "--scheme",
            "plurality",
            "--max-m",
            "3",
            "--strategy-limit",
            "2",
        ]
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "S_0:" in out
    # Verify at least one option tuple line is printed.
    assert "s_" in out
    assert "O~=" in out
    assert "H~_i=" in out
    # The CLI should not emit a truncation summary line.
    assert "more not shown" not in out


def test_cli_profitable_flag_runs(tmp_path: Path, capsys) -> None:
    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
1:0>1>2
1:1>2>0
1:2>0>1
"""
    p = tmp_path / "x.abif"
    p.write_text(content, encoding="utf-8")

    rc = main([
        str(p),
        "--scheme",
        "plurality",
        "--max-m",
        "3",
        "--profitable",
    ])
    assert rc == 0

    out = capsys.readouterr().out
    assert "scheme:" in out
    assert "S_0:" in out


def test_cli_prints_risk_line(tmp_path: Path, capsys) -> None:
    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
1:0>1>2
1:1>2>0
1:2>0>1
"""
    p = tmp_path / "x.abif"
    p.write_text(content, encoding="utf-8")

    rc = main([
        str(p),
        "--scheme",
        "plurality",
        "--max-m",
        "3",
        "--risk-method",
        "avg_gain_all_options",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "risk (avg_gain_all_options):" in out

    rc = main([
        str(p),
        "--scheme",
        "plurality",
        "--max-m",
        "3",
        "--risk-method",
        "fraction_change_winner",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "risk (fraction_change_winner):" in out


def test_cli_risk_is_printed_with_profitable_flag(tmp_path: Path, capsys) -> None:
    """--profitable is a display-only flag; risk is still reported (computed over tactical options)."""

    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
1:0>1>2
1:1>2>0
1:2>0>1
"""
    p = tmp_path / "x.abif"
    p.write_text(content, encoding="utf-8")

    rc = main([
        str(p),
        "--scheme",
        "plurality",
        "--max-m",
        "3",
        "--risk-method",
        "avg_gain_all_options",
        "--profitable",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "risk (avg_gain_all_options):" in out
