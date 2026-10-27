# ============================================================
# Switching Time Analysis
#
# Generates:
#   1. Stable switching CDF
#   2. Instantaneous switching probability
#   3. Settling probability
#   4. Stable switching CDF (custom threshold)
# ============================================================

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# PROJECT PATH
# ============================================================

# switching_time_analysis.py is inside:
#     simsetup_v3/tools/
#
# Therefore:
#     PROJECT_ROOT = simsetup_v3/

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Allow imports from simsetup_v3/
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# CONFIG / UTILITIES
# ============================================================

from modules.config import (
    TABLES_DIR,
    MZ_THRESHOLD,
)

from modules.utils import (
    format_title,
)


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

TABLES_ROOT = PROJECT_ROOT / TABLES_DIR

# ============================================================
# OPTIONS
# ============================================================

PLOT_STABLE_CDF = True
PLOT_INSTANTANEOUS = True
PLOT_SETTLING = True
PLOT_CUSTOM_THRESHOLD = False


# ============================================================
# HELPERS
# ============================================================

def print_title(text):
    print()
    print(format_title("=" * 70))
    print(format_title(text.center(70)))
    print(format_title("=" * 70))

def get_tables_folder(
    pulse_ns,
    temperature_K,
    current_mA,
):
    folder_name = (
        f"{pulse_ns:.4f}ns_"
        f"{int(temperature_K)}K_"
        f"{current_mA:.3f}mA"
    )

    return TABLES_ROOT / folder_name

def read_table(table_file):
    """
    Reads either
        t mx my mz
    or
        t mx1 my1 mz1 mx2 my2 mz2
    """

    df = pd.read_csv(
        table_file,
        sep=r"\s+",
        comment="#",
        header=None,
    )

    if len(df) == 0:
        return None

    if df.shape[1] == 4:

        df.columns = [
            "t",
            "mx",
            "my",
            "mz",
        ]

        return pd.DataFrame({
            "time_ns": df["t"] * 1e9,
            "mz": df["mz"],
        })

    elif df.shape[1] == 7:

        df.columns = [
            "t",
            "mx1",
            "my1",
            "mz1",
            "mx2",
            "my2",
            "mz2",
        ]

        return pd.DataFrame({
            "time_ns": df["t"] * 1e9,
            "mz": df["mz2"],
        })

    else:

        print(f"Skipping invalid table: {table_file}")

        return None


# ============================================================
# STABILITY DETECTION
# ============================================================

def detect_stable_state(df, threshold):
    """
    Finds the first time after which the magnetization
    never leaves the stable region.

    Returns
    -------
    state :
        SWITCHED
        NOT_SWITCHED
        INVALID

    stable_time :
        float (ns) or None
    """

    mz = df["mz"].to_numpy()
    t = df["time_ns"].to_numpy()

    # -----------------------------
    # switched
    # -----------------------------

    mask = mz <= -threshold

    if mask[-1]:

        suffix = np.flip(
            np.cumprod(
                np.flip(mask.astype(int))
            )
        ).astype(bool)

        idx = np.argmax(suffix)

        if suffix[idx]:
            return "SWITCHED", t[idx]

    # -----------------------------
    # not switched
    # -----------------------------

    mask = mz >= threshold

    if mask[-1]:

        suffix = np.flip(
            np.cumprod(
                np.flip(mask.astype(int))
            )
        ).astype(bool)

        idx = np.argmax(suffix)

        if suffix[idx]:
            return "NOT_SWITCHED", t[idx]

    return "INVALID", None


# ============================================================
# LOAD ONE SWEEP POINT
# ============================================================

def load_runs(
    pulse_ns,
    temperature_K,
    current_mA,
    threshold,
    custom_threshold=None,
):

    tables_folder = get_tables_folder(
        pulse_ns,
        temperature_K,
        current_mA,
    )

    table_files = sorted(
        tables_folder.glob("*")
    )

    print(
        f"Reading tables... {len(table_files)} found"
    )

    runs = []

    for table_file in table_files:

        df = read_table(table_file)

        if df is None:
            continue

        state, stable_time = detect_stable_state(
            df,
            threshold,
        )

        run = {

            "df": df,

            "state": state,

            "stable_time": stable_time,

        }

        if custom_threshold is not None:

            c_state, c_time = detect_stable_state(
                df,
                custom_threshold,
            )

            run["custom_state"] = c_state
            run["custom_time"] = c_time

        runs.append(run)

    print(
        f"Loaded {len(runs)} runs."
    )

    return runs


# ============================================================
# PARAMS
# ============================================================

PARAMS_FILE = PROJECT_ROOT / "params.csv"

params = pd.read_csv(PARAMS_FILE)

print_title("Switching Time Analysis")

