# ATVA-1: Voter Collusion.

from __future__ import annotations
import itertools
from dataclasses import dataclass
from itertools import combinations, product
import math
from btva.models import VotingScheme, VotingSituation
from btva.strategies import StrategicBallot
from btva.voting import tally_votes, tally_votes_strategic
from btva.happiness import HappinessMetric, happiness_for_outcome

@dataclass(frozen=True)
class _BallotOption:
    ballot: StrategicBallot
    bullet_choice: str | None

# strategic option for a coaltion of voters
@dataclass(frozen=True)
class CoalitionOption:
    voter_indices: tuple[int, ...]
    tactical_ballots: dict[int, StrategicBallot]
    baseline_outcome: str
    strategic_outcome: str
    coalition_baseline_happiness: float
    coalition_strategic_happiness: float

    #total happiness gain for coalition
    @property
    def coalition_gain(self) -> float:
        return self.coalition_strategic_happiness - self.coalition_baseline_happiness

    # does coalition option change the winner?
    @property
    def changes_winner(self) -> bool:
        return self.strategic_outcome != self.baseline_outcome

# result of ATVA-1 analysis
@dataclass(frozen=True)
class Atva1Result:
    scheme: VotingScheme
    baseline_outcome: str
    baseline_total_happiness: float
    coalition_options: dict[int, list[CoalitionOption]]
    max_coalition_size_that_changes_winner: int
    fraction_of_coalitions_that_change_winner: float
    avg_coalition_gain: float

#Generate strategic ballot options for a single coalition member.
#Mirrors BTVA's two strategy types, comprimise/bury and bullet voting
def _generate_voter_ballot_options(
    scheme: VotingScheme,
    situation: VotingSituation,
    voter_idx: int,
    *,
    max_ballots_per_voter: int = 5,
) -> list[_BallotOption]:

    sincere = situation.voters_preferences[voter_idx]
    options: list[_BallotOption] = []

    # cap check on compbury
    comp_bury: list[_BallotOption] = []
    for perm in itertools.permutations(situation.alternatives):
        if perm == sincere:
            continue
        ballot = StrategicBallot(voter_index=voter_idx, kind="compromising_burying", preferences=perm)
        comp_bury.append(_BallotOption(ballot=ballot, bullet_choice=None))
        if max_ballots_per_voter > 0 and len(comp_bury) >= max_ballots_per_voter:
            break
    options.extend(comp_bury)

    # excludes bv for plurality
    if scheme != VotingScheme.PLURALITY:
        for chosen in situation.alternatives:
            others = [a for a in sincere if a != chosen]
            ballot = StrategicBallot(voter_index=voter_idx, kind="bullet", preferences=tuple([chosen] + others))
            options.append(_BallotOption(ballot=ballot, bullet_choice=chosen))

    return options

# enumariting coaltion options for a given coalition size k.
def enumerate_coalition_options_size_k(
    scheme: VotingScheme,
    situation: VotingSituation,
    coalition_size: int,
    *,
    max_ballots_per_voter: int = 5,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[CoalitionOption]:
    
    situation.validate()
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(situation, baseline_outcome.winner, metric=happiness_metric)

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

        #skip coalitions where any member has no tactical options
        if any(len(opts) == 0 for opts in ballot_options_by_voter):
            continue

        # Try all combinations of ballot options across coalition members
        for ballot_combo in product(*ballot_options_by_voter):
            overrides: dict[int, StrategicBallot] = {}
            bullet_choices: dict[int, str] = {}

            for voter_idx, opt in zip(coalition_indices, ballot_combo):
                if opt.bullet_choice is not None:
                    bullet_choices[voter_idx] = opt.bullet_choice
                else:
                    overrides[voter_idx] = opt.ballot

            strategic_outcome = tally_votes_strategic(
                scheme,
                situation,
                overrides=overrides,
                bullet_choice_by_voter=bullet_choices,
            )

            strategic_happiness = happiness_for_outcome(situation, strategic_outcome.winner, metric=happiness_metric)
            coalition_baseline = sum(baseline_happiness.per_voter[i] for i in coalition_indices)
            coalition_strategic = sum(strategic_happiness.per_voter[i] for i in coalition_indices)

            if coalition_strategic > coalition_baseline:
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
    
    situation.validate()
    baseline_outcome = tally_votes(scheme, situation)
    baseline_happiness = happiness_for_outcome(situation, baseline_outcome.winner, metric=happiness_metric)
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

    max_size_changes_winner = 0
    n = situation.n_voters
    max_k = min(max_coalition_size, n)

    total_coalitions_evaluated = sum(math.comb(n, k) for k in range(2, max_k + 1))
    coalitions_with_winner_change: set[tuple[int, ...]] = set()
    best_gain_by_coalition: dict[tuple[int, ...], float] = {}

    for size, opts in coalition_options.items():
        for opt in opts:
            coalition = opt.voter_indices

            if opt.changes_winner:
                coalitions_with_winner_change.add(coalition)
                if size > max_size_changes_winner:
                    max_size_changes_winner = size

            prev_best = best_gain_by_coalition.get(coalition, float("-inf"))
            if opt.coalition_gain > prev_best:
                best_gain_by_coalition[coalition] = opt.coalition_gain

    fraction_change_winner = (
        (len(coalitions_with_winner_change) / total_coalitions_evaluated)
        if total_coalitions_evaluated > 0
        else 0.0
    )
    avg_gain = (
        (sum(best_gain_by_coalition.values()) / len(best_gain_by_coalition))
        if best_gain_by_coalition
        else 0.0
    )

    return Atva1Result(
        scheme=scheme,
        baseline_outcome=baseline_outcome.winner,
        baseline_total_happiness=baseline_happiness.total,
        coalition_options=coalition_options,
        max_coalition_size_that_changes_winner=max_size_changes_winner,
        fraction_of_coalitions_that_change_winner=fraction_change_winner,
        avg_coalition_gain=avg_gain,
    )
