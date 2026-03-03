"""ATVA-1: Voter Collusion Analysis.

Drops BTVA limitation #1: "TVA only analyzes single-voter manipulation,
voter collusion is not considered."

This module analyzes scenarios where multiple voters coordinate their strategic
votes to achieve a common goal (e.g., electing a preferred candidate).

Key difference from BTVA:
- BTVA: Analyzes single voter deviations using compromise/bury and bullet voting
- ATVA-1: Same strategic repertoire (compromise/bury + bullet), but applied to
  coalitions of voters who coordinate their ballots
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from itertools import combinations, product

from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome


@dataclass(frozen=True)
class _BallotOption:
    """Internal: one candidate ballot for a single coalition member.

    bullet_choice is set for bullet-voting ballots and None for
    compromise/bury ballots.  This mirrors the split that BTVA makes
    between overrides (permutation-based) and bullet_choice_by_voter.
    """

    ballot: StrategicBallot
    bullet_choice: str | None


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


def _generate_voter_ballot_options(
    scheme: VotingScheme,
    situation: VotingSituation,
    voter_idx: int,
    *,
    max_ballots_per_voter: int = 5,
) -> list[_BallotOption]:
    """Generate strategic ballot options for a single coalition member.

    Mirrors BTVA's two strategy types:

    1. Compromise / bury — every permutation of alternatives except the
       voter's sincere ranking.  Capped to ``max_ballots_per_voter`` entries
       (set to 0 for no cap).
    2. Bullet voting — one option per alternative; always included in full
       because there are only m options and bullet voting is not applicable
       to plurality.

    Args:
        scheme: Voting scheme (bullet voting skipped for PLURALITY).
        situation: The voting situation.
        voter_idx: Index of the voter within the situation.
        max_ballots_per_voter: Maximum number of compromise/bury options to
            keep per voter (0 means no cap).  Bullet options are never capped.
    """
    sincere = situation.voters_preferences[voter_idx]
    options: list[_BallotOption] = []

    # 1. Compromise / bury — early exit once cap is reached
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


def enumerate_coalition_options_size_k(
    scheme: VotingScheme,
    situation: VotingSituation,
    coalition_size: int,
    *,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[CoalitionOption]:
    """Enumerate strategic options for all coalitions of size k.

    Uses the same strategic repertoire as BTVA (compromise/bury + bullet
    voting), extended to coordinated coalitions of k voters.

    For each coalition:
    - Each member independently picks a ballot from their strategic options.
    - All combinations across members are tried.
    - Compromise/bury ballots are passed as ``overrides``; bullet ballots are
      passed as ``bullet_choice_by_voter`` — exactly as BTVA does for single
      voters.
    - Only combinations where the coalition's collective happiness improves
      are kept.

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        coalition_size: Number of voters in the coalition.
        max_ballots_per_voter: Cap on compromise/bury options per voter
            (0 = no cap).  Bullet options are always included in full.
        happiness_metric: How to measure voter happiness.

    Returns:
        List of CoalitionOption instances where the coalition benefits.
    """
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )

    options: list[CoalitionOption] = []

    for coalition_indices in combinations(range(situation.n_voters), coalition_size):
        coalition_indices = tuple(coalition_indices)

        # Generate ballot options for each coalition member
        ballot_options_by_voter: list[list[_BallotOption]] = [
            _generate_voter_ballot_options(
                scheme,
                situation,
                voter_idx,
                max_ballots_per_voter=max_ballots_per_voter,
            )
            for voter_idx in coalition_indices
        ]

        # Skip coalitions where any member has no tactical options
        if any(len(opts) == 0 for opts in ballot_options_by_voter):
            continue

        # Try all combinations of ballot options across coalition members
        for ballot_combo in product(*ballot_options_by_voter):
            # Split into the two BTVA call interfaces
            overrides: dict[int, StrategicBallot] = {}
            bullet_choices: dict[int, str] = {}

            for voter_idx, opt in zip(coalition_indices, ballot_combo):
                if opt.bullet_choice is not None:
                    bullet_choices[voter_idx] = opt.bullet_choice
                else:
                    overrides[voter_idx] = opt.ballot

            # Compute outcome with coalition deviation
            strategic_outcome = tally_votes_strategic(
                scheme,
                situation,
                overrides=overrides,
                bullet_choice_by_voter=bullet_choices,
            )
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

            # Only keep options where the coalition collectively benefits
            if coalition_strategic > coalition_baseline:
                # Merge all tactical ballots for the record (bullet ballots
                # included even though they are keyed by bullet_choices above)
                all_ballots = dict(overrides)
                for voter_idx, opt in zip(coalition_indices, ballot_combo):
                    if voter_idx not in all_ballots:
                        all_ballots[voter_idx] = opt.ballot

                options.append(CoalitionOption(
                    voter_indices=coalition_indices,
                    tactical_ballots=all_ballots,
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

    Applies the same strategic voting types as BTVA (compromise/bury + bullet)
    to coordinated voter coalitions.

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        max_coalition_size: Maximum coalition size to analyze (for tractability).
        max_ballots_per_voter: Cap on compromise/bury options per voter
            (0 = no cap).
        happiness_metric: How to measure voter happiness.

    Returns:
        ATVA-1 analysis result.
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
