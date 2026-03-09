from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from .models import VotingSituation

class HappinessMetric(str, Enum):
    BORDA = "borda"
    RANK_NORMALIZED = "rank_normalized"

#happiness metrics for a fixed outcome winner
@dataclass(frozen=True)
class HappinessResult:
    outcome: str
    per_voter: tuple[float, ...]

    @property
    def total(self) -> float:
        return float(sum(self.per_voter))

# compute per-voter happiness using Borda utility of the outcome
def borda_happiness_for_outcome(
    situation: VotingSituation, outcome: str
) -> HappinessResult:

    situation.validate()

    if outcome not in situation.alternatives:
        raise ValueError(f"Outcome '{outcome}' is not a valid alternative.")

    m = situation.m_alternatives
    per_voter: list[float] = []
    for pref in situation.voters_preferences:
        rank = pref.index(outcome)
        per_voter.append(float((m - 1) - rank))

    return HappinessResult(outcome=outcome, per_voter=tuple(per_voter))

# compute per-voter happiness using rank-based normalized utility
def rank_normalized_happiness_for_outcome(
    situation: VotingSituation, outcome: str
) -> HappinessResult:

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
