from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class VotingScheme(str, Enum):
    """Voting schemes supported by the assignment (Part II.1)."""

    PLURALITY = "plurality"  # {1,0,...,0}
    VOTE_FOR_TWO = "vote_for_two"  # {1,1,0,...,0}
    ANTI_PLURALITY = "anti_plurality"  # {1,1,...,0}
    BORDA = "borda"  # {m-1,m-2,...,0}


# Strategic voting types mentioned in the assignment.
# The assignment notes that compromising/burying can be treated as equivalent.
class StrategicVotingType(str, Enum):
    COMPROMISE_OR_BURY = "compromise_or_bury"
    BULLET = "bullet"


@dataclass(frozen=True)
class VotingSituation:
    """Matrix of true preferences: m alternatives x n voters.

    We represent preferences as a list/tuple of voters, where each voter is a
    complete ranking of alternatives from most preferred to least preferred.

    Example (3 voters, 4 alternatives):
        voters_preferences = [
            ("C", "B", "A", "D"),
            ("A", "B", "D", "C"),
            ("B", "A", "C", "D"),
        ]

    Constraints (assignment): m,n > 2.
    """

    voters_preferences: tuple[tuple[str, ...], ...]

    @property
    def n_voters(self) -> int:
        return len(self.voters_preferences)

    @property
    def m_alternatives(self) -> int:
        return len(self.voters_preferences[0]) if self.voters_preferences else 0

    @property
    def alternatives(self) -> tuple[str, ...]:
        return self.voters_preferences[0] if self.voters_preferences else tuple()

    def validate(self) -> None:
        if self.n_voters <= 2:
            raise ValueError("VotingSituation must have n > 2 voters.")
        if self.m_alternatives <= 2:
            raise ValueError("VotingSituation must have m > 2 alternatives.")

        expected_alts = set(self.voters_preferences[0])
        if len(expected_alts) != self.m_alternatives:
            raise ValueError("Alternatives must be unique within a preference list.")

        for idx, pref in enumerate(self.voters_preferences):
            if len(pref) != self.m_alternatives:
                raise ValueError(
                    f"Voter {idx} has {len(pref)} ranked alternatives, expected {self.m_alternatives}."
                )
            if set(pref) != expected_alts:
                missing = expected_alts - set(pref)
                extra = set(pref) - expected_alts
                raise ValueError(
                    f"Voter {idx} must rank exactly the same alternatives. Missing={missing}, extra={extra}."
                )
