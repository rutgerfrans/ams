# !!!for convenience tests were generated with llm support.!!!
from __future__ import annotations

import pytest

from btva.models import VotingScheme, VotingSituation
from btva.strategies import apply_bullet_vote, apply_compromise_or_bury
from btva.voting import tally_votes_strategic


def test_compromise_or_bury_move_any_positions() -> None:
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C", "D"),
            ("A", "B", "C", "D"),
            ("A", "B", "C", "D"),
        )
    )

    # Move D to the top; move B to the bottom.
    b = apply_compromise_or_bury(
        situation,
        0,
        move_up="D",
        move_up_to=0,
        move_down="B",
        move_down_to=3,
    )
    assert b.preferences == ("D", "A", "C", "B")


def test_bullet_vote_rejected_for_plurality() -> None:
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C"),
            ("B", "C", "A"),
            ("C", "A", "B"),
        )
    )

    with pytest.raises(ValueError):
        apply_bullet_vote(situation, VotingScheme.PLURALITY, 0, chosen="A")


def test_tally_with_bullet_vote_borda_only_chosen_scores() -> None:
    # 3 voters, 3 alternatives.
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C"),
            ("B", "C", "A"),
            ("C", "A", "B"),
        )
    )

    # Voter 0 bullet-votes for A under Borda => adds 2 points to A and 0 to others.
    out = tally_votes_strategic(
        VotingScheme.BORDA,
        situation,
        bullet_choice_by_voter={0: "A"},
    )

    # Baseline Borda totals without bullet would be A=3, B=3, C=3.
    # With bullet for voter0:
    # - voter0 contributes A=2 only
    # - voter1: B=2, C=1, A=0
    # - voter2: C=2, A=1, B=0
    # Totals: A=3, B=2, C=3 (tie A/C => lexicographic winner A)
    assert out.scores == {"A": 3, "B": 2, "C": 3}
    assert out.winner == "A"
