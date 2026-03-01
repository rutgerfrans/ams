# Advanced Tactical Voting Analyst (ATVA)

This directory contains implementations of **Advanced Tactical Voting Analysts (ATVAs)** that extend the Basic TVA (BTVA) by dropping one of its four limitations.

## BTVA Limitations

The BTVA has the following limitations:

1. **Single-voter manipulation only**: TVA only analyzes single-voter manipulation; voter collusion is not considered.
2. **No counter-strategic voting**: TVA does not consider the issue of counter-strategic voting.
3. **Perfect knowledge**: TVA has perfect knowledge, i.e., it knows the true preferences of all voters.
4. **Single tactical voter in calculations**: In calculating H and H̃, TVA only considers tactical voting by a single voter (i.e., it does not consider situations in which several voters vote tactically at the same time).

## ATVA Variants

Each ATVA variant drops exactly **one** of these limitations:

### ATVA-1: Voter Collusion (`atva1_collusion.py`)

**Drops limitation #1**: Analyzes voter collusion where multiple voters coordinate their strategic votes.

**Key features:**
- Enumerates coalitions of voters (size 2 to max_coalition_size)
- Computes coalition happiness gains
- Identifies coalitions that can change the winner
- Metrics: max coalition size needed to change winner, fraction of coalitions that succeed

**Example:**
```bash
.venv\Scripts\python -m atva.cli atva1 voting_scenarios/sv_poll_1.abif --scheme borda --max-coalition-size 3
```

### ATVA-2: Counter-Strategic Voting (`atva2_counter_strategic.py`)

**Drops limitation #2**: Considers how voters respond strategically to others' strategic votes.

**Key features:**
- Finds counter-responses to manipulations
- Simulates iterative strategic voting sequences
- Tracks convergence of strategic behavior
- Metrics: fraction of manipulations with counter-response, average sequence length

**Example:**
```bash
.venv\Scripts\python -m atva.cli atva2 voting_scenarios/sv_poll_1.abif --scheme borda --max-iterations 5
```

### ATVA-3: Imperfect Knowledge (`atva3_imperfect_knowledge.py`)

**Drops limitation #3**: Analyzes strategic voting under uncertainty about others' preferences.

**Key features:**
- Models voters' beliefs as probability distributions over scenarios
- Evaluates strategic options under uncertainty
- Computes expected happiness and variance
- Identifies "robust" options (good in all scenarios)
- Metrics: expected gain, fraction of robust options, average regret

**Example:**
```bash
.venv\Scripts\python -m atva.cli atva3 voting_scenarios/sv_poll_1.abif --scheme borda --n-scenarios 5 --noise-level 0.3
```

### ATVA-4: Multiple Tactical Voters (`atva4_multiple_tactical.py`)

**Drops limitation #4**: Considers multiple voters voting tactically simultaneously (independently, not coordinated).

**Key features:**
- Enumerates scenarios with multiple independent tactical voters
- Analyzes when tactical voters help/hurt each other
- Finds Nash equilibria in the voting game
- Metrics: fraction where all/some tactical voters benefit, effect on total happiness

**Example:**
```bash
.venv\Scripts\python -m atva.cli atva4 voting_scenarios/sv_poll_1.abif --scheme borda --max-tactical-voters 3 --find-equilibria
```

## Key Differences

| Aspect | BTVA | ATVA-1 | ATVA-2 | ATVA-3 | ATVA-4 |
|--------|------|--------|--------|--------|--------|
| **Voters deviating** | 1 | 2+ (coordinated) | 1→2→... (sequential) | 1 | 2+ (independent) |
| **Coordination** | None | Yes (coalition) | Reactive | None | None |
| **Information** | Perfect | Perfect | Perfect | Imperfect | Perfect |
| **Dynamics** | Static | Static | Iterative | Static | Simultaneous |

## Usage

### Command-line Interface

All ATVA variants use the same CLI interface:

```bash
python -m atva.cli <variant> <input_file> --scheme <scheme> [options]
```

Where:
- `variant`: One of `atva1`, `atva2`, `atva3`, `atva4`
- `input_file`: Path to `.abif` file
- `scheme`: One of `plurality`, `vote_for_two`, `anti_plurality`, `borda`

### Common Options

- `--happiness-metric {borda,rank_normalized}`: Happiness metric (default: borda)
- `--max-ballots-per-voter N`: Limit strategic ballots per voter (default: 5)

### Variant-Specific Options

**ATVA-1:**
- `--max-coalition-size N`: Maximum coalition size (default: 3)

**ATVA-2:**
- `--max-iterations N`: Maximum counter-strategic iterations (default: 5)

**ATVA-3:**
- `--n-scenarios N`: Number of belief scenarios (default: 5)
- `--noise-level FLOAT`: Uncertainty level 0-1 (default: 0.3)
- `--seed N`: Random seed (default: 42)

**ATVA-4:**
- `--max-tactical-voters N`: Max simultaneous tactical voters (default: 3)
- `--find-equilibria`: Compute Nash equilibria (can be slow)

## Implementation Notes

### Computational Complexity

- **ATVA-1**: Exponential in coalition size (binomial combinations)
- **ATVA-2**: Polynomial in iterations, but sequences can be long
- **ATVA-3**: Linear in number of scenarios
- **ATVA-4**: Exponential in number of tactical voters; Nash equilibrium computation is exponential in total voters

