from __future__ import annotations
from .happiness import HappinessMetric, happiness_for_outcome
from .models import VotingScheme, VotingSituation
from .strategic_options import StrategicOption
from .strategies import StrategicBallot
from .voting import tally_votes, tally_votes_strategic

#Enumerate bullet-voting options for a single voter.
def enumerate_bullet_options_for_voter(
    scheme: VotingScheme,
    situation: VotingSituation,
    voter_index: int,
    *,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> list[StrategicOption]:

    situation.validate()
    if scheme == VotingScheme.PLURALITY:
        return []

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happy = happiness_for_outcome(situation, baseline_outcome.winner, metric=happiness_metric)

    options: list[StrategicOption] = []
    for chosen in situation.alternatives:

        sincere = list(situation.voters_preferences[voter_index])
        others = [a for a in sincere if a != chosen]
        tactical = StrategicBallot(voter_index=voter_index, kind="bullet", preferences=tuple([chosen] + others))

        out = tally_votes_strategic(scheme, situation, bullet_choice_by_voter={voter_index: chosen})
        happy = happiness_for_outcome(situation, out.winner, metric=happiness_metric)

        options.append(
            StrategicOption(
                voter_index=voter_index,
                strategy_kind="bullet",
                tactical_ballot=tactical,
                strategic_outcome=out.winner,
                baseline_outcome=baseline_outcome.winner,
                strategic_happiness=happy,
                baseline_happiness=baseline_happy,
            )
        )
    return options


def enumerate_bullet_options(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    happiness_metric: HappinessMetric = HappinessMetric.BORDA,
) -> dict[int, list[StrategicOption]]:

    situation.validate()
    return {
        i: enumerate_bullet_options_for_voter(
            scheme, situation, i, happiness_metric=happiness_metric
        )
        for i in range(situation.n_voters)
    }
