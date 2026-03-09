# !!!for convenience tests were generated with llm support.!!!
from __future__ import annotations

from btva.happiness import rank_normalized_happiness_for_outcome
from btva.models import VotingSituation


def test_rank_normalized_happiness_basic() -> None:
    # 3 alternatives => denom = m-1 = 2
    # For outcome "0":
    # - rank 0 => 1.0
    # - rank 1 => 0.5
    # - rank 2 => 0.0
    situation = VotingSituation(
        voters_preferences=(
            ("0", "1", "2"),
            ("1", "0", "2"),
            ("2", "1", "0"),
        ),
    )

    happy = rank_normalized_happiness_for_outcome(situation, "0")
    assert happy.per_voter == (1.0, 0.5, 0.0)
    assert happy.total == 1.5
