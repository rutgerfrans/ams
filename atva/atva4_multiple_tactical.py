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

Uses the same strategic voting repertoire as BTVA (compromise/bury + bullet
voting).  Compromise/bury ballots go through ``overrides``; bullet ballots go
through ``bullet_choice_by_voter`` — matching BTVA's tally interface.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from itertools import combinations, product

from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome


# ---------------------------------------------------------------------------
# Internal helpers (mirrors atva1 / atva2 / atva3)
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


def _tally_with_deviations(
    scheme: VotingScheme,
    situation: VotingSituation,
    deviations: dict[int, _BallotOption],
):
    """Call tally_votes_strategic with deviations split into overrides / bullet_choices."""
    overrides = {v: opt.ballot for v, opt in deviations.items() if opt.bullet_choice is None}
    bullets = {v: opt.bullet_choice for v, opt in deviations.items() if opt.bullet_choice is not None}
    return tally_votes_strategic(
        scheme, situation, overrides=overrides, bullet_choice_by_voter=bullets
    )


def _tally_profile(
    scheme: VotingScheme,
    situation: VotingSituation,
    strategies: dict[int, StrategicBallot | None],
):
    """Tally a Nash equilibrium strategy profile.

    Non-None strategies are split into overrides (compromise/bury) or
    bullet_choice_by_voter (bullet) based on their kind.
    """
    overrides: dict[int, StrategicBallot] = {}
    bullets: dict[int, str] = {}
    for v, s in strategies.items():
        if s is None:
            continue
        if s.kind == "bullet":
            bullets[v] = s.preferences[0]
        else:
            overrides[v] = s
    return tally_votes_strategic(
        scheme, situation, overrides=overrides, bullet_choice_by_voter=bullets
    )


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MultiVoterTacticalScenario:
    """A scenario where multiple voters vote tactically simultaneously."""

    tactical_voters: tuple[int, ...]
    tactical_ballots: dict[int, StrategicBallot]

    baseline_outcome: str
    tactical_outcome: str

    baseline_total_happiness: float
    tactical_total_happiness: float
    per_voter_baseline_happiness: tuple[float, ...]
    per_voter_tactical_happiness: tuple[float, ...]

    individual_gains: dict[int, float]

    @property
    def n_tactical_voters(self) -> int:
        return len(self.tactical_voters)

    @property
    def total_happiness_change(self) -> float:
        return self.tactical_total_happiness - self.baseline_total_happiness

    @property
    def all_tactical_voters_benefit(self) -> bool:
        return all(self.individual_gains.get(v, 0) > 0 for v in self.tactical_voters)

    @property
    def some_tactical_voters_hurt(self) -> bool:
        return any(self.individual_gains.get(v, 0) < 0 for v in self.tactical_voters)

    @property
    def changes_winner(self) -> bool:
        return self.tactical_outcome != self.baseline_outcome


@dataclass(frozen=True)
class NashEquilibrium:
    """A Nash equilibrium in the voting game."""

    voter_strategies: dict[int, StrategicBallot | None]  # None = sincere vote
    outcome: str
    per_voter_happiness: tuple[float, ...]

    @property
    def n_tactical_voters(self) -> int:
        return sum(1 for s in self.voter_strategies.values() if s is not None)

    @property
    def is_sincere_equilibrium(self) -> bool:
        return all(s is None for s in self.voter_strategies.values())


@dataclass(frozen=True)
class Atva4Result:
    """Result of ATVA-4 multiple tactical voters analysis."""

    scheme: VotingScheme
    baseline_outcome: str
    baseline_total_happiness: float

    scenarios: list[MultiVoterTacticalScenario]
    nash_equilibria: list[NashEquilibrium]

    fraction_scenarios_all_benefit: float
    fraction_scenarios_some_hurt: float
    avg_total_happiness_change: float
    max_tactical_voters_observed: int


# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------

