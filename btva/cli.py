from __future__ import annotations

import argparse
from pathlib import Path

from .models import VotingScheme
from .parsing import load_input_file
from .voting import tally_votes


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="btva",
        description="Basic Tactical Voting Analyst (BTVA) — tally positional voting rules.",
    )

    p.add_argument(
        "input",
        type=str,
        help="Path to an .abif input file.",
    )
    p.add_argument(
        "--scheme",
        required=True,
        choices=[s.value for s in VotingScheme],
        help="Voting scheme to apply (required because .abif inputs do not include the scheme).",
    )
    p.add_argument(
        "--show-scores",
        action="store_true",
        help="Print full score table.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    parsed = load_input_file(Path(args.input))
    scheme: VotingScheme = VotingScheme(args.scheme)

    outcome = tally_votes(scheme, parsed.situation)

    print(f"scheme: {outcome.scheme.value}")
    print(f"winner: {outcome.winner}")
    if args.show_scores:
        for alt in sorted(outcome.scores):
            print(f"{alt}: {outcome.scores[alt]}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())