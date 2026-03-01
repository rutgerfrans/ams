"""Advanced Tactical Voting Analyst (ATVA).

This package extends BTVA by dropping one of the four limitations:

1. ATVA-1: Analyzes voter collusion (multiple voters coordinating)
2. ATVA-2: Considers counter-strategic voting (other voters responding)
3. ATVA-3: Does not assume perfect knowledge (uncertainty about preferences)
4. ATVA-4: Considers multiple voters voting tactically simultaneously

Each ATVA variant is implemented in its own module.
"""

from btva.models import VotingScheme, VotingSituation

__all__ = ["VotingScheme", "VotingSituation"]
