from __future__ import annotations

import argparse
from pathlib import Path

from .models import VotingScheme
from .analysis import run_btva
from .parsing import load_input_file


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

    result = run_btva(scheme, parsed.situation)

    print(f"scheme: {result.outcome.scheme.value}")
    print(f"winner: {result.outcome.winner}")
    print(f"H_i: {list(result.happiness.per_voter)}")
    print(f"H: {result.happiness.total}")
    if args.show_scores:
        for alt in sorted(result.outcome.scores):
            print(f"{alt}: {result.outcome.scores[alt]}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())