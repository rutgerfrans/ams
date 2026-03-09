# Tactical Voting Analyst — AMS Lab

Python implementation of a **Basic Tactical Voting Analyst (BTVA)** and four **Advanced Tactical Voting Analyst (ATVA)** variants for the *Strategic Voting* lab of Agents and Multi-Agent Systems (AMS).

## Quickstart

```bash
# run tests
.venv/bin/python -m pytest

# BTVA
.venv/bin/btva voting_scenarios/sv_poll_1.abif --scheme borda

# ATVA (choose atva1 / atva2 / atva3 / atva4)
.venv/bin/python -m atva.cli atva1 voting_scenarios/sv_poll_1.abif --scheme borda
```

## Repository structure

```
btva/           Core BTVA package
  models.py       VotingScheme, VotingSituation
  parsing.py      .abif input parsing
  voting.py       Positional scoring rules + tie-breaking
  happiness.py    Happiness metrics (borda, rank_normalized)
  strategies.py   Strategic ballot types (bullet, compromise/bury)
  enumeration.py  Full-permutation enumeration (capped by --max-m)
  enumeration_bullet.py  Bullet-vote enumeration
  strategic_options.py   StrategicOption dataclass
  analysis.py     Risk computation + main run_btva() entry point
  cli.py          BTVA command-line interface
  experiments.py  Batch experiment runner -> CSV
  plot_results.py Tradeoff scatter plots from CSV

atva/           Advanced TVA package (4 variants)
  atva1_collusion.py          ATVA-1: voter collusion
  atva2_counter_strategic.py  ATVA-2: counter-strategic voting
  atva3_imperfect_knowledge.py ATVA-3: imperfect knowledge
  atva4_multiple_tactical.py  ATVA-4: multiple tactical voters
  cli.py          Unified ATVA CLI
  experiments.py  Batch experiment runner -> CSV
  plot_results.py ATVA-specific plots
  plot_tradeoffs.py Additional tradeoff plots

tests/          Unit tests (pytest)
voting_scenarios/ ~970 .abif scenario files
experiments/    CSV results and plot output
```

## Voting schemes

Four positional scoring rules:

| Scheme | Score vector |
|--------|-------------|
| **Plurality** | (1, 0, ..., 0) |
| **Vote-for-two** | (1, 1, 0, ..., 0) |
| **Anti-plurality (veto)** | (1, 1, ..., 1, 0) |
| **Borda** | (m-1, m-2, ..., 0) |

Ties are broken deterministically in lexicographic order (A < B < C < ...).

## Input format (`.abif`)

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

- First line: `# <m> candidates`
- Ballots: `count:ranking` (complete rankings; truncated ballots are padded)

## Strategic deviations

Two types of unilateral ballot deviations are enumerated per voter:

- **Bullet voting** — place a single alternative first, rest unchanged
- **Compromising / burying** — full permutation enumeration (capped by `--max-m`; defaults to 8)

An option is **tactical** iff it strictly improves the deviator’s happiness: H̃_i > H_i.

## Happiness metrics

| Metric | Formula | Range |
|--------|---------|-------|
| `borda` (default) | (m-1) - rank_i(w) | [0, m-1] |
| `rank_normalized` | 1 - rank_i(w) / (m-1) | [0, 1] |

## Risk metrics

| Metric | Meaning |
|--------|---------|
| `avg_gain_all_options` | Average happiness gain across all tactical options (incentive strength) |
| `fraction_change_winner` | Fraction of voters that can change the winner via a tactical option |

## ATVA variants

Each variant drops one limitation of the BTVA:

| Variant | Drops | Description |
|---------|-------|-------------|
| **ATVA-1** | Single-voter only | **Collusion** — coalitions of voters coordinate strategic ballots |
| **ATVA-2** | No counter-strategy | **Counter-strategic voting** — voters respond to others’ manipulations iteratively |
| **ATVA-3** | Perfect knowledge | **Imperfect knowledge** — strategic analysis under noisy/uncertain preferences |
| **ATVA-4** | Single tactical voter | **Multiple tactical voters** — several voters deviate simultaneously (independently) |

## CLI usage

### BTVA

```bash
.venv/bin/btva <input.abif> --scheme <scheme> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--scheme` | *(required)* | `plurality`, `vote_for_two`, `anti_plurality`, `borda` |
| `--happiness-metric` | `borda` | `borda` or `rank_normalized` |
| `--max-m` | `8` | Cap for permutation enumeration; falls back to bullet-only if m > cap |
| `--strategy-limit` | `3` | Max tactical options printed per voter (`-1` for all) |
| `--risk-method` | `avg_gain_all_options` | `avg_gain_all_options` or `fraction_change_winner` |

### ATVA

```bash
.venv/bin/python -m atva.cli <variant> <input.abif> --scheme <scheme> [options]
```

Common options are the same as BTVA. Variant-specific options:

| Variant | Option | Default |
|---------|--------|---------|
| `atva1` | `--max-coalition-size` | `3` |
| `atva2` | `--max-iterations` | `5` |
| `atva3` | `--n-scenarios` | `5` |
| `atva3` | `--noise-level` | `0.3` |
| `atva3` | `--seed` | `42` |
| `atva4` | `--max-tactical-voters` | `3` |
| `atva4` | `--find-equilibria` | off |

## Experiments

Batch-run all (scenario, scheme) pairs and write a dated CSV:

```bash
# BTVA experiments
.venv/bin/python -m btva.experiments \
  --include 'sv_poll_*_small.abif' \
  --include 'sv_poll_*_medium.abif'

# ATVA experiments (runs all 4 variants)
.venv/bin/python -m atva.experiments \
  --include 'sv_poll_*_small.abif'
```

Output: `experiments/results_YYYY-MM-DD.csv` (BTVA) and `experiments/atva_results_YYYY-MM-DD.csv` (ATVA).

## Plotting

```bash
# BTVA tradeoff plots
.venv/bin/python -m btva.plot_results --out-dir experiments/plots

# ATVA plots
.venv/bin/python -m atva.plot_results
```

BTVA produces two scatter plots (happiness vs. risk, one per risk metric). ATVA produces variant-specific plots (coalition analysis, counter-strategic sequences, uncertainty, tactical interference).

If `--csv` is omitted, the plotter auto-selects the newest dated CSV in `experiments/`.

## Tests

```bash
.venv/bin/python -m pytest
```

Covers parsing, voting rules, happiness computation, strategic enumeration, CLI smoke tests, and experiments.

### LLM note
The tests and this readme were generated by the use of an llm for convenienve purposes.
