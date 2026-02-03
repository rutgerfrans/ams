# TVA — Tactical Voting Analyst (AMS Lab)

This repository contains a **basic scaffold** for the *Strategic Voting* lab of **Agents and Multi-Agent Systems (KEN 4111)**.

The goal of the assignment is to implement a **Tactical Voting Analyst (TVA)**.

This codebase currently implements the **Basic TVA (BTVA)** foundations and is being extended towards **ATVA-1** (the assignment’s *Advanced TVA* variant that drops limitation 1: *single-voter-only manipulation*, i.e. it considers **collusion**).

### BTVA assumptions (from the assignment)

- single-voter manipulation only (**no collusion**)
- no counter-strategic voting
- perfect knowledge of true preferences
- only one voter votes strategically at a time

### ATVA-1 change (minimum ATVA)

ATVA-1 drops the first limitation: it **does** consider voter collusion (but still keeps the other three limitations).

> Note: per the assignment, an “ATVA-x” drops *exactly one* of the four BTVA limitations.

## What the assignment expects (high level)

### Input
A BTVA takes:

1. A **voting scheme** (one of: plurality, vote-for-two, veto/anti-plurality, Borda)
2. A **voting situation**: true preference lists of $n$ voters over $m$ alternatives (constraints: $m,n>2$)

### Output
For a given voting scheme and voting situation, a BTVA (and hence also our ATVA-1 extension) should produce:

1. Non-strategic voting outcome $O$
2. Per-voter happiness levels $H_i$ (definition chosen by you)
3. Overall happiness $H = \sum_i H_i$
4. Per-voter strategic options set $S_i$ (possibly empty)
5. Overall **risk of strategic voting** (definition chosen by you)

## Repository structure

- `btva/` — package code
	- `models.py` — core data models and validation (`VotingScheme`, `VotingSituation`)
	- `parsing.py` — `.abif` input parsing (assignment-style strict rankings)
	- `voting.py` — voting scheme implementation (score vectors, tallying, tie-breaking)
- `tests/` — unit tests
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

## Input format (`.abif`)

This project expects voting situations in an **ABIF-like** text format (files named like `sv_poll_1.abif`).

Minimal example:

```text
# 5 candidates
=0 : [0]
=1 : [1]
=2 : [2]
=3 : [3]
=4 : [4]
1:4>2>3>1>0
1:3>1>4>2>0
```

Rules/assumptions:

- The first line declares the number of candidates: `# <m> candidates`.
- Ballots are `count:ranking`.
- Rankings must be **complete** (each ballot must contain every candidate exactly once).
- If a ballot contains `=` (tied ranks/indifference), we **linearize** it by converting `=` to `>` while keeping the left-to-right order.
	- Example: `1:4>1>3>2=0` is treated as `1:4>1>3>2>0`.
- If a ballot is **truncated** (doesn’t list all candidates), we append the missing candidates at the bottom in ascending candidate-id order.
	- Example (4 candidates): `1:1>2` is treated as `1:1>2>0>3`.

## Development setup

This is a plain Python project. A virtual environment already exists in `.venv/` in this workspace.

### Run tests

```bash
.venv/bin/python -m pytest
```

## Run the CLI

The project defines a console script called `btva`.

### `.abif` input

```bash
.venv/bin/btva path/to/sv_poll_1.abif --scheme borda --show-scores
```

## Progress (status at the end)

### Completed
- [x] Extracted assignment requirements (inputs + 5 required outputs)
- [x] Implemented and tested the 4 voting schemes
- [x] Implemented deterministic tie-breaking (lexicographic)
- [x] JSON input parsing + voting situation validation
- [x] Minimal CLI to run a scheme and show winner/scores

### In progress / next
- [ ] Expand CLI output into a full TVA “report” (all 5 required outputs)
- [ ] Define and implement the happiness function $H_i$
- [ ] Implement BTVA strategic option enumeration per voter ($S_i$): compromise/bury + bullet (with scheme constraints)
- [ ] Define and implement “risk of strategic voting” measure
- [ ] **ATVA-1 (collusion)**: extend strategic option enumeration from single voter to coalitions (keep other BTVA assumptions)
- [ ] Add end-to-end tests for the report output