from __future__ import annotations

from dataclasses import dataclass

from .happiness import HappinessResult, borda_happiness_for_outcome
from .models import VotingScheme, VotingSituation
from .voting import VotingOutcome, tally_votes


@dataclass(frozen=True)
class BtvaResult:
    """Minimal BTVA result object for the assignment's outputs #1-#3.

    - O: non-strategic voting outcome (winner)
    - H_i: per-voter happiness levels (our definition)

    Strategic option sets S_i and risk are out of scope for this object for now.
    """

    outcome: VotingOutcome  # contains O as outcome.winner
    happiness: HappinessResult  # contains (H_i) and total H


def run_btva(scheme: VotingScheme, situation: VotingSituation) -> BtvaResult:
    """Compute outcome O and happiness values H_i (and total H)."""

    voting_outcome = tally_votes(scheme, situation)
    happiness = borda_happiness_for_outcome(situation, voting_outcome.winner)
    return BtvaResult(outcome=voting_outcome, happiness=happiness)
