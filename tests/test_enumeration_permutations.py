from __future__ import annotations

from btva.enumeration import enumerate_all_permutations_options_for_voter
from btva.enumeration_bullet import enumerate_bullet_options_for_voter
from btva.models import VotingScheme, VotingSituation


def test_enumerate_all_permutations_options_for_voter_m3() -> None:
    # Keep m=3 so 3! = 6 permutations; minus sincere => 5 options.
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C"),
            ("B", "C", "A"),
            ("C", "A", "B"),
        )
    )

    opts = enumerate_all_permutations_options_for_voter(VotingScheme.PLURALITY, situation, 0)
    assert len(opts) == 5

    # Sanity: every option in opts should target the right voter.
    assert all(o.voter_index == 0 for o in opts)


def test_enumerate_bullet_options_for_voter_m3_borda() -> None:
    situation = VotingSituation(
        voters_preferences=(
            ("A", "B", "C"),
            ("B", "C", "A"),
            ("C", "A", "B"),
        )
    )

    opts = enumerate_bullet_options_for_voter(VotingScheme.BORDA, situation, 0)
    # For m=3 there are 3 possible bullet choices.
    assert len(opts) == 3
    assert set(o.strategy_kind for o in opts) == {"bullet"}
