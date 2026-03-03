"""ATVA-2: Counter-Strategic Voting Analysis.

Drops BTVA limitation #2: "TVA does not consider the issue of counter-strategic voting."

This module analyzes scenarios where voters respond strategically to others'
strategic votes, potentially leading to iterative strategic behavior and
equilibrium concepts.

Key difference from BTVA:
- BTVA: Assumes other voters remain sincere when one voter deviates
- ATVA-2: Analyzes how voters might counter-manipulate in response

Uses the same strategic voting repertoire as BTVA (compromise/bury + bullet
voting) for both the initial manipulation and every counter-response.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome


# ---------------------------------------------------------------------------
# Internal helpers (mirrors atva1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _BallotOption:
    """Internal: one candidate ballot for a single voter.

    bullet_choice is set for bullet-voting ballots and None for
    compromise/bury ballots.
    """

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


def _ballot_to_option(ballot: StrategicBallot) -> _BallotOption:
    """Convert a StrategicBallot to a _BallotOption (infers bullet_choice from kind)."""
    if ballot.kind == "bullet":
        return _BallotOption(ballot=ballot, bullet_choice=ballot.preferences[0])
    return _BallotOption(ballot=ballot, bullet_choice=None)


def _tally_with_deviations(
    scheme: VotingScheme,
    situation: VotingSituation,
    deviations: dict[int, _BallotOption],
):
    """Call tally_votes_strategic with deviations split into overrides / bullet_choices.

    Compromise/bury ballots go into ``overrides``; bullet ballots go into
    ``bullet_choice_by_voter`` — exactly as BTVA does for single voters.
    """
    overrides = {v: opt.ballot for v, opt in deviations.items() if opt.bullet_choice is None}
    bullets = {v: opt.bullet_choice for v, opt in deviations.items() if opt.bullet_choice is not None}
    return tally_votes_strategic(
        scheme, situation, overrides=overrides, bullet_choice_by_voter=bullets
    )


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrategicResponse:
    """A voter's strategic response to another voter's manipulation."""

    responding_voter: int
    original_manipulator: int
    response_ballot: StrategicBallot

    # Outcomes
    baseline_outcome: str          # No manipulation
    after_manipulation_outcome: str  # After original voter manipulates
    after_response_outcome: str    # After response

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

    voter_sequence: tuple[int, ...]
    ballot_sequence: tuple[StrategicBallot, ...]
    outcome_sequence: tuple[str, ...]
    happiness_sequence: tuple[tuple[float, ...], ...]

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

    responses: list[StrategicResponse]
    iterative_sequences: list[IterativeStrategicSequence]

    fraction_manipulations_with_counter_response: float
    avg_sequence_length_until_convergence: float
    fraction_sequences_restore_original: float


# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------

def find_counter_responses(
    scheme: VotingScheme,
    situation: VotingSituation,
    manipulator: int,
    manipulator_ballot: StrategicBallot,
    *,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[StrategicResponse]:
    """Find strategic responses by other voters to a manipulation.

    Every other voter is given the full BTVA strategic repertoire
    (compromise/bury + bullet) to respond with.  The manipulator's ballot
    is routed through the correct tally interface based on its kind.

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        manipulator: Index of voter who manipulates.
        manipulator_ballot: The manipulator's strategic ballot.
        max_ballots_per_voter: Cap on compromise/bury options per responder.
        happiness_metric: How to measure happiness.

    Returns:
        List of strategic responses that improve the responding voter.
    """
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )

    # Route the manipulator's ballot correctly
    manip_opt = _ballot_to_option(manipulator_ballot)
    manip_deviation: dict[int, _BallotOption] = {manipulator: manip_opt}

    after_manip_outcome = _tally_with_deviations(scheme, situation, manip_deviation)
    after_manip_happiness = happiness_for_outcome(
        situation, after_manip_outcome.winner, metric=happiness_metric
    )

    responses: list[StrategicResponse] = []

    for responder in range(situation.n_voters):
        if responder == manipulator:
            continue

        # Try all strategic options for the responder (compromise/bury + bullet)
        for resp_opt in _generate_voter_ballot_options(
            scheme, situation, responder, max_ballots_per_voter=max_ballots_per_voter
        ):
            test_deviations = {**manip_deviation, responder: resp_opt}
            after_response_outcome = _tally_with_deviations(scheme, situation, test_deviations)
            after_response_happiness = happiness_for_outcome(
                situation, after_response_outcome.winner, metric=happiness_metric
            )

            if (
                after_response_happiness.per_voter[responder]
                > after_manip_happiness.per_voter[responder]
            ):
                responses.append(StrategicResponse(
                    responding_voter=responder,
                    original_manipulator=manipulator,
                    response_ballot=resp_opt.ballot,
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
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[IterativeStrategicSequence]:
    """Simulate iterative strategic voting sequences.

    Starting from the baseline, voters take turns making the best improving
    strategic move available to them (using the full BTVA strategy repertoire:
    compromise/bury + bullet voting).  Each voter may act at most once per
    simulation run.  A run stops when no remaining voter can improve, or
    ``max_iterations`` moves have been made.

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        max_iterations: Maximum number of strategic moves to simulate.
        max_ballots_per_voter: Cap on compromise/bury options per voter.
        happiness_metric: How to measure happiness.

    Returns:
        List of iterative sequences (one per initial move tried).
    """
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )

    sequences: list[IterativeStrategicSequence] = []

    for initial_voter in range(situation.n_voters):
        for init_opt in _generate_voter_ballot_options(
            scheme, situation, initial_voter, max_ballots_per_voter=max_ballots_per_voter
        ):
            # Initialize sequence state
            voter_seq: list[int] = [initial_voter]
            ballot_seq: list[StrategicBallot] = [init_opt.ballot]
            outcome_seq: list[str] = [baseline_outcome.winner]
            happiness_seq: list[tuple[float, ...]] = [tuple(baseline_happiness.per_voter)]

            current_deviations: dict[int, _BallotOption] = {initial_voter: init_opt}

            current_outcome = _tally_with_deviations(scheme, situation, current_deviations)
            current_happiness = happiness_for_outcome(
                situation, current_outcome.winner, metric=happiness_metric
            )
            outcome_seq.append(current_outcome.winner)
            happiness_seq.append(tuple(current_happiness.per_voter))

            # Iteratively let other voters make their best improving move
            for _ in range(max_iterations - 1):
                made_move = False

                for voter in range(situation.n_voters):
                    if voter in current_deviations:
                        continue  # Voter already deviated this run

                    best_gain = 0.0
                    best_opt: _BallotOption | None = None

                    for opt in _generate_voter_ballot_options(
                        scheme, situation, voter, max_ballots_per_voter=max_ballots_per_voter
                    ):
                        test_deviations = {**current_deviations, voter: opt}
                        test_outcome = _tally_with_deviations(scheme, situation, test_deviations)
                        test_happiness = happiness_for_outcome(
                            situation, test_outcome.winner, metric=happiness_metric
                        )

                        gain = (
                            test_happiness.per_voter[voter]
                            - current_happiness.per_voter[voter]
                        )
                        if gain > best_gain:
                            best_gain = gain
                            best_opt = opt

                    if best_opt is not None:
                        current_deviations[voter] = best_opt
                        current_outcome = _tally_with_deviations(
                            scheme, situation, current_deviations
                        )
                        current_happiness = happiness_for_outcome(
                            situation, current_outcome.winner, metric=happiness_metric
                        )

                        voter_seq.append(voter)
                        ballot_seq.append(best_opt.ballot)
                        outcome_seq.append(current_outcome.winner)
                        happiness_seq.append(tuple(current_happiness.per_voter))

                        made_move = True
                        break  # One move per iteration

                if not made_move:
                    break  # Sequence converged

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
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> Atva2Result:
    """Run ATVA-2 analysis: analyze counter-strategic voting.

    Uses the same strategic voting types as BTVA (compromise/bury + bullet)
    for both initial manipulations and counter-responses.

    Args:
        scheme: Voting scheme.
        situation: Voting situation.
        max_iterations: Maximum iterations for iterative sequences.
        max_ballots_per_voter: Cap on compromise/bury options per voter (0 = no cap).
        happiness_metric: How to measure happiness.

    Returns:
        ATVA-2 analysis result.
    """
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(
        situation, baseline_outcome.winner, metric=happiness_metric
    )

    all_responses: list[StrategicResponse] = []
    manipulations_checked = 0
    manipulations_with_responses = 0

    # For each voter, try every strategic ballot as a manipulation
    for manipulator in range(situation.n_voters):
        for manip_opt in _generate_voter_ballot_options(
            scheme, situation, manipulator, max_ballots_per_voter=max_ballots_per_voter
        ):
            responses = find_counter_responses(
                scheme,
                situation,
                manipulator,
                manip_opt.ballot,
                max_ballots_per_voter=max_ballots_per_voter,
                happiness_metric=happiness_metric,
            )

            manipulations_checked += 1
            if responses:
                manipulations_with_responses += 1
                all_responses.extend(responses)

    # Simulate iterative sequences
    sequences = simulate_iterative_strategic_voting(
        scheme,
        situation,
        max_iterations=max_iterations,
        max_ballots_per_voter=max_ballots_per_voter,
        happiness_metric=happiness_metric,
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
