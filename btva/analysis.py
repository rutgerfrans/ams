from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Literal

from .enumeration import enumerate_all_permutations_options
from .enumeration_bullet import enumerate_bullet_options

from .happiness import HappinessResult, HappinessMetric, happiness_for_outcome
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


RiskMethod = Literal["avg_gain_all_options", "fraction_change_winner"]


def compute_risk(
    strategic_options: dict[int, list[StrategicOption]],
    *,
    method: RiskMethod,
) -> dict[str, object]:
    """Compute an overall 'risk of strategic voting' value from S_i.

    We implement two metrics:

    - avg_gain_all_options:
        Average (H~_i - H_i) across all enumerated options s_ij.
        (Each option contributes one gain number for the voter that deviates.)

    - fraction_change_winner:
        Fraction of voters i that have at least one option s_ij that changes
        the winner (O~ != O).

    Returns a small report dict with:
        {"method": ..., "overall": float, "by_strategy_kind": {kind: float}, "n_options": int}
    """

    n_options = sum(len(opts) for opts in strategic_options.values())
    if n_options == 0:
        return {
            "method": method,
            "overall": 0.0,
            "by_strategy_kind": {},
            "n_options": 0,
        }

    if method == "avg_gain_all_options":
        gains_by_kind: dict[str, list[int]] = defaultdict(list)
        total_gain = 0
        for voter_idx, opts in strategic_options.items():
            for opt in opts:
                gain = opt.H_tilde_i - opt.H_i
                total_gain += gain
                gains_by_kind[opt.strategy_kind].append(gain)

        overall = total_gain / n_options
        by_kind = {
            kind: (sum(gains) / len(gains)) if gains else 0.0
            for kind, gains in gains_by_kind.items()
        }
        return {
            "method": method,
            "overall": float(overall),
            "by_strategy_kind": dict(by_kind),
            "n_options": n_options,
        }

    if method == "fraction_change_winner":
        n_voters = len(strategic_options)
        # Overall: fraction of voters that can change the winner with any option.
        voters_can_change = 0
        voters_can_change_by_kind: dict[str, set[int]] = defaultdict(set)

        for voter_idx, opts in strategic_options.items():
            changed_any = False
            for opt in opts:
                if opt.strategic_outcome != opt.baseline_outcome:
                    changed_any = True
                    voters_can_change_by_kind[opt.strategy_kind].add(voter_idx)
            if changed_any:
                voters_can_change += 1

        overall = voters_can_change / max(1, n_voters)
        by_kind = {
            kind: (len(voters) / max(1, n_voters))
            for kind, voters in voters_can_change_by_kind.items()
        }
        return {
            "method": method,
            "overall": float(overall),
            "by_strategy_kind": dict(by_kind),
            "n_options": n_options,
        }

    raise ValueError(f"Unknown risk method: {method}")


def run_btva(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> BtvaResult:
    """Compute outcome O and happiness values H_i (and total H)."""

    voting_outcome = tally_votes(scheme, situation)
    happiness = happiness_for_outcome(
        situation, voting_outcome.winner, metric=happiness_metric
    )
    return BtvaResult(outcome=voting_outcome, happiness=happiness)


def run_btva_with_strategies(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    include_no_change: bool = False,
    max_m: int = 8,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> BtvaResult:
    """Compute O, H_i, H plus strategic option sets S_i (step 4).

    This uses the "all permutations" enumeration, which is factorial in m.
    To protect you from accidental 10! explosions, we refuse to enumerate when
    m > max_m unless you explicitly raise max_m.
    """

    base = run_btva(scheme, situation, happiness_metric=happiness_metric)

    m = situation.m_alternatives
    strategic_options: dict[int, list[StrategicOption]] = {
        i: [] for i in range(situation.n_voters)
    }

    # Bullet options are cheap (O(n*m)), so we can always include them.
    bullet = enumerate_bullet_options(
        scheme, situation, happiness_metric=happiness_metric
    )
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
        scheme,
        situation,
        include_no_change=include_no_change,
        happiness_metric=happiness_metric,
    )
    for i, opts in perms.items():
        strategic_options[i].extend(opts)
    return BtvaResult(
        outcome=base.outcome,
        happiness=base.happiness,
        strategic_options=strategic_options,
    )
