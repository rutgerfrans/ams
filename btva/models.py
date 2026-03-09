from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

#voting schemes
class VotingScheme(str, Enum):
    PLURALITY = "plurality"  # {1,0,...,0}
    VOTE_FOR_TWO = "vote_for_two"  # {1,1,0,...,0}
    ANTI_PLURALITY = "anti_plurality"  # {1,1,...,0}
    BORDA = "borda"  # {m-1,m-2,...,0}


# Strategic voting types compromise/bury and bullet voting 
class StrategicVotingType(str, Enum):
    COMPROMISE_OR_BURY = "compromise_or_bury"
    BULLET = "bullet"


@dataclass(frozen=True)
class VotingSituation:
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
                raise ValueError(f"Voter {idx} has {len(pref)} ranked alternatives, expected {self.m_alternatives}.")
            if set(pref) != expected_alts:
                missing = expected_alts - set(pref)
                extra = set(pref) - expected_alts
                raise ValueError(f"Voter {idx} must rank exactly the same alternatives. Missing={missing}, extra={extra}.")
