# simsetup_v3: simulated switching statistics and NIST tests

This repository holds the simulation and analysis code, extracted bitstreams, result tables and NIST SP 800-22 test outputs for the IL2231 course paper on simsetup_v3, a GPU-based micromagnetic simulation workflow for a stochastically switching magnetic tunnel junction. Each simulation run applies one current pulse to the free layer and records whether the magnetization switched. The bitstreams below are built from these simulated outcomes. They are simulation data and not output from a hardware random number generator.

## Contents

| Path | Content |
|---|---|
| `simsetup_v3/runner_scheduled.py` | Main runner: reads `params.csv`, schedules one MuMax3 run per seed across the configured GPUs, classifies each run and appends to `results/run_summary.csv`. |
| `simsetup_v3/params.csv` | Parameter sets to run (pulse width, temperature, current, seed range). |
| `simsetup_v3/modules/config.py` | Machine and protocol settings: MuMax3 path, GPU IDs, threshold, early-stop criteria, output paths. Edit before running. |
| `simsetup_v3/modules/template.mx3` | MuMax3 input template for the free layer; placeholders are filled per run. |
| `simsetup_v3/modules/iter_run.py` | Runs one simulation (one seed), extracts the m_z table and writes per-run metadata. |
| `simsetup_v3/modules/autoplot.py`, `simsetup_v3/modules/utils.py` | Automatic summary plot and terminal formatting helpers. |
| `simsetup_v3/build_results_summary.py`, `simsetup_v3/build_invalid_list.py` | Summarise switching counts per parameter set and list invalid runs. |
| `simsetup_v3/test_iter.py` | Single-run smoke test. |
| `simsetup_v3/tools/` | Post-processing utilities: metadata checks, invalid-run cleanup, magnetization trace plots, switching-time analysis, OVF snapshot conversion, single-run tool, and the NIST input builder/checker used to cut a bitstream into NIST input files. |
| `analysis/paper_config.py` | Paths and settings shared by the analysis scripts (results folder, switching threshold \|m_z\| = 0.8, pulse start time). |
| `analysis/Paper_plotter.py` | Reads the per-seed magnetization tables and metadata, classifies each run as switched, not switched or invalid, and draws the trace, overlay and bitstream figures. |
| `analysis/sweep_plots.py` | Coarse and fine pulse-width sweeps and the temperature sweep; also writes `plots/sweep_summary.csv`. |
| `analysis/polarity_plots.py` | Forward versus reversed polarity comparison. |
| `analysis/repro_plots.py` | Reproducibility figure for the same seeds run on two machines. |
| `analysis/export_bitstream.py` | Exports the analysed bitstream for 0.2088 ns, 300 K, -0.100 mA to `data/`. |
| `analysis/device_diagram.py`, `analysis/setup_diagram.py` | Device and workflow diagrams used in the paper. |
| `data/bitstream_24k.txt` | 156 x 156 = 24,336 valid bits (seed order, 1 = switched, invalid runs removed). |
| `data/bitstream_full.txt` | 173 x 173 = 29,929 valid bits from the full 30,000-run set; this is the stream given to the NIST tests. |
| `data/*_seeds.csv` | Per-bit record for each bitstream: index, seed, bit and final m_z. |
| `results/results_tables.md` | Switching probability tables (coarse sweep, fine sweep, temperature, polarity) with binomial standard errors. |
| `results/nist_results.md` | Summary of the NIST SP 800-22 p-values and the tests not applicable at this length. |
| `nist/nist_input_1eq_switched.txt`, `nist/nist_input_1eq_notswitched.txt` | NIST input files for both bit conventions (1 = switched, and its complement). |
| `nist/run_nist.sh` | Builds the NIST suite and runs the six applicable tests on one input file. |
| `nist/raw_A_1eq_switched/`, `nist/raw_B_1eq_notswitched/` | Unedited NIST STS output (`finalAnalysisReport.txt` and per-test `stats.txt`, `results.txt`). |

## Reproducing the results

Requirements: Python 3.10 or newer with `numpy`, `pandas` and `matplotlib`; MuMax3 3.10 with a CUDA GPU for the simulations.

1. Edit `simsetup_v3/modules/config.py` (MuMax3 path, GPU IDs) and `simsetup_v3/params.csv`, then run `python runner_scheduled.py` from `simsetup_v3/`. Results are written to `simsetup_v3/results/`. The analysis expects `results/tables/<pulse>ns_<T>K_<I>mA/seedNNNN_<hash>.txt` and the matching `results/metadata/` JSON files.
2. The analysis scripts read `simsetup_v3/results/` by default; set the environment variable `SIMSETUP_RESULTS` to use another folder. The coarse sweep and the reversed-polarity runs were stored in separate result folders; set `SIMSETUP_COARSE_RESULTS` and `SIMSETUP_POLARITY_RESULTS` for them.
3. From `analysis/`, run `python Paper_plotter.py`, `python sweep_plots.py`, `python polarity_plots.py` and `python repro_plots.py`. Figures are written to `analysis/plots/`.
4. Run `python export_bitstream.py` to regenerate the bitstream in `data/`.

### NIST tests

The tests use the NIST Statistical Test Suite, version 2.1.2, compiled without changes. Download it from NIST (https://csrc.nist.gov/projects/random-bit-generation/documentation-and-software), copy `nist/run_nist.sh` into the unpacked `sts-2.1.2` folder and run it from there:

```
bash run_nist.sh /absolute/path/to/nist/nist_input_1eq_switched.txt
```

The script feeds one 29,929-bit ASCII sequence to `assess` and runs Frequency, Block Frequency (M = 128), Cumulative Sums, Runs, Longest Run of Ones and the Discrete Fourier Transform test at alpha = 0.01. The remaining tests need longer sequences and were not run. The output appears in `experiments/AlgorithmTesting/` and should match the files in `nist/raw_*`.
