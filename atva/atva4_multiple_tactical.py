"""ATVA-4: Multiple Simultaneous Tactical Voters Analysis.

Drops BTVA limitation #4: "In calculating H and H~, TVA only considers tactical 
voting by a single voter (i.e., it does not consider situations in which several 
voters vote tactically at the same time)."

This module analyzes scenarios where multiple voters independently vote tactically
at the same time, without coordination (unlike ATVA-1 which analyzes collusion).

Key difference from BTVA:
- BTVA: Only one voter deviates at a time when computing H~
- ATVA-4: Multiple voters may deviate simultaneously (independently)
- Different from ATVA-1: Voters don't coordinate; they act independently
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Literal

from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome


@dataclass(frozen=True)
class MultiVoterTacticalScenario:
    """A scenario where multiple voters vote tactically simultaneously."""

    tactical_voters: tuple[int, ...]  # Indices of voters who vote tactically
    tactical_ballots: dict[int, StrategicBallot]  # Their ballots
    
    # Outcomes
    baseline_outcome: str  # No one votes tactically
    tactical_outcome: str  # All tactical voters deviate simultaneously
    
    # Happiness analysis
    baseline_total_happiness: float
    tactical_total_happiness: float
    per_voter_baseline_happiness: tuple[float, ...]
    per_voter_tactical_happiness: tuple[float, ...]
    
    # Individual gains/losses
    individual_gains: dict[int, float]  # happiness change for each voter
    
    @property
    def n_tactical_voters(self) -> int:
        """Number of tactical voters."""
        return len(self.tactical_voters)
    
    @property
    def total_happiness_change(self) -> float:
        """Change in total social happiness."""
        return self.tactical_total_happiness - self.baseline_total_happiness
    
    @property
    def all_tactical_voters_benefit(self) -> bool:
        """Do all tactical voters improve their happiness?"""
        return all(
            self.individual_gains.get(v, 0) > 0 
            for v in self.tactical_voters
        )
    
    @property
    def some_tactical_voters_hurt(self) -> bool:
        """Do some tactical voters hurt themselves?"""
        return any(
            self.individual_gains.get(v, 0) < 0 
            for v in self.tactical_voters
        )
    
    @property
    def changes_winner(self) -> bool:
        """Does tactical voting change the winner?"""
        return self.tactical_outcome != self.baseline_outcome


@dataclass(frozen=True)
class NashEquilibrium:
    """A Nash equilibrium in the voting game."""

    voter_strategies: dict[int, StrategicBallot | None]  # None = sincere vote
    outcome: str
    per_voter_happiness: tuple[float, ...]
    
    @property
    def n_tactical_voters(self) -> int:
        """Number of voters voting tactically in equilibrium."""
        return sum(1 for s in self.voter_strategies.values() if s is not None)
    
    @property
    def is_sincere_equilibrium(self) -> bool:
        """Is everyone voting sincerely?"""
        return all(s is None for s in self.voter_strategies.values())


@dataclass(frozen=True)
class Atva4Result:
    """Result of ATVA-4 multiple tactical voters analysis."""

    scheme: VotingScheme
    baseline_outcome: str
    baseline_total_happiness: float
    
    # Multi-voter tactical scenarios
    scenarios: list[MultiVoterTacticalScenario]
    
    # Nash equilibria
    nash_equilibria: list[NashEquilibrium]
    
    # Risk metrics
    fraction_scenarios_all_benefit: float  # All tactical voters benefit
    fraction_scenarios_some_hurt: float  # Some tactical voters hurt themselves
    avg_total_happiness_change: float
    max_tactical_voters_observed: int


def enumerate_multi_voter_scenarios(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_tactical_voters: int = 3,
    max_ballots_per_voter: int = 3,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[MultiVoterTacticalScenario]:
    """Enumerate scenarios with multiple simultaneous tactical voters.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        max_tactical_voters: Maximum number of tactical voters to consider
        max_ballots_per_voter: Limit on strategic ballots per voter
        happiness_metric: How to measure happiness
    
    Returns:
        List of multi-voter tactical scenarios
    """
    situation.validate()
    
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )
    
    scenarios: list[MultiVoterTacticalScenario] = []
    
    # Try different numbers of tactical voters
    for k in range(2, min(max_tactical_voters + 1, situation.n_voters + 1)):
        # Try different sets of k voters
        for voter_set in combinations(range(situation.n_voters), k):
            voter_set = tuple(voter_set)
            
            # Generate strategic ballot options for each voter
            ballot_options: dict[int, list[StrategicBallot]] = {}
            for voter_idx in voter_set:
                ballots = []
                
                # Add bullet vote options
                for alt in situation.alternatives[:max_ballots_per_voter]:
                    remaining = [a for a in situation.alternatives if a != alt]
                    ballot_prefs = (alt,) + tuple(remaining)
                    ballots.append(StrategicBallot(
                        voter_index=voter_idx,
                        kind="bullet",
                        preferences=ballot_prefs
                    ))
                
                ballot_options[voter_idx] = ballots
            
            # Try all combinations of ballots
            ballot_combos = product(*[ballot_options[v] for v in voter_set])
            
            for ballot_combo in ballot_combos:
                # Create override dict
                overrides = {
                    voter_set[i]: ballot_combo[i]
                    for i in range(len(voter_set))
                }
                
                # Compute outcome with all tactical voters
                tactical_outcome = tally_votes_strategic(scheme, situation, overrides=overrides)
                tactical_happiness = happiness_for_outcome(
                    situation, tactical_outcome.winner, metric=happiness_metric
                )
                
                # Compute individual gains
                individual_gains = {
                    v: tactical_happiness.per_voter[v] - baseline_happiness.per_voter[v]
                    for v in voter_set
                }
                
                scenarios.append(MultiVoterTacticalScenario(
                    tactical_voters=voter_set,
                    tactical_ballots=overrides,
                    baseline_outcome=baseline_outcome.winner,
                    tactical_outcome=tactical_outcome.winner,
                    baseline_total_happiness=baseline_happiness.total,
                    tactical_total_happiness=tactical_happiness.total,
                    per_voter_baseline_happiness=tuple(baseline_happiness.per_voter),
                    per_voter_tactical_happiness=tuple(tactical_happiness.per_voter),
                    individual_gains=individual_gains,
                ))
    
    return scenarios


def find_nash_equilibria(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_ballots_per_voter: int = 3,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[NashEquilibrium]:
    """Find Nash equilibria in the voting game.
    
    A Nash equilibrium is a strategy profile where no voter can improve their
    happiness by unilaterally changing their vote.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        max_ballots_per_voter: Limit on strategic ballots to check per voter
        happiness_metric: How to measure happiness
    
    Returns:
        List of Nash equilibria found
    """
    situation.validate()
    
    equilibria: list[NashEquilibrium] = []
    
    # Generate strategic ballot options for each voter
    ballot_options: dict[int, list[StrategicBallot | None]] = {}
    for voter_idx in range(situation.n_voters):
        ballots: list[StrategicBallot | None] = [None]  # None = sincere vote
        
        # Add bullet vote options
        for alt in situation.alternatives[:max_ballots_per_voter]:
            remaining = [a for a in situation.alternatives if a != alt]
            ballot_prefs = (alt,) + tuple(remaining)
            ballots.append(StrategicBallot(
                voter_index=voter_idx,
                kind="bullet",
                preferences=ballot_prefs
            ))
        
        ballot_options[voter_idx] = ballots
    
    # Check each strategy profile to see if it's a Nash equilibrium
    # Note: This is exponential in the number of voters, so we limit it
    if situation.n_voters > 4:
        # For larger games, only check a few candidate equilibria
        # (sincere voting and a few random profiles)
        candidate_profiles = [
            tuple([None] * situation.n_voters)  # Sincere voting
        ]
    else:
        # For small games, check all profiles
        candidate_profiles = list(product(*[ballot_options[v] for v in range(situation.n_voters)]))
    
    for profile in candidate_profiles:
        # Create strategy dict
        strategies = {
            v: profile[v] for v in range(situation.n_voters)
        }
        
        # Compute outcome and happiness under this profile
        overrides = {v: s for v, s in strategies.items() if s is not None}
        outcome = tally_votes_strategic(scheme, situation, overrides=overrides)
        happiness = happiness_for_outcome(situation, outcome.winner, metric=happiness_metric)
        
        # Check if this is a Nash equilibrium
        is_equilibrium = True
        for voter_idx in range(situation.n_voters):
            current_ballot = strategies[voter_idx]
            current_happiness = happiness.per_voter[voter_idx]
            
            # Check if voter can improve by deviating
            for alt_ballot in ballot_options[voter_idx]:
                if alt_ballot == current_ballot:
                    continue
                
                # Test deviation
                test_overrides = {**overrides}
                if alt_ballot is None:
                    test_overrides.pop(voter_idx, None)
                else:
                    test_overrides[voter_idx] = alt_ballot
                
                test_outcome = tally_votes_strategic(scheme, situation, overrides=test_overrides)
                test_happiness = happiness_for_outcome(situation, test_outcome.winner, metric=happiness_metric)
                
                if test_happiness.per_voter[voter_idx] > current_happiness:
                    is_equilibrium = False
                    break
            
            if not is_equilibrium:
                break
        
        if is_equilibrium:
            equilibria.append(NashEquilibrium(
                voter_strategies=strategies,
                outcome=outcome.winner,
                per_voter_happiness=tuple(happiness.per_voter),
            ))
    
    return equilibria


def run_atva4(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_tactical_voters: int = 3,
    max_ballots_per_voter: int = 3,
    find_equilibria: bool = True,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> Atva4Result:
    """Run ATVA-4 analysis: analyze multiple simultaneous tactical voters.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        max_tactical_voters: Maximum number of tactical voters to consider
        max_ballots_per_voter: Limit on strategic ballots per voter
        find_equilibria: Whether to compute Nash equilibria
        happiness_metric: How to measure happiness
    
    Returns:
        ATVA-4 analysis result
    """
    situation.validate()
    
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )
    
    # Enumerate multi-voter scenarios
    scenarios = enumerate_multi_voter_scenarios(
        scheme, situation,
        max_tactical_voters=max_tactical_voters,
        max_ballots_per_voter=max_ballots_per_voter,
        happiness_metric=happiness_metric,
    )
    
    # Find Nash equilibria if requested
    equilibria = []
    if find_equilibria:
        equilibria = find_nash_equilibria(
            scheme, situation,
            max_ballots_per_voter=max_ballots_per_voter,
            happiness_metric=happiness_metric,
        )
    
    # Compute risk metrics
    if scenarios:
        all_benefit = sum(1 for s in scenarios if s.all_tactical_voters_benefit)
        some_hurt = sum(1 for s in scenarios if s.some_tactical_voters_hurt)
        fraction_all_benefit = all_benefit / len(scenarios)
        fraction_some_hurt = some_hurt / len(scenarios)
        avg_happiness_change = sum(s.total_happiness_change for s in scenarios) / len(scenarios)
        max_tactical = max(s.n_tactical_voters for s in scenarios)
    else:
        fraction_all_benefit = 0.0
        fraction_some_hurt = 0.0
        avg_happiness_change = 0.0
        max_tactical = 0
    
    return Atva4Result(
        scheme=scheme,
        baseline_outcome=baseline_outcome.winner,
        baseline_total_happiness=baseline_happiness.total,
        scenarios=scenarios,
        nash_equilibria=equilibria,
        fraction_scenarios_all_benefit=fraction_all_benefit,
        fraction_scenarios_some_hurt=fraction_some_hurt,
        avg_total_happiness_change=avg_happiness_change,
        max_tactical_voters_observed=max_tactical,
    )
