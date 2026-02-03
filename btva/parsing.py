from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import VotingScheme, VotingSituation


@dataclass(frozen=True)
class ParsedInput:
    scheme: VotingScheme
    situation: VotingSituation


def load_input_file(path: str | Path) -> ParsedInput:
  """Load an ABIF-like preference profile.

  This project only supports a strict-ranking input format aligned with the
  assignment's preference-matrix notion.

  Expected file shape (example):

  # 5 candidates
  =0 : [0]
  =1 : [1]
  ...
  1:4>2>3>1>0
  1:3>1>4>2>0

  Ballot lines are `count:ranking` where `ranking` is an order using `>`.

  Some dataset files include `=` inside a ballot to indicate indifference (tie),
  e.g. `2=0`. The assignment's preference-matrix input assumes strict rankings,
  so we *linearize* such ties deterministically by replacing `=` with `>` and
  keeping the left-to-right order as written in the file.

  Note: the scheme is not present in this format; the CLI must provide it.
  """

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
      # Example: "# 5 candidates"
      parts = line[1:].strip().split()
      if parts and parts[0].isdigit():
        m_alts = int(parts[0])
      continue

    # Candidate mapping lines like "=3 : [3]" are not needed for our model;
    # we identify alternatives by their numeric ids as strings.
    if line.startswith("="):
      continue

    if ":" not in line:
      raise ValueError(f"Invalid ballot line (missing ':'): {line}")
    count_str, ranking_str = line.split(":", 1)
    count = int(count_str.strip())
    ranking_str = ranking_str.strip()

    # Linearize ballot ties (e.g. "2=0") into a strict order "2>0".
    ranking_str = ranking_str.replace("=", ">")

    alts = [a.strip() for a in ranking_str.split(">") if a.strip()]

    # If ballots are truncated, append missing candidates deterministically.
    # This keeps the TVA input compatible with the assignment's strict
    # preference lists while allowing dataset files to omit bottom-ranked
    # alternatives.
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

  # Placeholder scheme; caller (CLI) should override.
  return ParsedInput(scheme=VotingScheme.PLURALITY, situation=situation)


def load_strategies_block(path: str | Path) -> dict[str, Any]:
  # No strategies block in .abif input format for this project.
  return {}
