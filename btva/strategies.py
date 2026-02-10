from __future__ import annotations

from dataclasses import dataclass

from .models import VotingScheme, VotingSituation


@dataclass(frozen=True)
class StrategicBallot:
    """A tactically modified preference list for a single voter."""

    voter_index: int
    kind: str  # "compromise_or_bury" | "bullet"
    preferences: tuple[str, ...]


def _validate_ballot(ballot: tuple[str, ...], expected_alts: tuple[str, ...]) -> None:
    if len(ballot) != len(expected_alts):
        raise ValueError("Ballot length must equal number of alternatives")
    if set(ballot) != set(expected_alts):
        raise ValueError("Ballot must be a permutation of the alternatives")


def apply_compromise_or_bury(
    situation: VotingSituation,
    voter_index: int,
    *,
    move_up: str | None = None,
    move_up_to: int | None = None,
    move_down: str | None = None,
    move_down_to: int | None = None,
) -> StrategicBallot:
    """Compromise/bury tactic (assignment treats them as equivalent).

    We implement this as a minimal, well-defined transformation:

    - Take the voter's sincere ranking.
    - "Compromise" = move `move_up` UP to a desired target index (closer to the top)
    - "Bury" = move `move_down` DOWN to a desired target index (closer to the bottom)

    The assignment notes they often occur in parallel; our enumeration step can
    choose to apply either one or both.

    Parameters:
    - move_up: alternative to move upward (optional)
    - move_up_to: target index to insert move_up at (0-based). Must be < its current index.
    - move_down: alternative to move downward (optional)
    - move_down_to: target index to insert move_down at (0-based). Must be > its current index.

    At least one of (move_up, move_down) must be provided.
    """

    situation.validate()
    prefs = list(situation.voters_preferences[voter_index])
    expected = situation.alternatives

    if move_up is None and move_down is None:
        raise ValueError("At least one of move_up/move_down must be provided")

    if move_up is not None:
        if move_up not in prefs:
            raise ValueError("move_up must be a valid alternative")
        if move_up_to is None:
            raise ValueError("move_up_to must be provided when move_up is set")
        if not (0 <= move_up_to < len(prefs)):
            raise ValueError("move_up_to is out of range")

        cur = prefs.index(move_up)
        if move_up_to >= cur:
            raise ValueError("Compromise requires move_up_to be above the current position")

        prefs.pop(cur)
        prefs.insert(move_up_to, move_up)

    if move_down is not None:
        if move_down not in prefs:
            raise ValueError("move_down must be a valid alternative")
        if move_down_to is None:
            raise ValueError("move_down_to must be provided when move_down is set")
        if not (0 <= move_down_to < len(prefs)):
            raise ValueError("move_down_to is out of range")

        cur = prefs.index(move_down)
        if move_down_to <= cur:
            raise ValueError("Bury requires move_down_to be below the current position")

        prefs.pop(cur)
        prefs.insert(move_down_to, move_down)

    ballot = tuple(prefs)
    _validate_ballot(ballot, expected)
    return StrategicBallot(voter_index=voter_index, kind="compromise_or_bury", preferences=ballot)


def apply_bullet_vote(
    situation: VotingSituation,
    scheme: VotingScheme,
    voter_index: int,
    *,
    chosen: str,
) -> StrategicBallot:
    """Bullet voting (assignment version).

    The assignment restricts bullet voting to: "assigning points only to one
    alternative" (the chosen one). The number of points is always the maximum
    possible for that scheme.

    For our positional-vector implementation, we can model this as:
    - Put `chosen` first
    - Put all other alternatives after it (their relative order won't matter
      because they should receive 0 points under bullet voting)

    Important (assignment): bullet voting cannot be applied to plurality.

    Note: Our base tally implementation always uses full rankings + the scheme's
    positional vector. To properly support bullet voting we will extend tallying
    in the next step to allow "masked" vectors for the bullet voter.

    For now, this function only returns the strategic ballot ordering.
    """

    situation.validate()

    if scheme == VotingScheme.PLURALITY:
        raise ValueError("Bullet voting cannot be applied to plurality (assignment).")

    sincere = list(situation.voters_preferences[voter_index])
    if chosen not in sincere:
        raise ValueError("chosen must be a valid alternative")

    others = [a for a in sincere if a != chosen]
    ballot = tuple([chosen] + others)
    _validate_ballot(ballot, situation.alternatives)
    return StrategicBallot(voter_index=voter_index, kind="bullet", preferences=ballot)
