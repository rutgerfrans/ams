"""ATVA-3: Imperfect Knowledge Analysis.

Drops BTVA limitation #3: "TVA has perfect knowledge, i.e. it knows the true
preferences of all voters."

This module analyzes scenarios where voters have uncertain or incomplete knowledge
about other voters' preferences, and must make strategic decisions under uncertainty.

Key difference from BTVA:
- BTVA: Assumes perfect knowledge of all voters' true preferences
- ATVA-3: Models uncertainty and analyzes decisions under imperfect information

Uses the same strategic voting repertoire as BTVA (compromise/bury + bullet
voting).  Each tactical ballot is evaluated across all belief scenarios, and
the correct tally interface (overrides vs. bullet_choice_by_voter) is chosen
based on the ballot's kind.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome


# ---------------------------------------------------------------------------
# Internal helpers (mirrors atva1 / atva2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _BallotOption:
    """Internal: one candidate ballot for a single voter."""

    ballot: StrategicBallot
    bullet_choice: str | None


def _generate_voter_ballot_options(
    scheme: VotingScheme,
    situation: VotingSituation,
    voter_idx: int,
    *,
    max_ballots_per_voter: int = 5,
) -> list[_BallotOption]:
    """Generate strategic ballot options (compromise/bury + bullet) for a voter.

    Mirrors BTVA:
    1. Compromise / bury — all permutations except sincere, capped by
       ``max_ballots_per_voter`` (0 = no cap).
    2. Bullet voting — one per alternative; always included, skipped for PLURALITY.
    """
    sincere = situation.voters_preferences[voter_idx]
    options: list[_BallotOption] = []

    # 1. Compromise / bury
    comp_bury: list[_BallotOption] = []
    for perm in itertools.permutations(situation.alternatives):
        if perm == sincere:
            continue
        ballot = StrategicBallot(
            voter_index=voter_idx,
            kind="compromising_burying",
            preferences=perm,
        )
        comp_bury.append(_BallotOption(ballot=ballot, bullet_choice=None))
        if max_ballots_per_voter > 0 and len(comp_bury) >= max_ballots_per_voter:
            break
    options.extend(comp_bury)

    # 2. Bullet voting (not applicable to plurality)
    if scheme != VotingScheme.PLURALITY:
        for chosen in situation.alternatives:
            others = [a for a in sincere if a != chosen]
            ballot = StrategicBallot(
                voter_index=voter_idx,
                kind="bullet",
                preferences=tuple([chosen] + others),
            )
            options.append(_BallotOption(ballot=ballot, bullet_choice=chosen))

    return options


def _tally_strategic_ballot(
    scheme: VotingScheme,
    situation: VotingSituation,
    voter_index: int,
    tactical_ballot: StrategicBallot,
):
    """Call tally_votes_strategic for a single voter's tactical ballot.

    Routes to ``overrides`` or ``bullet_choice_by_voter`` based on the
    ballot's kind, matching BTVA's tally interface.
    """
    if tactical_ballot.kind == "bullet":
        return tally_votes_strategic(
            scheme,
            situation,
            bullet_choice_by_voter={voter_index: tactical_ballot.preferences[0]},
        )
    return tally_votes_strategic(
        scheme,
        situation,
        overrides={voter_index: tactical_ballot},
    )


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BeliefModel:
    """A voter's beliefs about others' preferences.

    The voter knows their own preferences perfectly.  Other voters' preferences
    are uncertain and modelled as a probability distribution over scenarios.
    """

    voter_index: int
    true_situation: VotingSituation

    belief_scenarios: tuple[VotingSituation, ...]
    scenario_probabilities: tuple[float, ...]

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

    expected_happiness: float
    baseline_expected_happiness: float
    happiness_variance: float

    outcomes_by_scenario: tuple[str, ...]
    happiness_by_scenario: tuple[float, ...]
    baseline_happiness_by_scenario: tuple[float, ...]

    true_outcome: str | None
    true_happiness: float | None

    @property
    def expected_gain(self) -> float:
        """Expected happiness gain."""
        return self.expected_happiness - self.baseline_expected_happiness

    @property
    def is_robust(self) -> bool:
        """Is this option good in all scenarios? (happiness > baseline in all)"""
        return all(h > b for h, b in zip(self.happiness_by_scenario, self.baseline_happiness_by_scenario))


@dataclass(frozen=True)
class Atva3Result:
    """Result of ATVA-3 imperfect knowledge analysis."""

    scheme: VotingScheme

    true_baseline_outcome: str
    true_baseline_happiness: float

    options_under_uncertainty: dict[int, list[StrategicOptionUnderUncertainty]]

    avg_expected_gain: float
    fraction_robust_options: float
    avg_regret: float


# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------

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
        situation: True voting situation.
        voter_index: Which voter's belief model to generate.
        n_scenarios: Number of scenarios to generate.
        noise_level: Amount of uncertainty (0 = perfect knowledge, 1 = maximal).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (scenarios, probabilities).
    """
    if seed is not None:
        random.seed(seed)

    scenarios: list[VotingSituation] = []

    # Scenario 0: true situation
    scenarios.append(situation)

    for _ in range(n_scenarios - 1):
        noisy_prefs = list(situation.voters_preferences)

        for v in range(situation.n_voters):
            if v == voter_index:
                continue  # Voter knows their own preferences

            if random.random() < noise_level:
                pref_list = list(situation.voters_preferences[v])
                n_swaps = random.randint(1, len(pref_list) // 2)
                for _ in range(n_swaps):
                    pos = random.randint(0, len(pref_list) - 2)
                    pref_list[pos], pref_list[pos + 1] = pref_list[pos + 1], pref_list[pos]
                noisy_prefs[v] = tuple(pref_list)

        scenarios.append(VotingSituation(voters_preferences=tuple(noisy_prefs)))

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

    The ballot is routed through the correct tally interface (overrides for
    compromise/bury, bullet_choice_by_voter for bullet) in every scenario.

    Args:
        scheme: Voting scheme.
        voter_index: Which voter is considering this option.
        tactical_ballot: The strategic ballot being considered.
        belief_model: The voter's beliefs about others.
        happiness_metric: How to measure happiness.

    Returns:
        Evaluation of the option across belief scenarios.
    """
    outcomes: list[str] = []
    happiness_values: list[float] = []
    baseline_happiness_values: list[float] = []

    for scenario in belief_model.belief_scenarios:
        # Baseline outcome in this scenario
        baseline_outcome = tally_votes(scheme, scenario)
        baseline_happy = happiness_for_outcome(
            scenario, baseline_outcome.winner, metric=happiness_metric
        )
        baseline_happiness_values.append(baseline_happy.per_voter[voter_index])

        # Strategic outcome — route correctly based on ballot kind
        strategic_outcome = _tally_strategic_ballot(scheme, scenario, voter_index, tactical_ballot)
        strategic_happy = happiness_for_outcome(
            scenario, strategic_outcome.winner, metric=happiness_metric
        )

        outcomes.append(strategic_outcome.winner)
        happiness_values.append(strategic_happy.per_voter[voter_index])

    probs = belief_model.scenario_probabilities
    expected_happiness = sum(h * p for h, p in zip(happiness_values, probs))
    baseline_expected = sum(h * p for h, p in zip(baseline_happiness_values, probs))

    variance = sum(
        p * (h - expected_happiness) ** 2
        for h, p in zip(happiness_values, probs)
    )

    # True outcome using ground truth — also routed correctly
    true_outcome_obj = _tally_strategic_ballot(
        scheme, belief_model.true_situation, voter_index, tactical_ballot
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
        baseline_happiness_by_scenario=tuple(baseline_happiness_values),
    )


def run_atva3(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    n_scenarios: int = 5,
    noise_level: float = 0.3,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
    seed: int | None = None,
) -> Atva3Result:
    """Run ATVA-3 analysis: analyze strategic voting under imperfect knowledge.

    Each voter evaluates the full BTVA strategic repertoire (compromise/bury
    + bullet voting) across their belief scenarios.

    Args:
        scheme: Voting scheme.
        situation: True voting situation (ground truth).
        n_scenarios: Number of belief scenarios to generate per voter.
        noise_level: Amount of uncertainty (0 = perfect, 1 = maximal).
        max_ballots_per_voter: Cap on compromise/bury options per voter (0 = no cap).
        happiness_metric: How to measure happiness.
        seed: Random seed for reproducibility.

    Returns:
        ATVA-3 analysis result.
    """
    situation.validate()

    true_baseline_outcome = tally_votes(scheme, situation)
    true_baseline_happiness = happiness_for_outcome(
        situation, true_baseline_outcome.winner, metric=happiness_metric
    )

    options_under_uncertainty: dict[int, list[StrategicOptionUnderUncertainty]] = {}

    for voter_idx in range(situation.n_voters):
        scenarios, probs = generate_belief_scenarios(
            situation,
            voter_idx,
            n_scenarios=n_scenarios,
            noise_level=noise_level,
            seed=seed + voter_idx if seed is not None else None,
        )

        belief_model = BeliefModel(
            voter_index=voter_idx,
            true_situation=situation,
            belief_scenarios=scenarios,
            scenario_probabilities=probs,
        )

        voter_options: list[StrategicOptionUnderUncertainty] = []

        # Evaluate all strategic options (compromise/bury + bullet)
        for opt in _generate_voter_ballot_options(
            scheme, situation, voter_idx, max_ballots_per_voter=max_ballots_per_voter
        ):
            option = evaluate_option_under_uncertainty(
                scheme,
                voter_idx,
                opt.ballot,
                belief_model,
                happiness_metric=happiness_metric,
            )

            if option.expected_gain > 0:
                voter_options.append(option)

        options_under_uncertainty[voter_idx] = voter_options

    # Compute risk metrics
    all_options = [opt for opts in options_under_uncertainty.values() for opt in opts]

    if all_options:
        avg_expected_gain = sum(opt.expected_gain for opt in all_options) / len(all_options)
        robust_options = sum(1 for opt in all_options if opt.is_robust)
        fraction_robust = robust_options / len(all_options)

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
