#ATVA-2: Counter-Strategic Voting Analysis.

from __future__ import annotations
import itertools
from dataclasses import dataclass
from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome

@dataclass(frozen=True)
class _BallotOption:
    ballot: StrategicBallot
    bullet_choice: str | None

# strategic option for a coaltion of voters
def _generate_voter_ballot_options(
    scheme: VotingScheme,
    situation: VotingSituation,
    voter_idx: int,
    *,
    max_ballots_per_voter: int = 5,
) -> list[_BallotOption]:
    
    sincere = situation.voters_preferences[voter_idx]
    options: list[_BallotOption] = []

    #Compromise / bbury
    comp_bury: list[_BallotOption] = []
    for perm in itertools.permutations(situation.alternatives):
        if perm == sincere:
            continue
        ballot = StrategicBallot(voter_index=voter_idx, kind="compromising_burying", preferences=perm)
        comp_bury.append(_BallotOption(ballot=ballot, bullet_choice=None))
        if max_ballots_per_voter > 0 and len(comp_bury) >= max_ballots_per_voter:
            break
    options.extend(comp_bury)

    #bullet voting (not applicable to plurality)
    if scheme != VotingScheme.PLURALITY:
        for chosen in situation.alternatives:
            others = [a for a in sincere if a != chosen]
            ballot = StrategicBallot(voter_index=voter_idx, kind="bullet", preferences=tuple([chosen] + others))
            options.append(_BallotOption(ballot=ballot, bullet_choice=chosen))

    return options


def _ballot_to_option(ballot: StrategicBallot) -> _BallotOption:
    if ballot.kind == "bullet":
        return _BallotOption(ballot=ballot, bullet_choice=ballot.preferences[0])
    return _BallotOption(ballot=ballot, bullet_choice=None)


def _tally_with_deviations(
    scheme: VotingScheme,
    situation: VotingSituation,
    deviations: dict[int, _BallotOption],
):
    overrides = {v: opt.ballot for v, opt in deviations.items() if opt.bullet_choice is None}
    bullets = {v: opt.bullet_choice for v, opt in deviations.items() if opt.bullet_choice is not None}
    return tally_votes_strategic(scheme, situation, overrides=overrides, bullet_choice_by_voter=bullets)

#voter's strategic response to another voter's manipulation
@dataclass(frozen=True)
class StrategicResponse:
    responding_voter: int
    original_manipulator: int
    response_ballot: StrategicBallot

    baseline_outcome: str 
    after_manipulation_outcome: str
    after_response_outcome: str

    baseline_happiness: float
    after_manipulation_happiness: float
    after_response_happiness: float

    @property
    def response_improves_responder(self) -> bool:
        return self.after_response_happiness > self.after_manipulation_happiness

    @property
    def response_restores_original(self) -> bool:
        return self.after_response_outcome == self.baseline_outcome

# Sequence of strategic moves and counter-moves
@dataclass(frozen=True)
class IterativeStrategicSequence:
    voter_sequence: tuple[int, ...]
    ballot_sequence: tuple[StrategicBallot, ...]
    outcome_sequence: tuple[str, ...]
    happiness_sequence: tuple[tuple[float, ...], ...]

    @property
    def converged(self) -> bool:
        if len(self.outcome_sequence) < 2:
            return False
        return self.outcome_sequence[-1] == self.outcome_sequence[-2]

    @property
    def length(self) -> int:
        return len(self.voter_sequence)

#Result of ATVA-2 counter-strategic analysiss
@dataclass(frozen=True)
class Atva2Result:
    scheme: VotingScheme
    baseline_outcome: str
    baseline_total_happiness: float

    responses: list[StrategicResponse]
    iterative_sequences: list[IterativeStrategicSequence]

    fraction_manipulations_with_counter_response: float
    avg_sequence_length_until_convergence: float
    fraction_sequences_restore_original: float

