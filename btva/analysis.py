from __future__ import annotations

from dataclasses import dataclass

from .enumeration import enumerate_all_permutations_options
from .enumeration_bullet import enumerate_bullet_options

from .happiness import HappinessResult, borda_happiness_for_outcome
from .models import VotingScheme, VotingSituation
from .strategic_options import StrategicOption
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
    strategic_options: dict[int, list[StrategicOption]] | None = None  # S_i


def run_btva(scheme: VotingScheme, situation: VotingSituation) -> BtvaResult:
    """Compute outcome O and happiness values H_i (and total H)."""

    voting_outcome = tally_votes(scheme, situation)
    happiness = borda_happiness_for_outcome(situation, voting_outcome.winner)
    return BtvaResult(outcome=voting_outcome, happiness=happiness)


def run_btva_with_strategies(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    include_no_change: bool = False,
    max_m: int = 8,
) -> BtvaResult:
    """Compute O, H_i, H plus strategic option sets S_i (step 4).

    This uses the "all permutations" enumeration, which is factorial in m.
    To protect you from accidental 10! explosions, we refuse to enumerate when
    m > max_m unless you explicitly raise max_m.
    """

    base = run_btva(scheme, situation)

    m = situation.m_alternatives
    strategic_options: dict[int, list[StrategicOption]] = {
        i: [] for i in range(situation.n_voters)
    }

    # Bullet options are cheap (O(n*m)), so we can always include them.
    bullet = enumerate_bullet_options(scheme, situation)
    for i, opts in bullet.items():
        strategic_options[i].extend(opts)

    # Permutation options are factorial in m, protect with max_m.
    if m > max_m:
        # Keep bullet options only.
        return BtvaResult(
            outcome=base.outcome,
            happiness=base.happiness,
            strategic_options=strategic_options,
        )

    perms = enumerate_all_permutations_options(
        scheme, situation, include_no_change=include_no_change
    )
    for i, opts in perms.items():
        strategic_options[i].extend(opts)
    return BtvaResult(
        outcome=base.outcome,
        happiness=base.happiness,
        strategic_options=strategic_options,
    )
