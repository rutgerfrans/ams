from __future__ import annotations

from dataclasses import dataclass

from .happiness import HappinessResult
from .strategies import StrategicBallot


@dataclass(frozen=True)
class StrategicOption:
    """One strategic-voting option s_ij for voter i.

    Matches the assignment's tuple (with our concrete representations):

        s_ij = (v~_ij, O~, H~_i, H_i, H~, H)

    Where:
    - v~_ij: tactically modified preference list (StrategicBallot)
    - O~: outcome under v~_ij (winner)
    - H~_i: happiness of voter i under O~
    - H_i: baseline happiness of voter i under O
    - H~: overall happiness under O~
    - H: baseline overall happiness under O

    Notes:
    - We store full per-voter happiness vectors for baseline/strategic to keep
      it easy to compute H/H~ and to print/debug later.
    """

    voter_index: int
    # Distinguishes which tactic generated this option (e.g. "compromising_burying", "bullet").
    strategy_kind: str
    tactical_ballot: StrategicBallot

    strategic_outcome: str  # O~
    baseline_outcome: str  # O

    strategic_happiness: HappinessResult  # contains (H~_1..H~_n) and H~
    baseline_happiness: HappinessResult  # contains (H_1..H_n) and H

    @property
    def H_tilde_i(self) -> int:
        return self.strategic_happiness.per_voter[self.voter_index]

    @property
    def H_i(self) -> int:
        return self.baseline_happiness.per_voter[self.voter_index]

    @property
    def H_tilde(self) -> int:
        return self.strategic_happiness.total

    @property
    def H(self) -> int:
        return self.baseline_happiness.total
