from __future__ import annotations

from dataclasses import dataclass

from .models import VotingScheme, VotingSituation


@dataclass(frozen=True)
class VotingOutcome:
    """Result of tallying a voting situation under a voting scheme."""

    scheme: VotingScheme
    scores: dict[str, int]
    winner: str


def scoring_vector(scheme: VotingScheme, m: int) -> list[int]:
    """Return positional scoring vector as described in the assignment.

    The vector is ordered from 1st preference to m-th preference.
    """

    if m <= 0:
        raise ValueError("m must be positive")

    if scheme == VotingScheme.PLURALITY:
        return [1] + [0] * (m - 1)
    if scheme == VotingScheme.VOTE_FOR_TWO:
        if m < 2:
            raise ValueError("vote_for_two requires m >= 2")
        return [1, 1] + [0] * (m - 2)
    if scheme == VotingScheme.ANTI_PLURALITY:
        # Veto: everyone gets 1 point except last ranked alternative.
        return [1] * (m - 1) + [0]
    if scheme == VotingScheme.BORDA:
        return list(range(m - 1, -1, -1))

    raise ValueError(f"Unsupported voting scheme: {scheme}")


def tally_votes(scheme: VotingScheme, situation: VotingSituation) -> VotingOutcome:
    """Compute scores and winner for the given scheme and situation.

    Tie-breaking: if multiple alternatives have the highest score, pick the one
    that comes first in lexicographical order (A < B < C < ...).
    """

    situation.validate()
    m = situation.m_alternatives
    vec = scoring_vector(scheme, m)

    # Initialize all alternatives with 0 score (ensures deterministic ordering).
    scores: dict[str, int] = {a: 0 for a in sorted(situation.alternatives)}

    for pref in situation.voters_preferences:
        for position, alt in enumerate(pref):
            scores[alt] += vec[position]

    max_score = max(scores.values())
    winners = [a for a, s in scores.items() if s == max_score]
    winner = sorted(winners)[0]

    return VotingOutcome(scheme=scheme, scores=scores, winner=winner)


__all__ = ["VotingOutcome", "tally_votes", "scoring_vector"]