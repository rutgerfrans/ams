from __future__ import annotations

from enum import Enum
from dataclasses import dataclass

from .models import VotingSituation


class HappinessMetric(str, Enum):
    BORDA = "borda"
    RANK_NORMALIZED = "rank_normalized"


@dataclass(frozen=True)
class HappinessResult:
    """Happiness metrics for a fixed outcome winner O.

    We follow the assignment's notation:
    - O: the non-strategic outcome (winner)
    - H_i: happiness for voter i
    - H: overall happiness (sum_i H_i)

    The definition of H_i is provided by this module.
    """

    outcome: str  # O
    per_voter: tuple[float, ...]  # (H_1, ..., H_n)

    @property
    def total(self) -> int:
        return sum(self.per_voter)


def borda_happiness_for_outcome(
    situation: VotingSituation, outcome: str
) -> HappinessResult:
    """Compute per-voter happiness using Borda utility of the outcome.

    Definition (Borda-based): for each voter i, let rank_i(O) be the 0-based
    position of the outcome O in the voter's true preference list (0 = top).

    With m alternatives, define:
        H_i = (m - 1) - rank_i(O)

    So:
    - top-ranked winner => H_i = m-1
    - bottom-ranked winner => H_i = 0

    This is exactly the Borda score that voter i assigns to the winner.

    Returns a HappinessResult containing (O, (H_1..H_n)).
    """

    situation.validate()

    if outcome not in situation.alternatives:
        raise ValueError(f"Outcome '{outcome}' is not a valid alternative.")

    m = situation.m_alternatives
    per_voter: list[float] = []
    for pref in situation.voters_preferences:
        rank = pref.index(outcome)
        per_voter.append(float((m - 1) - rank))

    return HappinessResult(outcome=outcome, per_voter=tuple(per_voter))


def rank_normalized_happiness_for_outcome(
    situation: VotingSituation, outcome: str
) -> HappinessResult:
    """Compute per-voter happiness using rank-based normalized utility.

    Definition: for each voter i, let rank_i(O) be the 0-based position
    of outcome O in i's true preference list (0 = top).

    With m alternatives, define:

        H_i = 1 - rank_i(O)/(m-1)

    So:
    - top-ranked winner => H_i = 1.0
    - bottom-ranked winner => H_i = 0.0

    This is rank-based and scale-free, avoiding Borda point magnitudes.
    """

    situation.validate()

    if outcome not in situation.alternatives:
        raise ValueError(f"Outcome '{outcome}' is not a valid alternative.")

    m = situation.m_alternatives
    denom = max(1, m - 1)
    per_voter: list[float] = []
    for pref in situation.voters_preferences:
        rank = pref.index(outcome)
        per_voter.append(1.0 - (rank / denom))

    return HappinessResult(outcome=outcome, per_voter=tuple(per_voter))


def happiness_for_outcome(
    situation: VotingSituation,
    outcome: str,
    *,
    metric: HappinessMetric = HappinessMetric.BORDA,
) -> HappinessResult:
    if metric == HappinessMetric.BORDA:
        return borda_happiness_for_outcome(situation, outcome)
    if metric == HappinessMetric.RANK_NORMALIZED:
        return rank_normalized_happiness_for_outcome(situation, outcome)
    raise ValueError(f"Unknown happiness metric: {metric}")
