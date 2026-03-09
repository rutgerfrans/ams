from __future__ import annotations

from dataclasses import dataclass

from .happiness import HappinessResult
from .strategies import StrategicBallot

# this function is the main data structure for representing strategic-voting options for voters, and their associated outcomes/happiness.
@dataclass(frozen=True)
class StrategicOption:

    voter_index: int
    strategy_kind: str
    tactical_ballot: StrategicBallot

    strategic_outcome: str
    baseline_outcome: str

    strategic_happiness: HappinessResult
    baseline_happiness: HappinessResult

    @property
    def H_tilde_i(self) -> float:
        return self.strategic_happiness.per_voter[self.voter_index]

    @property
    def H_i(self) -> float:
        return self.baseline_happiness.per_voter[self.voter_index]

    @property
    def H_tilde(self) -> float:
        return self.strategic_happiness.total

    @property
    def H(self) -> float:
        return self.baseline_happiness.total
