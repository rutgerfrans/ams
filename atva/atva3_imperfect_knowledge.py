"""ATVA-3: Imperfect Knowledge Analysis.

Drops BTVA limitation #3: "TVA has perfect knowledge, i.e. it knows the true 
preferences of all voters."

This module analyzes scenarios where voters have uncertain or incomplete knowledge
about other voters' preferences, and must make strategic decisions under uncertainty.

Key difference from BTVA:
- BTVA: Assumes perfect knowledge of all voters' true preferences
- ATVA-3: Models uncertainty and analyzes decisions under imperfect information
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import random

from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome


@dataclass(frozen=True)
class BeliefModel:
    """A voter's beliefs about others' preferences.
    
    This models uncertainty as a probability distribution over possible
    preference orderings of other voters.
    """

    voter_index: int  # Whose belief model is this
    true_situation: VotingSituation  # The actual true preferences (voter doesn't know this)
    
    # Simple belief model: voter knows their own preferences, but others' prefs
    # are uncertain. We model this as possible scenarios with probabilities.
    belief_scenarios: tuple[VotingSituation, ...]  # Possible belief states
    scenario_probabilities: tuple[float, ...]  # Probability of each scenario
    
    def __post_init__(self):
        if len(self.belief_scenarios) != len(self.scenario_probabilities):
            raise ValueError("Number of scenarios must match number of probabilities")
        if abs(sum(self.scenario_probabilities) - 1.0) > 1e-6:
            raise ValueError("Probabilities must sum to 1.0")


@dataclass(frozen=True)
class StrategicOptionUnderUncertainty:
    """A strategic option evaluated under uncertainty."""

    voter_index: int
    tactical_ballot: StrategicBallot
    
    # Expected outcomes across belief scenarios
    expected_happiness: float  # Expected H~_i across scenarios
    baseline_expected_happiness: float  # Expected H_i across scenarios
    
    # Variance/risk
    happiness_variance: float  # Variance in happiness outcomes
    
    # Scenario-specific outcomes
    outcomes_by_scenario: tuple[str, ...]  # Winner in each scenario
    happiness_by_scenario: tuple[float, ...]  # Happiness in each scenario
    
    # True outcome (if we know ground truth)
    true_outcome: str | None
    true_happiness: float | None
    
    @property
    def expected_gain(self) -> float:
        """Expected happiness gain."""
        return self.expected_happiness - self.baseline_expected_happiness
    
    @property
    def is_robust(self) -> bool:
        """Is this option good in all scenarios? (happiness > baseline in all)"""
        return all(h > self.baseline_expected_happiness for h in self.happiness_by_scenario)


@dataclass(frozen=True)
class Atva3Result:
    """Result of ATVA-3 imperfect knowledge analysis."""

    scheme: VotingScheme
    
    # Ground truth (what we know but voters don't)
    true_baseline_outcome: str
    true_baseline_happiness: float
    
    # Strategic options under uncertainty (by voter)
    options_under_uncertainty: dict[int, list[StrategicOptionUnderUncertainty]]
    
    # Risk metrics
    avg_expected_gain: float  # Average expected gain across all options
    fraction_robust_options: float  # Fraction of options that are robust
    avg_regret: float  # Average difference between expected and true outcomes


def generate_belief_scenarios(
    situation: VotingSituation,
    voter_index: int,
    *,
    n_scenarios: int = 5,
    noise_level: float = 0.3,
    seed: int | None = None,
) -> tuple[tuple[VotingSituation, ...], tuple[float, ...]]:
    """Generate belief scenarios with uncertainty about others' preferences.
    
    Args:
        situation: True voting situation
        voter_index: Which voter's belief model to generate
        n_scenarios: Number of scenarios to generate
        noise_level: How much uncertainty (0=perfect knowledge, 1=maximal uncertainty)
        seed: Random seed for reproducibility
    
    Returns:
        Tuple of (scenarios, probabilities)
    """
    if seed is not None:
        random.seed(seed)
    
    scenarios: list[VotingSituation] = []
    
    # Scenario 0: True situation (voter might believe this with some probability)
    scenarios.append(situation)
    
    # Generate noisy scenarios
    for i in range(n_scenarios - 1):
        noisy_prefs = list(situation.voters_preferences)
        
        # For each other voter, potentially permute their preferences
        for v in range(situation.n_voters):
            if v == voter_index:
                continue  # Voter knows their own preferences
            
            if random.random() < noise_level:
                # Add noise: swap a few adjacent preferences
                pref_list = list(situation.voters_preferences[v])
                n_swaps = random.randint(1, len(pref_list) // 2)
                for _ in range(n_swaps):
                    pos = random.randint(0, len(pref_list) - 2)
                    pref_list[pos], pref_list[pos + 1] = pref_list[pos + 1], pref_list[pos]
                noisy_prefs[v] = tuple(pref_list)
        
        scenarios.append(VotingSituation(voters_preferences=tuple(noisy_prefs)))
    
    # Simple uniform probabilities for now
    # In a more sophisticated model, these could be learned or estimated
    probs = tuple([1.0 / n_scenarios] * n_scenarios)
    
    return tuple(scenarios), probs


def evaluate_option_under_uncertainty(
    scheme: VotingScheme,
    voter_index: int,
    tactical_ballot: StrategicBallot,
    belief_model: BeliefModel,
    *,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> StrategicOptionUnderUncertainty:
    """Evaluate a strategic option under uncertainty.
    
    Args:
        scheme: Voting scheme
        voter_index: Which voter is considering this option
        tactical_ballot: The strategic ballot being considered
        belief_model: The voter's beliefs about others
        happiness_metric: How to measure happiness
    
    Returns:
        Evaluation of the option across belief scenarios
    """
    outcomes = []
    happiness_values = []
    baseline_happiness_values = []
    
    # Evaluate across all belief scenarios
    for scenario, prob in zip(belief_model.belief_scenarios, belief_model.scenario_probabilities):
        # Baseline outcome in this scenario
        baseline_outcome = tally_votes(scheme, scenario)
        baseline_happy = happiness_for_outcome(scenario, baseline_outcome.winner, metric=happiness_metric)
        baseline_happiness_values.append(baseline_happy.per_voter[voter_index])
        
        # Strategic outcome in this scenario
        strategic_outcome = tally_votes_strategic(
            scheme, scenario, overrides={voter_index: tactical_ballot}
        )
        strategic_happy = happiness_for_outcome(scenario, strategic_outcome.winner, metric=happiness_metric)
        
        outcomes.append(strategic_outcome.winner)
        happiness_values.append(strategic_happy.per_voter[voter_index])
    
    # Compute expected values
    probs = belief_model.scenario_probabilities
    expected_happiness = sum(h * p for h, p in zip(happiness_values, probs))
    baseline_expected = sum(h * p for h, p in zip(baseline_happiness_values, probs))
    
    # Compute variance
    variance = sum(
        p * (h - expected_happiness) ** 2 
        for h, p in zip(happiness_values, probs)
    )
    
    # Compute true outcome (using ground truth)
    true_outcome_obj = tally_votes_strategic(
        scheme, belief_model.true_situation, overrides={voter_index: tactical_ballot}
    )
    true_happy = happiness_for_outcome(
        belief_model.true_situation, true_outcome_obj.winner, metric=happiness_metric
    )
    
    return StrategicOptionUnderUncertainty(
        voter_index=voter_index,
        tactical_ballot=tactical_ballot,
        expected_happiness=expected_happiness,
        baseline_expected_happiness=baseline_expected,
        happiness_variance=variance,
        outcomes_by_scenario=tuple(outcomes),
        happiness_by_scenario=tuple(happiness_values),
        true_outcome=true_outcome_obj.winner,
        true_happiness=true_happy.per_voter[voter_index],
    )


def run_atva3(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    n_scenarios: int = 5,
    noise_level: float = 0.3,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
    seed: int | None = None,
) -> Atva3Result:
    """Run ATVA-3 analysis: analyze strategic voting under imperfect knowledge.
    
    Args:
        scheme: Voting scheme
        situation: True voting situation (ground truth)
        n_scenarios: Number of belief scenarios to generate per voter
        noise_level: Amount of uncertainty (0=perfect, 1=maximal)
        happiness_metric: How to measure happiness
        seed: Random seed for reproducibility
    
    Returns:
        ATVA-3 analysis result
    """
    situation.validate()
    
    true_baseline_outcome = tally_votes(scheme, situation)
    true_baseline_happiness = happiness_for_outcome(
        situation, true_baseline_outcome.winner, metric=happiness_metric
    )
    
    options_under_uncertainty: dict[int, list[StrategicOptionUnderUncertainty]] = {}
    
    # For each voter, generate their belief model and evaluate options
    for voter_idx in range(situation.n_voters):
        # Generate belief scenarios for this voter
        scenarios, probs = generate_belief_scenarios(
            situation, voter_idx, 
            n_scenarios=n_scenarios, 
            noise_level=noise_level,
            seed=seed + voter_idx if seed is not None else None
        )
        
        belief_model = BeliefModel(
            voter_index=voter_idx,
            true_situation=situation,
            belief_scenarios=scenarios,
            scenario_probabilities=probs,
        )
        
        # Generate strategic options (bullet votes for simplicity)
        voter_options = []
        for alt in situation.alternatives:
            remaining = [a for a in situation.alternatives if a != alt]
            tactical_ballot = StrategicBallot(
                voter_index=voter_idx,
                kind="bullet",
                preferences=(alt,) + tuple(remaining)
            )
            
            option = evaluate_option_under_uncertainty(
                scheme, voter_idx, tactical_ballot, belief_model,
                happiness_metric=happiness_metric
            )
            
            # Only keep options with positive expected gain
            if option.expected_gain > 0:
                voter_options.append(option)
        
        options_under_uncertainty[voter_idx] = voter_options
    
    # Compute risk metrics
    all_options = [opt for opts in options_under_uncertainty.values() for opt in opts]
    
    if all_options:
        avg_expected_gain = sum(opt.expected_gain for opt in all_options) / len(all_options)
        robust_options = sum(1 for opt in all_options if opt.is_robust)
        fraction_robust = robust_options / len(all_options)
        
        # Regret: difference between what they expect and what actually happens
        regrets = [
            abs(opt.expected_happiness - (opt.true_happiness or 0))
            for opt in all_options if opt.true_happiness is not None
        ]
        avg_regret = sum(regrets) / len(regrets) if regrets else 0.0
    else:
        avg_expected_gain = 0.0
        fraction_robust = 0.0
        avg_regret = 0.0
    
    return Atva3Result(
        scheme=scheme,
        true_baseline_outcome=true_baseline_outcome.winner,
        true_baseline_happiness=true_baseline_happiness.total,
        options_under_uncertainty=options_under_uncertainty,
        avg_expected_gain=avg_expected_gain,
        fraction_robust_options=fraction_robust,
        avg_regret=avg_regret,
    )
