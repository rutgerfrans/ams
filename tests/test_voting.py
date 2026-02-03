import pytest

from btva.models import VotingScheme, VotingSituation
from btva.voting import scoring_vector, tally_votes


def test_scoring_vectors() -> None:
    assert scoring_vector(VotingScheme.PLURALITY, 4) == [1, 0, 0, 0]
    assert scoring_vector(VotingScheme.VOTE_FOR_TWO, 4) == [1, 1, 0, 0]
    assert scoring_vector(VotingScheme.ANTI_PLURALITY, 4) == [1, 1, 1, 0]
    assert scoring_vector(VotingScheme.BORDA, 4) == [3, 2, 1, 0]


def test_tally_plurality_tie_break_lexicographic() -> None:
    # 3 voters, 3 alternatives.
    # Each alternative gets exactly one first-place vote => tie, pick lexicographically smallest: A
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C"),
            ("B", "C", "A"),
            ("C", "B", "A"),
        )
    )
    out = tally_votes(VotingScheme.PLURALITY, situation)
    assert out.scores == {"A": 1, "B": 1, "C": 1}
    assert out.winner == "A"


def test_tally_borda_simple() -> None:
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C"),
            ("A", "C", "B"),
            ("B", "A", "C"),
        )
    )
    out = tally_votes(VotingScheme.BORDA, situation)
    # Borda vector for m=3 is [2,1,0]
    # V1: A2 B1 C0
    # V2: A2 C1 B0
    # V3: B2 A1 C0
    # Totals: A5 B3 C1
    assert out.scores["A"] == 5
    assert out.winner == "A"


def test_invalid_situation_rejected() -> None:
    situation = VotingSituation(voters_preferences=(("A", "B", "C"), ("A", "B", "C")))
    with pytest.raises(ValueError):
        tally_votes(VotingScheme.PLURALITY, situation)
