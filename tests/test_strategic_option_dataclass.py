from __future__ import annotations

from btva.happiness import HappinessResult
from btva.strategic_options import StrategicOption
from btva.strategies import StrategicBallot


def test_strategic_option_properties() -> None:
    baseline = HappinessResult(outcome="A", per_voter=(3, 1, 0))
    strategic = HappinessResult(outcome="B", per_voter=(2, 2, 0))

    opt = StrategicOption(
        voter_index=1,
        strategy_kind="bullet",
        tactical_ballot=StrategicBallot(voter_index=1, kind="bullet", preferences=("B", "A", "C")),
        strategic_outcome="B",
        baseline_outcome="A",
        strategic_happiness=strategic,
        baseline_happiness=baseline,
    )

    assert opt.H_i == 1
    assert opt.H_tilde_i == 2
    assert opt.H == 4
    assert opt.H_tilde == 4
