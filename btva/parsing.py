from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import VotingScheme, VotingSituation


@dataclass(frozen=True)
class ParsedInput:
    scheme: VotingScheme
    situation: VotingSituation


def load_input_file(path: str | Path) -> ParsedInput:
  """Load an input file describing scheme + voting situation.

  Supported formats:
  - Our project JSON format (strict complete rankings).

  Expected format:
  {
    "voting_scheme": "plurality"|"vote_for_two"|"anti_plurality"|"borda",
    "voting_situation": {
      "voters": [
        ["C","B","A"],
        ["A","C","B"],
        ...
      ]
    },
    "strategies": {
      "enable": ["compromise_or_bury", "bullet"],
      "max_swaps": 1
    }
  }

  Note: the `strategies` block is accepted but not acted upon yet.
  """

  p = Path(path)
  raw = json.loads(p.read_text(encoding="utf-8"))

  scheme = VotingScheme(raw["voting_scheme"])
  voters = tuple(tuple(v) for v in raw["voting_situation"]["voters"])
  situation = VotingSituation(voters)
  situation.validate()

  return ParsedInput(scheme=scheme, situation=situation)


def load_strategies_block(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return raw.get("strategies", {})