For tractability, all variants limit:
- The number of strategic ballots considered per voter
- The maximum size/number of coalitions/tactical voters
- The depth of iterative sequences

### Simplifications

To keep the implementation tractable, we make some simplifications:

1. **Strategic ballots**: We primarily use bullet voting (putting one alternative first) rather than enumerating all permutations
2. **ATVA-1**: Coalitions try to maximize their collective happiness
3. **ATVA-2**: Voters respond one at a time in sequence
4. **ATVA-3**: Belief scenarios are generated with simple noise models
5. **ATVA-4**: Nash equilibrium search is limited for larger games

### Extension Points

Each module is designed to be extensible:

- **More sophisticated strategic ballots**: Add compromising/burying strategies
- **Better belief models (ATVA-3)**: Learn from polling data, historical elections
- **Game-theoretic refinements (ATVA-4)**: Subgame perfect equilibria, trembling hand
- **Coalition formation (ATVA-1)**: Model coalition formation process

## Integration with BTVA

All ATVA modules use the core BTVA components:

- `btva.models`: `VotingScheme`, `VotingSituation`
- `btva.voting`: `tally_votes`, `tally_votes_strategic`
- `btva.happiness`: `happiness_for_outcome`, `HappinessMetric`
- `btva.strategies`: `StrategicBallot`

This ensures consistency and allows comparing ATVA results with BTVA baselines.

## Testing

To test the ATVA modules:

```bash
.venv\Scripts\python -m pytest tests/test_atva*.py
```

(Note: You'll need to create tests for the ATVA modules)

## Running Experiments

Like BTVA, you can run batch experiments across multiple scenarios:

```bash
# Run all ATVA variants on small scenarios
.venv\Scripts\python -m atva.experiments --include 'sv_poll_*_small.abif'

# Run specific variants
.venv\Scripts\python -m atva.experiments --include 'sv_poll_*_small.abif' --variants atva1 atva4

# Adjust parameters for faster runs
.venv\Scripts\python -m atva.experiments \
  --include 'sv_poll_*_small.abif' \
  --max-coalition-size 2 \
  --max-tactical-voters 2 \
  --n-scenarios 3
```

This creates a CSV file: `experiments/atva_results_<date>.csv`

## Generating Plots

After running experiments, generate visualizations:

```bash
.venv\Scripts\python -m atva.plot_results
```

This creates plots in `experiments/atva_plots/`:

**ATVA-1 plots:**
- `atva1_coalition_size.png` - Min coalition size to change winner vs baseline happiness
- `atva1_coalition_vulnerability.png` - Coalition success rate vs average gain

**ATVA-2 plots:**
- `atva2_counter_strategic.png` - Counter-response rate vs sequence length

**ATVA-3 plots:**
- `atva3_uncertainty.png` - Robust options vs regret under uncertainty

**ATVA-4 plots:**
- `atva4_tactical_interference.png` - Mutual benefit vs self-harm
- `atva4_happiness_impact.png` - Total happiness impact of multiple tactical voters

**Comparison plots:**
- `scheme_comparison_radar.png` - Radar chart comparing schemes across all ATVA metrics
- `variant_comparison_time.png` - Execution time by variant
- `variant_comparison_baseline.png` - Baseline happiness consistency check

## Example Workflow

1. **Start with BTVA** to understand single-voter manipulation:
   ```bash
   .venv\Scripts\btva voting_scenarios/sv_poll_1.abif --scheme borda
   ```

2. **Run ATVA-1** to see if small coalitions can change the outcome:
   ```bash
   .venv\Scripts\python -m atva.cli atva1 voting_scenarios/sv_poll_1.abif --scheme borda
   ```

3. **Run ATVA-2** to see if counter-strategic voting is likely:
   ```bash
   .venv\Scripts\python -m atva.cli atva2 voting_scenarios/sv_poll_1.abif --scheme borda
   ```

4. **Run ATVA-3** to assess robustness under uncertainty:
   ```bash
   .venv\Scripts\python -m atva.cli atva3 voting_scenarios/sv_poll_1.abif --scheme borda
   ```

5. **Run ATVA-4** to find Nash equilibria:
   ```bash
   .venv\Scripts\python -m atva.cli atva4 voting_scenarios/sv_poll_1.abif --scheme borda --find-equilibria
   ```

6. **Run batch experiments** and generate plots:
   ```bash
   # Run experiments
   .venv\Scripts\python -m atva.experiments --include 'sv_poll_*_small.abif'
   
   # Generate plots
   .venv\Scripts\python -m atva.plot_results
   ```

## Future Work

Potential extensions:

- **ATVA experiments module**: Batch analysis across scenarios like BTVA
- **Comparative analysis**: Tools to compare all variants on the same scenario
- **Visualization**: Plot coalition power, strategic sequences, belief distributions
- **More voting rules**: Extend to ranked-choice methods (IRV, etc.)
- **Real data**: Analyze real election data with uncertainty

## References

This implementation is based on the AMS Strategic Voting Lab assignment. For theoretical background, see the literature on:

- Gibbard-Satterthwaite theorem
- Coalition manipulation in voting
- Iterated voting games
- Voting under uncertainty
- Nash equilibria in voting

---

**Status**: All four ATVA variants implemented and ready to use!
