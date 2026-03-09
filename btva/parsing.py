from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import VotingScheme, VotingSituation


@dataclass(frozen=True)
class ParsedInput:
    scheme: VotingScheme
    situation: VotingSituation

# load an abif-like preference profile from a file, returning a ParsedInput with the voting situation and a placeholder scheme.
# parsing = to >, and missing votes are filled on lexicographic order of candidate ids.
def load_input_file(path: str | Path) -> ParsedInput:
  p = Path(path)
  if p.suffix.lower() != ".abif":
    raise ValueError("Only .abif input files are supported")

  text = p.read_text(encoding="utf-8")
  m_alts: int | None = None
  voters: list[tuple[str, ...]] = []

  for raw_line in text.splitlines():
    line = raw_line.strip()
    if not line:
      continue

    if line.startswith("#"):
      parts = line[1:].strip().split()
      if parts and parts[0].isdigit():
        m_alts = int(parts[0])
      continue

    if line.startswith("="):
      continue

    if ":" not in line:
      raise ValueError(f"Invalid ballot line (missing ':'): {line}")
    count_str, ranking_str = line.split(":", 1)
    count = int(count_str.strip())
    ranking_str = ranking_str.strip()

    ranking_str = ranking_str.replace("=", ">")

    alts = [a.strip() for a in ranking_str.split(">") if a.strip()]

    if m_alts is not None:
      expected = [str(i) for i in range(m_alts)]
      seen = set(alts)
      missing = [a for a in expected if a not in seen]
      alts = alts + missing

    voters.extend([tuple(alts)] * count)

  if m_alts is None:
    raise ValueError("Missing '# <m> candidates' header")

  expected = tuple(str(i) for i in range(m_alts))
  expected_set = set(expected)
  for ballot in voters:
    if len(ballot) != m_alts:
      raise ValueError(f"Ballot does not rank exactly {m_alts} candidates: {ballot}")
    if set(ballot) != expected_set:
      raise ValueError(f"Ballot candidates don't match expected 0..{m_alts-1}: {ballot}")
    if len(set(ballot)) != len(ballot):
      raise ValueError(f"Ballot contains duplicate candidates after parsing: {ballot}")

  situation = VotingSituation(tuple(voters))
  situation.validate()

  return ParsedInput(scheme=VotingScheme.PLURALITY, situation=situation)

def load_strategies_block(path: str | Path) -> dict[str, Any]:
  return {}
