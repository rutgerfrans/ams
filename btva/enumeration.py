from __future__ import annotations

import itertools

from .happiness import borda_happiness_for_outcome
from .models import VotingScheme, VotingSituation
from .strategic_options import StrategicOption
from .strategies import StrategicBallot
from .voting import tally_votes, tally_votes_strategic


def enumerate_all_permutations_options_for_voter(
    scheme: VotingScheme,
    situation: VotingSituation,
    voter_index: int,
    *,
    include_no_change: bool = False,
) -> list[StrategicOption]:
    """Enumerate strategic options for voter i by trying ALL permutations.

    Warning: this is factorial in m (O(m!)). Only feasible for small m.

    We generate every possible full ranking (permutation of alternatives) for
    voter i, treat each as a tactical ballot v~_ij, compute the resulting
    outcome O~, compute per-voter happiness under O~, and package everything in
    StrategicOption.

    include_no_change:
        If False (default), skip the sincere ballot itself.
    """

    situation.validate()
    if not (0 <= voter_index < situation.n_voters):
        raise IndexError("voter_index out of range")

    baseline_outcome = tally_votes(scheme, situation)
    baseline_happy = borda_happiness_for_outcome(situation, baseline_outcome.winner)

    sincere = situation.voters_preferences[voter_index]

    options: list[StrategicOption] = []
    for perm in itertools.permutations(situation.alternatives):
        if not include_no_change and perm == sincere:
            continue

        tactical = StrategicBallot(
            voter_index=voter_index,
            kind="compromising_burying",
            preferences=tuple(perm),
        )

        out = tally_votes_strategic(scheme, situation, overrides={voter_index: tactical})
        happy = borda_happiness_for_outcome(situation, out.winner)

        options.append(
                StrategicOption(
                voter_index=voter_index,
                strategy_kind="compromising_burying",
                tactical_ballot=tactical,
                strategic_outcome=out.winner,
                baseline_outcome=baseline_outcome.winner,
                strategic_happiness=happy,
                baseline_happiness=baseline_happy,
            )
        )

    return options


def enumerate_all_permutations_options(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    include_no_change: bool = False,
) -> dict[int, list[StrategicOption]]:
    """Enumerate strategic options for every voter using ALL permutations."""

    situation.validate()

    return {
        i: enumerate_all_permutations_options_for_voter(
            scheme, situation, i, include_no_change=include_no_change
        )
        for i in range(situation.n_voters)
    }