print(
    f"Found {len(params)} sweep points\n"
)

for i, row in params.iterrows():

    current_mA = row["current_A"] * 1000
    temperature_K = int(row["temperature_K"])

    tables_folder = get_tables_folder(
        row["pulse_ns"],
        temperature_K,
        current_mA,
    )

    print(f"    Checking: {tables_folder}")
    print(f"    Exists:   {tables_folder.exists()}")

    if tables_folder.exists():
        print(
            f"    Contents: {len(list(tables_folder.iterdir()))} items"
        )
    else:
        print("    FOLDER DOES NOT EXIST")

    n_tables = len(
        list(tables_folder.glob("*"))
    )

    print(
        f"{i+1:>2}. "
        f"Pulse={row['pulse_ns']:.4f} ns | "
        f"T={int(row['temperature_K'])} K | "
        f"I={current_mA:.3f} mA | "
        f"{n_tables} tables"
    )

print()

if PLOT_CUSTOM_THRESHOLD:

    while True:

        try:

            CUSTOM_THRESHOLD = float(
                input(
                    "Enter custom stability threshold (0-1): "
                )
            )

            if 0 < CUSTOM_THRESHOLD < 1:
                break

        except:
            pass

        print("Threshold must be between 0 and 1.")

else:

    CUSTOM_THRESHOLD = None


# ============================================================
# RUN ANALYSIS
# ============================================================

input("\nPress Enter to begin analysis...")


# ============================================================
# ANALYSIS OPTIONS
# ============================================================

# Print the result of every individual run
PRINT_INDIVIDUAL_RUNS = True

# Print switching-time statistics
PRINT_TIME_STATISTICS = True

# Number of decimal places for probabilities
PROBABILITY_DECIMALS = 4

# Number of decimal places for time values
TIME_DECIMALS = 4


# ============================================================
# RESULT CONTAINERS
# ============================================================

all_results = []


# ============================================================
# ANALYSIS HELPERS
# ============================================================

def calculate_summary(runs):
    """
    Calculate the basic statistics for one sweep point.

    Parameters
    ----------
    runs : list of dict
        Output from load_runs().

    Returns
    -------
    summary : dict
    """

    total = len(runs)

    switched_runs = [
        run for run in runs
        if run["state"] == "SWITCHED"
    ]

    not_switched_runs = [
        run for run in runs
        if run["state"] == "NOT_SWITCHED"
    ]

    invalid_runs = [
        run for run in runs
        if run["state"] == "INVALID"
    ]

    switched = len(switched_runs)
    not_switched = len(not_switched_runs)
    invalid = len(invalid_runs)

    if total > 0:

        p_switched = switched / total
        p_not_switched = not_switched / total
        p_invalid = invalid / total

    else:

        p_switched = 0.0
        p_not_switched = 0.0
        p_invalid = 0.0

    switching_times = [
        run["stable_time"]
        for run in switched_runs
        if run["stable_time"] is not None
    ]

    if switching_times:

        switching_times = np.asarray(
            switching_times,
            dtype=float,
        )

        time_min = np.min(switching_times)
        time_max = np.max(switching_times)
        time_mean = np.mean(switching_times)
        time_median = np.median(switching_times)
        time_std = np.std(
            switching_times,
            ddof=0,
        )

    else:

        time_min = None
        time_max = None
        time_mean = None
        time_median = None
        time_std = None

    return {

        "total": total,

        "switched": switched,
        "not_switched": not_switched,
        "invalid": invalid,

        "p_switched": p_switched,
        "p_not_switched": p_not_switched,
        "p_invalid": p_invalid,

        "switching_times": switching_times,

        "time_min": time_min,
        "time_max": time_max,
        "time_mean": time_mean,
        "time_median": time_median,
        "time_std": time_std,

    }


def print_run_result(run_number, run):
    """
    Print the classification of one simulation run.
    """

    state = run["state"]
    stable_time = run["stable_time"]

    if stable_time is None:

        time_text = "N/A"

    else:

        time_text = (
            f"{stable_time:.{TIME_DECIMALS}f} ns"
        )

    print(
        f"    Run {run_number:>4}: "
        f"{state:<13} | "
        f"stable time = {time_text}"
    )


