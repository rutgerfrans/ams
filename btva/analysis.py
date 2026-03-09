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
    outcome: VotingOutcome
    happiness: HappinessResult
    strategic_options: dict[int, list[StrategicOption]] | None = None

#initialize risk methods
RiskMethod = Literal["avg_gain_all_options", "fraction_change_winner"]

#Compute an overall 'risk of strategic voting' value from S_i
def compute_risk(
    strategic_options: dict[int, list[StrategicOption]],
    *,
    method: RiskMethod,
) -> dict[str, object]:

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

    voting_outcome = tally_votes(scheme, situation)
    happiness = happiness_for_outcome(situation, voting_outcome.winner, metric=happiness_metric)
    return BtvaResult(outcome=voting_outcome, happiness=happiness)

#Compute O, H_i, H plus strategic option sets S_i 
def run_btva_with_strategies(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    include_no_change: bool = False,
    max_m: int = 8,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> BtvaResult:
    base = run_btva(scheme, situation, happiness_metric=happiness_metric)

    m = situation.m_alternatives
    strategic_options: dict[int, list[StrategicOption]] = {i: [] for i in range(situation.n_voters)}

    bullet = enumerate_bullet_options(scheme, situation, happiness_metric=happiness_metric)
    for i, opts in bullet.items():
        strategic_options[i].extend(opts)

    if m > max_m:
        return BtvaResult(outcome=base.outcome, happiness=base.happiness, strategic_options=strategic_options)

    perms = enumerate_all_permutations_options(scheme, situation, include_no_change=include_no_change, happiness_metric=happiness_metric)
    for i, opts in perms.items():
        strategic_options[i].extend(opts)
    return BtvaResult(outcome=base.outcome, happiness=base.happiness, strategic_options=strategic_options)
