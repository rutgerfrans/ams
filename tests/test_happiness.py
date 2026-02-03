from __future__ import annotations

from btva.happiness import borda_happiness_for_outcome
from btva.models import VotingSituation


def test_borda_happiness_for_outcome() -> None:
    # 3 voters, 4 alternatives
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C", "D"),
            ("B", "A", "D", "C"),
            ("D", "C", "B", "A"),
        )
    )

    # winner O = B
    res = borda_happiness_for_outcome(situation, "B")

    # m=4 => top=3, second=2, third=1, last=0
    # voter1 rank(B)=1 => 2
    # voter2 rank(B)=0 => 3
    # voter3 rank(B)=2 => 1
    assert res.outcome == "B"
    assert res.per_voter == (2, 3, 1)
    assert res.total == 6
