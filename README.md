# BTVA — Basic Tactical Voting Analyst (AMS Lab)

This repository contains a **basic scaffold** for the *Strategic Voting* lab of **Agents and Multi-Agent Systems (KEN 4111)**.

The goal of the assignment is to implement a **Tactical Voting Analyst (TVA)**. In particular, this codebase focuses on the **Basic TVA (BTVA)** variant described in the assignment:

- single-voter manipulation only (no collusion)
- no counter-strategic voting
- perfect knowledge of true preferences
- only one voter votes strategically at a time

## What the assignment expects (high level)

### Input
A BTVA takes:

1. A **voting scheme** (one of: plurality, vote-for-two, veto/anti-plurality, Borda)
2. A **voting situation**: true preference lists of $n$ voters over $m$ alternatives (constraints: $m,n>2$)

### Output
For a given voting scheme and voting situation, a BTVA should produce:

1. Non-strategic voting outcome $O$
2. Per-voter happiness levels $H_i$ (definition chosen by you)
3. Overall happiness $H = \sum_i H_i$
4. Per-voter strategic options set $S_i$ (possibly empty)
5. Overall **risk of strategic voting** (definition chosen by you)

## Repository structure

- `btva/` — package code
	- `models.py` — core data models and validation (`VotingScheme`, `VotingSituation`)
	- `parsing.py` — JSON input parsing
	- `voting.py` — voting scheme implementation (score vectors, tallying, tie-breaking)
- `tests/` — unit tests (currently: voting scheme tests)
- `Strategic_Voting_Description.pdf` — assignment description
- `pyproject.toml` — Python project config

## Implemented so far

### Voting schemes ✅
The 4 required voting schemes are implemented in `btva/voting.py` using the positional vectors from the assignment:

- **Plurality**: `{1, 0, …, 0}`
- **Vote-for-two**: `{1, 1, 0, …, 0}`
- **Anti-plurality / veto**: `{1, 1, …, 0}`
- **Borda**: `{m-1, m-2, …, 0}`

Tie-breaking is **deterministic**: for equal top score, the winner is the alternative that comes first in **lexicographical order** (`A < B < C < …`).

## Input format (current)

Right now, `btva/parsing.py` supports an easy-to-edit **JSON** input format.

Example `input.json`:

```json
{
	"voting_scheme": "borda",
	"voting_situation": {
		"voters": [
			["A", "B", "C"],
			["A", "C", "B"],
			["B", "A", "C"]
		]
	},
	"strategies": {
		"enable": ["compromise_or_bury", "bullet"],
		"max_swaps": 1
	}
}
```

Notes:

- Each voter must rank **exactly the same alternatives**.
- Constraints are enforced: **$m,n>2$**.
- The `strategies` block is accepted in the JSON but is not acted upon yet (it will be used when implementing strategic option enumeration).

## Development setup

This is a plain Python project. A virtual environment already exists in `.venv/` in this workspace.

### Run tests

```bash
.venv/bin/python -m pytest
```

## Progress (status at the end)

### Completed
- [x] Extracted assignment requirements (inputs + 5 required outputs)
- [x] Implemented and tested the 4 voting schemes
- [x] Implemented deterministic tie-breaking (lexicographic)
- [x] JSON input parsing + voting situation validation

### In progress / next
- [ ] CLI runner that prints the 5 required output bullet points
- [ ] Define and implement the happiness function $H_i$
- [ ] Implement strategic option generation per voter ($S_i$): compromise/bury + bullet (with scheme constraints)
- [ ] Define and implement “risk of strategic voting” measure
- [ ] Add end-to-end tests for the report output