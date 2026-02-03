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

    rc = main([str(p), "--scheme", "plurality", "--show-scores"])
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
