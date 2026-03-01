"""ATVA-2: Counter-Strategic Voting Analysis.

Drops BTVA limitation #2: "TVA does not consider the issue of counter-strategic voting."

This module analyzes scenarios where voters respond strategically to others' 
strategic votes, potentially leading to iterative strategic behavior and 
equilibrium concepts.

Key difference from BTVA:
- BTVA: Assumes other voters remain sincere when one voter deviates
- ATVA-2: Analyzes how voters might counter-manipulate in response
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome
from btva.enumeration_bullet import enumerate_bullet_options


@dataclass(frozen=True)
class StrategicResponse:
    """A voter's strategic response to another voter's manipulation."""

    responding_voter: int
    original_manipulator: int
    response_ballot: StrategicBallot
    
    # Outcomes
    baseline_outcome: str  # No manipulation
    after_manipulation_outcome: str  # After original voter manipulates
    after_response_outcome: str  # After response
    
    # Happiness of responding voter
    baseline_happiness: float
    after_manipulation_happiness: float
    after_response_happiness: float
    
    @property
    def response_improves_responder(self) -> bool:
        """Does the response improve the responding voter's happiness?"""
        return self.after_response_happiness > self.after_manipulation_happiness
    
    @property
    def response_restores_original(self) -> bool:
        """Does the response restore the original outcome?"""
        return self.after_response_outcome == self.baseline_outcome


@dataclass(frozen=True)
class IterativeStrategicSequence:
    """A sequence of strategic moves and counter-moves."""

    voter_sequence: tuple[int, ...]  # Order of voters making strategic moves
    ballot_sequence: tuple[StrategicBallot, ...]  # Their strategic ballots
    outcome_sequence: tuple[str, ...]  # Outcomes after each move
    happiness_sequence: tuple[tuple[float, ...], ...]  # All voters' happiness after each move
    
    @property
    def converged(self) -> bool:
        """Did the sequence converge (last two outcomes the same)?"""
        if len(self.outcome_sequence) < 2:
            return False
        return self.outcome_sequence[-1] == self.outcome_sequence[-2]
    
    @property
    def length(self) -> int:
        """Number of strategic moves in the sequence."""
        return len(self.voter_sequence)


@dataclass(frozen=True)
class Atva2Result:
    """Result of ATVA-2 counter-strategic analysis."""

    scheme: VotingScheme
    baseline_outcome: str
    baseline_total_happiness: float
    
    # Counter-strategic responses
    responses: list[StrategicResponse]
    
    # Iterative sequences
    iterative_sequences: list[IterativeStrategicSequence]
    
    # Risk metrics
    fraction_manipulations_with_counter_response: float
    avg_sequence_length_until_convergence: float
    fraction_sequences_restore_original: float


def find_counter_responses(
    scheme: VotingScheme,
    situation: VotingSituation,
    manipulator: int,
    manipulator_ballot: StrategicBallot,
    *,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[StrategicResponse]:
    """Find strategic responses by other voters to a manipulation.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        manipulator: Index of voter who manipulates
        manipulator_ballot: The manipulator's strategic ballot
        happiness_metric: How to measure happiness
    
    Returns:
        List of strategic responses that improve the responding voter
    """
    situation.validate()
    
    # Baseline: no manipulation
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )
    
    # After manipulation
    after_manip_outcome = tally_votes_strategic(
        scheme, situation, overrides={manipulator: manipulator_ballot}
    )
    after_manip_happiness = happiness_for_outcome(
        situation, after_manip_outcome.winner, metric=happiness_metric
    )
    
    responses: list[StrategicResponse] = []
    
    # For each other voter, check if they can beneficially respond
    for responder in range(situation.n_voters):
        if responder == manipulator:
            continue
        
        # Try bullet vote responses for each alternative
        for alt in situation.alternatives:
            remaining = [a for a in situation.alternatives if a != alt]
            response_prefs = (alt,) + tuple(remaining)
            response_ballot = StrategicBallot(
                voter_index=responder,
                kind="bullet_response",
                preferences=response_prefs
            )
            
            # Compute outcome after both manipulation and response
            after_response_outcome = tally_votes_strategic(
                scheme, 
                situation, 
                overrides={manipulator: manipulator_ballot, responder: response_ballot}
            )
            after_response_happiness = happiness_for_outcome(
                situation, after_response_outcome.winner, metric=happiness_metric
            )
            
            # Check if response improves responder's happiness
            if after_response_happiness.per_voter[responder] > after_manip_happiness.per_voter[responder]:
                responses.append(StrategicResponse(
                    responding_voter=responder,
                    original_manipulator=manipulator,
                    response_ballot=response_ballot,
                    baseline_outcome=baseline_outcome.winner,
                    after_manipulation_outcome=after_manip_outcome.winner,
                    after_response_outcome=after_response_outcome.winner,
                    baseline_happiness=baseline_happiness.per_voter[responder],
                    after_manipulation_happiness=after_manip_happiness.per_voter[responder],
                    after_response_happiness=after_response_happiness.per_voter[responder],
                ))
    
    return responses


