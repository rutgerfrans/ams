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
    # With m=3, each voter has 3! - 1 = 5 permutation options (excluding sincere ballot).
    # Under plurality, bullet voting is not allowed, so S_i contains permutations only.
    assert "S_0: 5 options (permutation=5)" in out
    assert "S_1: 5 options (permutation=5)" in out
    assert "S_2: 5 options (permutation=5)" in out


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
    assert "S_0: 5 options" in out
    # Verify at least one option tuple line is printed.
    assert "s_0,0:" in out
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
        "--profitable2",
    ])
    assert rc == 0

    out = capsys.readouterr().out
    assert "scheme:" in out
    assert "S_0:" in out