def enumerate_multi_voter_scenarios(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_tactical_voters: int = 3,
    max_ballots_per_voter: int = 3,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[MultiVoterTacticalScenario]:
    """Enumerate scenarios with multiple simultaneous independent tactical voters.

    Uses the full BTVA strategic repertoire (compromise/bury + bullet voting).
    Unlike ATVA-1, voters do not coordinate — each independently picks their
    own best ballot.  All combinations are enumerated and kept (no coalition-gain
    filter).

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        max_tactical_voters: Maximum number of simultaneous tactical voters.
        max_ballots_per_voter: Cap on compromise/bury options per voter (0 = no cap).
        happiness_metric: How to measure happiness.

    Returns:
        List of all multi-voter tactical scenarios.
    """
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )

    scenarios: list[MultiVoterTacticalScenario] = []

    for k in range(2, min(max_tactical_voters + 1, situation.n_voters + 1)):
        for voter_set in combinations(range(situation.n_voters), k):
            voter_set = tuple(voter_set)

            # Generate strategic ballot options for each voter
            ballot_options_by_voter: list[list[_BallotOption]] = [
                _generate_voter_ballot_options(
                    scheme, situation, voter_idx,
                    max_ballots_per_voter=max_ballots_per_voter,
                )
                for voter_idx in voter_set
            ]

            if any(len(opts) == 0 for opts in ballot_options_by_voter):
                continue

            for ballot_combo in product(*ballot_options_by_voter):
                deviations: dict[int, _BallotOption] = {
                    voter_set[i]: ballot_combo[i]
                    for i in range(len(voter_set))
                }

                tactical_outcome = _tally_with_deviations(scheme, situation, deviations)
                tactical_happiness = happiness_for_outcome(
                    situation, tactical_outcome.winner, metric=happiness_metric
                )

                individual_gains = {
                    v: tactical_happiness.per_voter[v] - baseline_happiness.per_voter[v]
                    for v in voter_set
                }

                # Record all tactical ballots (use .ballot from each _BallotOption)
                tactical_ballots = {v: opt.ballot for v, opt in deviations.items()}

                scenarios.append(MultiVoterTacticalScenario(
                    tactical_voters=voter_set,
                    tactical_ballots=tactical_ballots,
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
    happiness by unilaterally changing their vote.  Each voter's strategy set
    is {sincere} ∪ {all compromise/bury permutations} ∪ {all bullet votes},
    matching the BTVA repertoire.

    For games with > 4 voters, only the sincere profile is checked (heuristic).
    For ≤ 4 voters, all profiles are checked exhaustively.

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        max_ballots_per_voter: Cap on compromise/bury options per voter (0 = no cap).
        happiness_metric: How to measure happiness.

    Returns:
        List of Nash equilibria found.
    """
    situation.validate()

    # Build strategy sets: None (sincere) + all strategic options per voter
    ballot_options: dict[int, list[StrategicBallot | None]] = {}
    for voter_idx in range(situation.n_voters):
        opts: list[StrategicBallot | None] = [None]
        opts.extend(
            opt.ballot
            for opt in _generate_voter_ballot_options(
                scheme, situation, voter_idx,
                max_ballots_per_voter=max_ballots_per_voter,
            )
        )
        ballot_options[voter_idx] = opts

    # For large games, only check sincere profile (exponential otherwise)
    if situation.n_voters > 4:
        candidate_profiles: list[tuple[StrategicBallot | None, ...]] = [
            tuple([None] * situation.n_voters)
        ]
    else:
        candidate_profiles = list(
            product(*[ballot_options[v] for v in range(situation.n_voters)])
        )

    equilibria: list[NashEquilibrium] = []

    for profile in candidate_profiles:
        strategies: dict[int, StrategicBallot | None] = {
            v: profile[v] for v in range(situation.n_voters)
        }

        outcome = _tally_profile(scheme, situation, strategies)
        happiness = happiness_for_outcome(situation, outcome.winner, metric=happiness_metric)

        is_equilibrium = True
        for voter_idx in range(situation.n_voters):
            current_ballot = strategies[voter_idx]
            current_happiness = happiness.per_voter[voter_idx]

            # Check if voter can improve by unilaterally deviating
            for alt_ballot in ballot_options[voter_idx]:
                if alt_ballot == current_ballot:
                    continue

                test_strategies = dict(strategies)
                test_strategies[voter_idx] = alt_ballot

                test_outcome = _tally_profile(scheme, situation, test_strategies)
                test_happiness = happiness_for_outcome(
                    situation, test_outcome.winner, metric=happiness_metric
                )

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

    Uses the same strategic voting types as BTVA (compromise/bury + bullet)
    for all voters deviating simultaneously and independently.

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        max_tactical_voters: Maximum number of simultaneous tactical voters.
        max_ballots_per_voter: Cap on compromise/bury options per voter (0 = no cap).
        find_equilibria: Whether to compute Nash equilibria.
        happiness_metric: How to measure happiness.

    Returns:
        ATVA-4 analysis result.
    """
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )

    scenarios = enumerate_multi_voter_scenarios(
        scheme,
        situation,
        max_tactical_voters=max_tactical_voters,
        max_ballots_per_voter=max_ballots_per_voter,
        happiness_metric=happiness_metric,
    )

    equilibria: list[NashEquilibrium] = []
    if find_equilibria:
        equilibria = find_nash_equilibria(
            scheme,
            situation,
            max_ballots_per_voter=max_ballots_per_voter,
            happiness_metric=happiness_metric,
        )

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