#analysis functions
def find_counter_responses(
    scheme: VotingScheme,
    situation: VotingSituation,
    manipulator: int,
    manipulator_ballot: StrategicBallot,
    *,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[StrategicResponse]:
    
    situation.validate()
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(situation, baseline_outcome.winner, metric=happiness_metric)

    # Route the manipulator's ballot correctly
    manip_opt = _ballot_to_option(manipulator_ballot)
    manip_deviation: dict[int, _BallotOption] = {manipulator: manip_opt}

    after_manip_outcome = _tally_with_deviations(scheme, situation, manip_deviation)
    after_manip_happiness = happiness_for_outcome(situation, after_manip_outcome.winner, metric=happiness_metric)

    responses: list[StrategicResponse] = []

    for responder in range(situation.n_voters):
        if responder == manipulator:
            continue

        for resp_opt in _generate_voter_ballot_options(scheme, situation, responder, max_ballots_per_voter=max_ballots_per_voter):
            test_deviations = {**manip_deviation, responder: resp_opt}
            after_response_outcome = _tally_with_deviations(scheme, situation, test_deviations)
            after_response_happiness = happiness_for_outcome(situation, after_response_outcome.winner, metric=happiness_metric)

            if (after_response_happiness.per_voter[responder]> after_manip_happiness.per_voter[responder]):
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

#Simulate iterative strategic voting sequences
def simulate_iterative_strategic_voting(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    max_iterations: int = 5,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[IterativeStrategicSequence]:
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(situation, baseline_outcome.winner, metric=happiness_metric)

    sequences: list[IterativeStrategicSequence] = []

    for initial_voter in range(situation.n_voters):
        for init_opt in _generate_voter_ballot_options(scheme, situation, initial_voter, max_ballots_per_voter=max_ballots_per_voter):
            voter_seq: list[int] = [initial_voter]
            ballot_seq: list[StrategicBallot] = [init_opt.ballot]
            outcome_seq: list[str] = [baseline_outcome.winner]
            happiness_seq: list[tuple[float, ...]] = [tuple(baseline_happiness.per_voter)]

            current_deviations: dict[int, _BallotOption] = {initial_voter: init_opt}

            current_outcome = _tally_with_deviations(scheme, situation, current_deviations)
            current_happiness = happiness_for_outcome(situation, current_outcome.winner, metric=happiness_metric)
            outcome_seq.append(current_outcome.winner)
            happiness_seq.append(tuple(current_happiness.per_voter))

            for _ in range(max_iterations - 1):
                made_move = False

                for voter in range(situation.n_voters):
                    if voter in current_deviations:
                        continue

                    best_gain = 0.0
                    best_opt: _BallotOption | None = None

                    for opt in _generate_voter_ballot_options(scheme, situation, voter, max_ballots_per_voter=max_ballots_per_voter):
                        test_deviations = {**current_deviations, voter: opt}
                        test_outcome = _tally_with_deviations(scheme, situation, test_deviations)
                        test_happiness = happiness_for_outcome(situation, test_outcome.winner, metric=happiness_metric)

                        gain = (test_happiness.per_voter[voter]- current_happiness.per_voter[voter])
                        if gain > best_gain:
                            best_gain = gain
                            best_opt = opt

                    if best_opt is not None:
                        current_deviations[voter] = best_opt
                        current_outcome = _tally_with_deviations(scheme, situation, current_deviations)
                        current_happiness = happiness_for_outcome(situation, current_outcome.winner, metric=happiness_metric)

                        voter_seq.append(voter)
                        ballot_seq.append(best_opt.ballot)
                        outcome_seq.append(current_outcome.winner)
                        happiness_seq.append(tuple(current_happiness.per_voter))

                        made_move = True
                        break

                if not made_move:
                    break

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
    
    situation.validate()

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(situation, baseline_outcome.winner, metric=happiness_metric)

    all_responses: list[StrategicResponse] = []
    manipulations_checked = 0
    manipulations_with_responses = 0

    for manipulator in range(situation.n_voters):
        for manip_opt in _generate_voter_ballot_options(scheme, situation, manipulator, max_ballots_per_voter=max_ballots_per_voter):
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

    sequences = simulate_iterative_strategic_voting(
        scheme,
        situation,
        max_iterations=max_iterations,
        max_ballots_per_voter=max_ballots_per_voter,
        happiness_metric=happiness_metric,
    )

    fraction_with_response = (manipulations_with_responses / manipulations_checked if manipulations_checked > 0 else 0.0)

    avg_seq_length = (sum(s.length for s in sequences) / len(sequences)if sequences else 0.0)

    sequences_restore = sum(1 for s in sequences if len(s.outcome_sequence) >= 2 and s.outcome_sequence[-1] == s.outcome_sequence[0])
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
