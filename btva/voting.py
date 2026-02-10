from __future__ import annotations

from dataclasses import dataclass

from .models import VotingScheme, VotingSituation
from .strategies import StrategicBallot


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


def tally_votes_strategic(
    scheme: VotingScheme,
    situation: VotingSituation,
    *,
    overrides: dict[int, StrategicBallot] | None = None,
    bullet_choice_by_voter: dict[int, str] | None = None,
) -> VotingOutcome:
    """Tally votes with optional per-voter tactical overrides.

    This supports the BTVA assumption that at most one voter votes strategically,
    but the implementation allows more for convenience.

    Bullet voting (assignment): the voter assigns points only to one alternative
    (the chosen one), with the maximum number of points for the scheme.

    Notes:
    - Bullet voting is not allowed for plurality.
    - For vote-for-two and anti-plurality, the "maximum" is 1.
    - For Borda, the "maximum" is m-1.
    """

    situation.validate()
    m = situation.m_alternatives
    vec = scoring_vector(scheme, m)

    overrides = overrides or {}
    bullet_choice_by_voter = bullet_choice_by_voter or {}

    # Initialize all alternatives with 0 score (ensures deterministic ordering).
    scores: dict[str, int] = {a: 0 for a in sorted(situation.alternatives)}

    for voter_idx, sincere_pref in enumerate(situation.voters_preferences):
        pref = sincere_pref
        if voter_idx in overrides:
            pref = overrides[voter_idx].preferences

        if voter_idx in bullet_choice_by_voter:
            if scheme == VotingScheme.PLURALITY:
                raise ValueError("Bullet voting cannot be applied to plurality (assignment).")

            chosen = bullet_choice_by_voter[voter_idx]
            if chosen not in situation.alternatives:
                raise ValueError(f"Invalid bullet choice: {chosen}")

            max_points = m - 1 if scheme == VotingScheme.BORDA else 1
            scores[chosen] += max_points
            continue

        for position, alt in enumerate(pref):
            scores[alt] += vec[position]

    max_score = max(scores.values())
    winners = [a for a, s in scores.items() if s == max_score]
    winner = sorted(winners)[0]

    return VotingOutcome(scheme=scheme, scores=scores, winner=winner)