def simulate_iterative_strategic_voting(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_iterations: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[IterativeStrategicSequence]:
    """Simulate iterative strategic voting sequences.
    
    Starting from the baseline, allow voters to make strategic moves in sequence
    if they can improve their happiness. Track sequences until convergence or
    max iterations.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        max_iterations: Maximum number of strategic moves to simulate
        happiness_metric: How to measure happiness
    
    Returns:
        List of iterative sequences
    """
    situation.validate()
    
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )
    
    sequences: list[IterativeStrategicSequence] = []
    
    # Try starting with each voter making an initial strategic move
    for initial_voter in range(situation.n_voters):
        # Try a few strategic ballots for the initial voter
        for alt in situation.alternatives[:3]:  # Limit for tractability
            remaining = [a for a in situation.alternatives if a != alt]
            initial_ballot = StrategicBallot(
                voter_index=initial_voter,
                kind="bullet",
                preferences=(alt,) + tuple(remaining)
            )
            
            # Initialize sequence
            voter_seq = [initial_voter]
            ballot_seq = [initial_ballot]
            outcome_seq = [baseline_outcome.winner]
            happiness_seq = [tuple(baseline_happiness.per_voter)]
            
            # Compute outcome after initial move
            current_overrides = {initial_voter: initial_ballot}
            current_outcome = tally_votes_strategic(scheme, situation, overrides=current_overrides)
            current_happiness = happiness_for_outcome(
                situation, current_outcome.winner, metric=happiness_metric
            )
            
            outcome_seq.append(current_outcome.winner)
            happiness_seq.append(tuple(current_happiness.per_voter))
            
            # Iterate: find if any voter wants to respond
            for iteration in range(max_iterations - 1):
                made_move = False
                
                # Check if any voter can improve by responding
                for voter in range(situation.n_voters):
                    if voter in current_overrides:
                        continue  # Skip voters who already deviated
                    
                    # Try bullet vote response
                    best_gain = 0.0
                    best_ballot = None
                    
                    for alt in situation.alternatives:
                        remaining = [a for a in situation.alternatives if a != alt]
                        test_ballot = StrategicBallot(
                            voter_index=voter,
                            kind="bullet",
                            preferences=(alt,) + tuple(remaining)
                        )
                        
                        test_overrides = {**current_overrides, voter: test_ballot}
                        test_outcome = tally_votes_strategic(scheme, situation, overrides=test_overrides)
                        test_happiness = happiness_for_outcome(
                            situation, test_outcome.winner, metric=happiness_metric
                        )
                        
                        gain = test_happiness.per_voter[voter] - current_happiness.per_voter[voter]
                        if gain > best_gain:
                            best_gain = gain
                            best_ballot = test_ballot
                    
                    # If found an improving move, make it
                    if best_ballot is not None:
                        current_overrides[voter] = best_ballot
                        current_outcome = tally_votes_strategic(scheme, situation, overrides=current_overrides)
                        current_happiness = happiness_for_outcome(
                            situation, current_outcome.winner, metric=happiness_metric
                        )
                        
                        voter_seq.append(voter)
                        ballot_seq.append(best_ballot)
                        outcome_seq.append(current_outcome.winner)
                        happiness_seq.append(tuple(current_happiness.per_voter))
                        
                        made_move = True
                        break  # One move per iteration
                
                if not made_move:
                    # No voter wants to respond - sequence converged
                    break
            
            # Only keep sequences that had at least one move
            if len(voter_seq) > 0:
                sequences.append(IterativeStrategicSequence(
                    voter_sequence=tuple(voter_seq),
                    ballot_sequence=tuple(ballot_seq),
                    outcome_sequence=tuple(outcome_seq),
                    happiness_sequence=tuple(happiness_seq),
                ))
    
    return sequences


def run_atva2(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_iterations: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> Atva2Result:
    """Run ATVA-2 analysis: analyze counter-strategic voting.
    
    Args:
        scheme: Voting scheme
        situation: Voting situation
        max_iterations: Maximum iterations for iterative sequences
        happiness_metric: How to measure happiness
    
    Returns:
        ATVA-2 analysis result
    """
    situation.validate()
    
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )
    
    # Find all counter-responses to single-voter manipulations
    all_responses: list[StrategicResponse] = []
    manipulations_checked = 0
    manipulations_with_responses = 0
    
    for manipulator in range(situation.n_voters):
        # Try a few manipulations (bullet votes)
        for alt in situation.alternatives:
            remaining = [a for a in situation.alternatives if a != alt]
            manip_ballot = StrategicBallot(
                voter_index=manipulator,
                kind="bullet",
                preferences=(alt,) + tuple(remaining)
            )
            
            responses = find_counter_responses(
                scheme, situation, manipulator, manip_ballot,
                happiness_metric=happiness_metric
            )
            
            manipulations_checked += 1
            if responses:
                manipulations_with_responses += 1
                all_responses.extend(responses)
    
    # Simulate iterative sequences
    sequences = simulate_iterative_strategic_voting(
        scheme, situation, max_iterations=max_iterations,
        happiness_metric=happiness_metric
    )
    
    # Compute risk metrics
    fraction_with_response = (
        manipulations_with_responses / manipulations_checked 
        if manipulations_checked > 0 else 0.0
    )
    
    avg_seq_length = (
        sum(s.length for s in sequences) / len(sequences)
        if sequences else 0.0
    )
    
    sequences_restore = sum(
        1 for s in sequences 
        if len(s.outcome_sequence) >= 2 and s.outcome_sequence[-1] == s.outcome_sequence[0]
    )
    fraction_restore = sequences_restore / len(sequences) if sequences else 0.0
    
    return Atva2Result(
        scheme=scheme,
        baseline_outcome=baseline_outcome.winner,
        baseline_total_happiness=baseline_happiness.total,
        responses=all_responses,
        iterative_sequences=sequences,
        fraction_manipulations_with_counter_response=fraction_with_response,
        avg_sequence_length_until_convergence=avg_seq_length,
        fraction_sequences_restore_original=fraction_restore,
    )
