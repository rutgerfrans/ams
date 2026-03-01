"""ATVA-1: Voter Collusion Analysis.

Drops BTVA limitation #1: "TVA only analyzes single-voter manipulation, 
voter collusion is not considered."

This module analyzes scenarios where multiple voters coordinate their strategic
votes to achieve a common goal (e.g., electing a preferred candidate).

Key difference from BTVA:
- BTVA: Analyzes single voter deviations
- ATVA-1: Analyzes coalitions of voters coordinating their ballots
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
class CoalitionOption:
    """A strategic option for a coalition of voters."""

    voter_indices: tuple[int, ...]  # Which voters are in the coalition
    tactical_ballots: dict[int, StrategicBallot]  # Ballot for each coalition member
    baseline_outcome: str  # Winner without coalition manipulation
    strategic_outcome: str  # Winner with coalition manipulation
    coalition_baseline_happiness: float  # Sum of H_i for coalition members (baseline)
    coalition_strategic_happiness: float  # Sum of H~_i for coalition members
    
    @property
    def coalition_gain(self) -> float:
        """Total happiness gain for the coalition."""
        return self.coalition_strategic_happiness - self.coalition_baseline_happiness
    
    @property
    def changes_winner(self) -> bool:
        """Does this coalition change the winner?"""
        return self.strategic_outcome != self.baseline_outcome


@dataclass(frozen=True)
class Atva1Result:
    """Result of ATVA-1 collusion analysis."""

    scheme: VotingScheme
    baseline_outcome: str
    baseline_total_happiness: float
    
    # Coalition options by coalition size
    coalition_options: dict[int, list[CoalitionOption]]
    
    # Risk metrics
    max_coalition_size_that_changes_winner: int
    fraction_of_coalitions_that_change_winner: float
    avg_coalition_gain: float


def enumerate_coalition_options_size_k(
    scheme: VotingScheme,
    situation: VotingSituation,
    coalition_size: int,
    *,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[CoalitionOption]:
    """Enumerate strategic options for all coalitions of size k.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        coalition_size: Number of voters in coalition
        max_ballots_per_voter: Limit on strategic ballots to consider per voter
        happiness_metric: How to measure happiness
    
    Returns:
        List of coalition options
    """
    situation.validate()
    
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )
    
    options: list[CoalitionOption] = []
    
    # Iterate over all coalitions of the given size
    n_voters = situation.n_voters
    for coalition_indices in combinations(range(n_voters), coalition_size):
        coalition_indices = tuple(coalition_indices)
        
        # For each coalition member, generate a few strategic ballot options
        # To keep this tractable, we'll use a simplified enumeration:
        # - Try bullet votes for each alternative
        # - Try a few compromising permutations
        
        strategic_ballots_by_voter: dict[int, list[StrategicBallot]] = {}
        for voter_idx in coalition_indices:
            ballots = []
            sincere = situation.voters_preferences[voter_idx]
            
            # Add bullet vote options for each alternative
            for alt in situation.alternatives:
                # Bullet vote: put alt first, others in arbitrary order
                remaining = [a for a in situation.alternatives if a != alt]
                ballot_prefs = (alt,) + tuple(remaining)
                
                ballots.append(StrategicBallot(
                    voter_index=voter_idx,
                    kind="bullet",
                    preferences=ballot_prefs
                ))
            
            # Limit the number of ballots per voter to keep enumeration tractable
            strategic_ballots_by_voter[voter_idx] = ballots[:max_ballots_per_voter]
        
        # Try all combinations of strategic ballots for coalition members
        ballot_combinations = product(*[
            strategic_ballots_by_voter[i] for i in coalition_indices
        ])
        
        for ballot_combo in ballot_combinations:
            # Create override dict
            overrides = {
                coalition_indices[i]: ballot_combo[i]
                for i in range(len(coalition_indices))
            }
            
            # Compute outcome with coalition deviation
            strategic_outcome = tally_votes_strategic(scheme, situation, overrides=overrides)
            strategic_happiness = happiness_for_outcome(
                situation, strategic_outcome.winner, metric=happiness_metric
            )
            
            # Calculate coalition-specific happiness
            coalition_baseline = sum(
                baseline_happiness.per_voter[i] for i in coalition_indices
            )
            coalition_strategic = sum(
                strategic_happiness.per_voter[i] for i in coalition_indices
            )
            
            # Only keep options where coalition benefits
            if coalition_strategic > coalition_baseline:
                options.append(CoalitionOption(
                    voter_indices=coalition_indices,
                    tactical_ballots=overrides,
                    baseline_outcome=baseline_outcome.winner,
                    strategic_outcome=strategic_outcome.winner,
                    coalition_baseline_happiness=coalition_baseline,
                    coalition_strategic_happiness=coalition_strategic,
                ))
    
    return options


def run_atva1(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_coalition_size: int = 3,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> Atva1Result:
    """Run ATVA-1 analysis: enumerate and analyze voter coalitions.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        max_coalition_size: Maximum coalition size to analyze (for tractability)
        max_ballots_per_voter: Limit on strategic ballots per voter
        happiness_metric: How to measure happiness
    
    Returns:
        ATVA-1 analysis result
    """
    situation.validate()
    
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )
    
    # Enumerate coalitions of each size from 2 to max_coalition_size
    coalition_options: dict[int, list[CoalitionOption]] = {}
    
    for k in range(2, min(max_coalition_size + 1, situation.n_voters + 1)):
        options = enumerate_coalition_options_size_k(
            scheme,
            situation,
            k,
            max_ballots_per_voter=max_ballots_per_voter,
            happiness_metric=happiness_metric,
        )
        coalition_options[k] = options
    
    # Compute risk metrics
    max_size_changes_winner = 0
    total_coalitions = sum(len(opts) for opts in coalition_options.values())
    coalitions_change_winner = 0
    total_gain = 0.0
    
    for size, opts in coalition_options.items():
        for opt in opts:
            if opt.changes_winner and size > max_size_changes_winner:
                max_size_changes_winner = size
            if opt.changes_winner:
                coalitions_change_winner += 1
            total_gain += opt.coalition_gain
    
    fraction_change_winner = (
        coalitions_change_winner / total_coalitions if total_coalitions > 0 else 0.0
    )
    avg_gain = total_gain / total_coalitions if total_coalitions > 0 else 0.0
    
    return Atva1Result(
        scheme=scheme,
        baseline_outcome=baseline_outcome.winner,
        baseline_total_happiness=baseline_happiness.total,
        coalition_options=coalition_options,
        max_coalition_size_that_changes_winner=max_size_changes_winner,
        fraction_of_coalitions_that_change_winner=fraction_change_winner,
        avg_coalition_gain=avg_gain,
    )
