from __future__ import annotations

from pathlib import Path

import pytest

from btva.parsing import load_input_file


def test_load_abif_parses_strict_ballots(tmp_path: Path) -> None:
    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
2:2>1>0
1:0>1>2
"""
    p = tmp_path / "x.abif"
    p.write_text(content, encoding="utf-8")

    parsed = load_input_file(p)
    # 2 + 1 voters expanded
    assert len(parsed.situation.voters_preferences) == 3
    assert parsed.situation.voters_preferences[0] == ("2", "1", "0")
    assert parsed.situation.voters_preferences[-1] == ("0", "1", "2")


def test_load_abif_linearizes_ties(tmp_path: Path) -> None:
    content = """\
# 3 candidates
=0 : [0]
=1 : [1]
=2 : [2]
    1:2>1=0
    1:0>1>2
    1:1>2>0
"""
    p = tmp_path / "bad.abif"
    p.write_text(content, encoding="utf-8")

    parsed = load_input_file(p)
    assert parsed.situation.voters_preferences[0] == ("2", "1", "0")