def print_summary(summary):
    """
    Print the summary statistics for one sweep point.
    """

    print()
    print(format_title("-" * 70))
    print(format_title("SWEEP SUMMARY".center(70)))
    print(format_title("-" * 70))

    print(
        f"    Total runs       : "
        f"{summary['total']}"
    )

    print(
        f"    Switched         : "
        f"{summary['switched']} "
        f"({summary['p_switched']:.{PROBABILITY_DECIMALS}f})"
    )

    print(
        f"    Not switched     : "
        f"{summary['not_switched']} "
        f"({summary['p_not_switched']:.{PROBABILITY_DECIMALS}f})"
    )

    print(
        f"    Invalid          : "
        f"{summary['invalid']} "
        f"({summary['p_invalid']:.{PROBABILITY_DECIMALS}f})"
    )

    if PRINT_TIME_STATISTICS:

        print()

        print(
            format_title(
                "SWITCHING TIME STATISTICS"
            )
        )

        if summary["time_min"] is None:

            print(
                "    No switched runs."
            )

        else:

            print(
                f"    Minimum          : "
                f"{summary['time_min']:.{TIME_DECIMALS}f} ns"
            )

            print(
                f"    Maximum          : "
                f"{summary['time_max']:.{TIME_DECIMALS}f} ns"
            )

            print(
                f"    Mean             : "
                f"{summary['time_mean']:.{TIME_DECIMALS}f} ns"
            )

            print(
                f"    Median           : "
                f"{summary['time_median']:.{TIME_DECIMALS}f} ns"
            )

            print(
                f"    Std. deviation   : "
                f"{summary['time_std']:.{TIME_DECIMALS}f} ns"
            )


# ============================================================
# MAIN ANALYSIS LOOP
# ============================================================

for i, row in params.iterrows():

    pulse_ns = float(
        row["pulse_ns"]
    )

    temperature_K = int(
        row["temperature_K"]
    )

    current_mA = float(
        row["current_A"]
    ) * 1000.0


    # --------------------------------------------------------
    # SWEEP HEADER
    # --------------------------------------------------------

    print()
    print(format_title("=" * 70))

    print(
        format_title(
            f"SWEEP POINT {i + 1}/{len(params)}"
        )
    )

    print(format_title("=" * 70))

    print(
        f"    Pulse width       : "
        f"{pulse_ns:.4f} ns"
    )

    print(
        f"    Temperature       : "
        f"{temperature_K} K"
    )

    print(
        f"    Current           : "
        f"{current_mA:.3f} mA"
    )

    print(
        f"    Stability threshold: "
        f"{MZ_THRESHOLD:.3f}"
    )


    # --------------------------------------------------------
    # LOAD RUNS
    # --------------------------------------------------------

    runs = load_runs(
        pulse_ns,
        temperature_K,
        current_mA,
        MZ_THRESHOLD,
        CUSTOM_THRESHOLD,
    )


    # --------------------------------------------------------
    # BASIC SUMMARY
    # --------------------------------------------------------

    summary = calculate_summary(
        runs
    )


    # --------------------------------------------------------
    # INDIVIDUAL RUN RESULTS
    # --------------------------------------------------------

    if PRINT_INDIVIDUAL_RUNS:

        print()
        print(
            format_title(
                "INDIVIDUAL RUN RESULTS"
            )
        )

        if len(runs) == 0:

            print(
                "    No valid table files found."
            )

        else:

            for run_number, run in enumerate(
                runs,
                start=1,
            ):

                print_run_result(
                    run_number,
                    run,
                )


    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print_summary(
        summary
    )


    # --------------------------------------------------------
    # STORE RESULTS IN MEMORY
    # --------------------------------------------------------

    result = {

        "pulse_ns": pulse_ns,

        "temperature_K": temperature_K,

        "current_mA": current_mA,

        "threshold": MZ_THRESHOLD,

        "runs": runs,

        "summary": summary,

    }

    all_results.append(
        result
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print(format_title("=" * 70))
print(format_title("FINAL SUMMARY".center(70)))
print(format_title("=" * 70))


for i, result in enumerate(
    all_results,
    start=1,
):

    summary = result["summary"]

    print(
        f"{i:>2}. "
        f"Pulse={result['pulse_ns']:.4f} ns | "
        f"T={result['temperature_K']} K | "
        f"I={result['current_mA']:.3f} mA | "
        f""
        f"Sw={summary['switched']} "
        f"({summary['p_switched']:.{PROBABILITY_DECIMALS}f}) | "
        f"NS={summary['not_switched']} "
        f"({summary['p_not_switched']:.{PROBABILITY_DECIMALS}f}) | "
        f"Inv={summary['invalid']} "
        f"({summary['p_invalid']:.{PROBABILITY_DECIMALS}f})"
    )


print()
print(
    "Analysis complete."
)


# ============================================================
# SAVING DISABLED FOR NOW
# ============================================================

# Nothing is saved to disk at this stage.
#
# Future output code will go here.
#
# Example:
#
# save_summary(...)
# save_cdf(...)
# save_switching_times(...)
# save_plots(...)
#
# All calculated results currently remain in:
#
#     all_results
#
# for use by the next analysis stage.