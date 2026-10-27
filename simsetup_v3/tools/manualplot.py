# modules/manualplot.py
#
# Manual overlay plot generator.
#
# Searches results/tables for available parameter sets, lets the user
# select one, then lets the user choose:
#   - ALL available seeds
#   - CUSTOM seed range
#
# Output:
#   results/plots/<parameter_folder>/
#       manualplot_<N>_<protocol>_<pulse>ns_<temp>K_<current>mA.png
#
# N = number of selected iterations/seeds
#
# The plotting format intentionally matches autoplot.py.

from pathlib import Path
import sys
import glob
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from modules.config import *

# Resolve config paths relative to the project root,
# not relative to the directory from which this script is launched.

TABLES_DIR = Path(TABLES_DIR)

if not TABLES_DIR.is_absolute():
    TABLES_DIR = PROJECT_ROOT / TABLES_DIR

PLOTS_DIR = Path(PLOTS_DIR)

if not PLOTS_DIR.is_absolute():
    PLOTS_DIR = PROJECT_ROOT / PLOTS_DIR


##############################################################################
# CONFIG IMPORT CONFIRMATION
##############################################################################

def print_config_confirmation():

    print()
    print("=" * 70)
    print("IMPORTED CONFIGURATION")
    print("=" * 70)

    config_items = [
        ("MACHINE", MACHINE),
        ("MACHINE_ID", MACHINE_ID),
        ("SIM_PROTOCOL", SIM_PROTOCOL),
        ("MEASUREMENT_THRESHOLD", MEASUREMENT_THRESHOLD),
        ("SEED_SHIFT", SEED_SHIFT),
        ("TABLES_DIR", TABLES_DIR),
        ("PLOTS_DIR", PLOTS_DIR),
    ]

    for name, value in config_items:
        print(f"{name:<25}: {value}")

    print("=" * 70)
    print()


##############################################################################
# PARAMETER SET DISCOVERY
##############################################################################

def find_parameter_sets(tables_dir):

    tables_dir = Path(tables_dir)

    if not tables_dir.exists():
        print(f"ERROR: Tables directory does not exist:")
        print(f"      {tables_dir}")
        return []

    parameter_sets = []

    for folder in sorted(tables_dir.iterdir()):

        if not folder.is_dir():
            continue

        # Expected:
        # 0.2075ns_300K_-0.100mA
        match = re.fullmatch(
            r"([+-]?\d+(?:\.\d+)?)ns_"
            r"(\d+)K_"
            r"([+-]?\d+(?:\.\d+)?)mA",
            folder.name,
        )

        if match is None:
            continue

        pulse_ns = float(match.group(1))
        temperature_K = int(match.group(2))
        current_mA = float(match.group(3))

        seed_files = get_all_seed_files(folder)

        if len(seed_files) == 0:
            continue

        parameter_sets.append(
            {
                "folder": folder,
                "pulse_ns": pulse_ns,
                "temperature_K": temperature_K,
                "current_mA": current_mA,
                "seed_files": seed_files,
            }
        )

    return parameter_sets


##############################################################################
# SEED FILE DISCOVERY
##############################################################################

def get_all_seed_files(tables_folder):

    tables_folder = Path(tables_folder)

    files = []

    for table_file in sorted(tables_folder.iterdir()):

        if not table_file.is_file():
            continue

        match = re.search(
            r"seed(\d+)",
            table_file.name,
        )

        if match is None:
            continue

        seed = int(match.group(1))

        files.append(
            {
                "seed": seed,
                "file": table_file,
            }
        )

    return sorted(
        files,
        key=lambda x: x["seed"],
    )


##############################################################################
# DISPLAY PARAMETER SETS
##############################################################################

def print_parameter_sets(parameter_sets):

    print()
    print("=" * 70)
    print("AVAILABLE PARAMETER SETS")
    print("=" * 70)

    print(
        f"{'#':>4} "
        f"{'Pulse (ns)':>12} "
        f"{'Temp (K)':>10} "
        f"{'Current (mA)':>15} "
        f"{'Seeds':>10}"
    )

    print("-" * 70)

    for i, p in enumerate(parameter_sets, start=1):

        seeds = [
            item["seed"]
            for item in p["seed_files"]
        ]

        print(
            f"{i:>4} "
            f"{p['pulse_ns']:>12.4f} "
            f"{p['temperature_K']:>10} "
            f"{p['current_mA']:>15.3f} "
            f"{len(seeds):>10}"
        )

    print("=" * 70)
    print()


##############################################################################
# USER SELECTION
##############################################################################

def choose_parameter_set(parameter_sets):

    while True:

        try:

            choice = input(
                f"Choose parameter set [1-{len(parameter_sets)}]: "
            ).strip()

            index = int(choice) - 1

            if 0 <= index < len(parameter_sets):
                return parameter_sets[index]

        except ValueError:
            pass

        print("Invalid selection. Please enter a valid number.")


##############################################################################
# SEED SELECTION
##############################################################################

def choose_seed_files(seed_files):

    available_seeds = [
        item["seed"]
        for item in seed_files
    ]

    print()
    print("=" * 70)
    print("AVAILABLE SEEDS")
    print("=" * 70)

    print(
        f"Available seeds: "
        f"{min(available_seeds)} -> {max(available_seeds)}"
    )

    print(
        f"Number available: "
        f"{len(available_seeds)}"
    )

    print()
    print("1. All available seeds")
    print("2. Custom seed range")
    print()

    while True:

        choice = input(
            "Choose seed selection [1/2]: "
        ).strip()

        if choice == "1":

            return seed_files

        if choice == "2":

            while True:

                try:

                    start_seed = int(
                        input("Start seed: ").strip()
                    )

                    end_seed = int(
                        input("End seed: ").strip()
                    )

                    if start_seed > end_seed:
                        print(
                            "Start seed must be <= end seed."
                        )
                        continue

                    selected = [
                        item
                        for item in seed_files
                        if start_seed <= item["seed"] <= end_seed
                    ]

                    if len(selected) == 0:

                        print(
                            "No available seed files exist "
                            "inside that range."
                        )
                        continue

                    print()
                    print(
                        f"Selected {len(selected)} available seeds."
                    )
                    print(
                        f"Requested range: "
                        f"{start_seed} -> {end_seed}"
                    )

                    return selected

                except ValueError:

                    print(
                        "Please enter integer seed numbers."
                    )

        print("Please enter 1 or 2.")


##############################################################################
# STATISTICS TOGGLE
##############################################################################

def choose_stats():

    while True:

        choice = input(
            "Show statistics (Psw + table)? [Y/N]: "
        ).strip().upper()

        if choice == "Y":
            return True

        if choice == "N":
            return False

        print("Please enter Y or N.")


##############################################################################
# TABLE READER
##############################################################################

def read_mz_table(table_file):

    try:

        df = pd.read_csv(
            table_file,
            sep=r"\s+",
            comment="#",
            header=None,
        )

    except Exception as e:

        print(
            f"MANUALPLOT PARSE ERROR: "
            f"{table_file}"
        )
        print(e)

        return None, None

    if len(df) == 0:
        return None, None

    ncols = df.shape[1]

    if ncols == 7:

        df.columns = [
            "t",
            "mx1",
            "my1",
            "mz1",
            "mx2",
            "my2",
            "mz2",
        ]

        mz = df["mz2"]

    elif ncols == 4:

        df.columns = [
            "t",
            "mx",
            "my",
            "mz",
        ]

        mz = df["mz"]

    else:

        print(
            f"MANUALPLOT BAD TABLE: "
            f"{table_file} "
            f"({ncols} columns)"
        )

        return None, None

    return df, mz


##############################################################################
# CREATE MANUAL PLOT
##############################################################################

def create_manualplot(
    tables_folder,
    seed_files,
    output_png,
    pulse_ns,
    temperature_K,
    current_mA,
    pulse_start_ns,
    pulse_end_ns,
    threshold,
    show_stats=True,
    machine="DGX",
    protocol="v1",
):

    tables_folder = Path(tables_folder)

    print()
    print("========== MANUALPLOT ==========")
    print("tables_folder =", tables_folder)
    print("exists        =", tables_folder.exists())
    print("is_dir        =", tables_folder.is_dir())
    print("n_files       =", len(seed_files))

    if len(seed_files):
        print(
            "first file    =",
            seed_files[0]["file"],
        )

    print("================================")
    print()

    switched = 0
    unswitched = 0
    invalid = 0

    fig = plt.figure(
        figsize=(14, 10)
    )

    if show_stats:

        gs = GridSpec(
            2,
            1,
            height_ratios=[5, 2],
            hspace=0.25,
        )

        ax = fig.add_subplot(gs[0])

    else:

        # No statistics -> no second table axis.
        gs = GridSpec(
            1,
            1,
        )

        ax = fig.add_subplot(gs[0])

    ##########################################################################
    # PLOT SELECTED TABLES
    ##########################################################################

    plotted = 0
    invalid_details = []

    for item in seed_files:

        table_file = item["file"]

        df, mz = read_mz_table(
            table_file
        )

        if df is None:
            continue

        t_ns = df["t"] * 1e9

        final_mz = mz.iloc[-1]

        ######################################################################
        # CLASSIFY
        ######################################################################

        if final_mz < -threshold:

            linestyle = "-"
            switched += 1

        elif final_mz > threshold:

            linestyle = "--"
            unswitched += 1

        else:

            linestyle = ":"
            invalid += 1

            invalid_details.append(
                (
                    item["seed"],
                    final_mz,
                    t_ns.iloc[-1],
                )
            )

        ######################################################################
        # PLOT
        ######################################################################

        ax.plot(
            t_ns,
            mz,
            linestyle=linestyle,
            linewidth=0.8,
        )

        plotted += 1

    ##########################################################################
    # INVALID RUN DIAGNOSTIC
    ##########################################################################

    print()
    print("=" * 70)
    print("INVALID RUN DETAILS")
    print("=" * 70)

    if len(invalid_details) == 0:

        print("No invalid runs found.")

    else:

        print(
            f"{'Seed':>8} "
            f"{'Final mz':>12} "
            f"{'Final time (ns)':>18}"
        )

        print("-" * 70)

        for seed, final_mz, final_time in invalid_details:

            print(
                f"{seed:>8} "
                f"{final_mz:>12.6f} "
                f"{final_time:>18.6f}"
            )

        print()
        print(
            f"Total invalid: "
            f"{len(invalid_details)}"
        )

    print("=" * 70)

    ##########################################################################
    # STATISTICS
    ##########################################################################

    total = (
        switched
        + unswitched
        + invalid
    )

    if total > 0:

        psw = switched / total
        punsw = unswitched / total
        pinvalid = invalid / total

    else:

        psw = 0
        punsw = 0
        pinvalid = 0

    ##########################################################################
    # PULSE REGION
    ##########################################################################

    ax.axvspan(
        pulse_start_ns,
        pulse_end_ns,
        alpha=0.20,
    )

    ##########################################################################
    # THRESHOLDS
    ##########################################################################

    ax.axhline(
        threshold,
        linewidth=1,
    )

    ax.axhline(
        -threshold,
        linewidth=1,
    )

    ##########################################################################
    # AXES
    ##########################################################################

    ax.set_xlabel(
        "Time (ns)"
    )

    ax.set_ylabel(
        "m$_z$"
    )

    ax.set_ylim(
        [-1.1, 1.1]
    )

    ax.grid(True)

    ##########################################################################
    # TITLE
    ##########################################################################

    title = (
        f"MANUALPLOT | {machine} | "
        f"protocol={protocol}\n"
        f"solid=switched | "
        f"dashed=unswitched | "
        f"dotted=invalid\n"
        f"pulse={pulse_ns:.4f} ns    "
        f"T={temperature_K} K    "
        f"I={current_mA:.3f} mA\n"
        f"no. of seeds={len(seed_files)}"
    )

    if show_stats:

        title += (
            f"\n"
            f"Psw={100*psw:.3f}%"
        )

    ax.set_title(
        title
    )

    ##########################################################################
    # SUMMARY TABLE
    ##########################################################################

    if show_stats:

        ax2 = fig.add_subplot(
            gs[1]
        )

        ax2.axis("off")
        ax2.set_anchor("N")

        table_data = [

            [
                "Iterations",
                total
            ],

            [
                "Switched",
                switched
            ],

            [
                "Not switched",
                unswitched
            ],

            [
                "Invalid",
                invalid
            ],

            [
                "Psw",
                f"{100*psw:.3f}%"
            ],

            [
                "Pnot",
                f"{100*punsw:.3f}%"
            ],

            [
                "Pinvalid",
                f"{100*pinvalid:.3f}%"
            ],

            [
                "Threshold",
                threshold
            ],

            [
                "Machine",
                machine
            ],

            [
                "Protocol",
                protocol
            ],
        ]

        table = ax2.table(
            cellText=table_data,
            colLabels=[
                "Parameter",
                "Value",
            ],
            loc="center",
            cellLoc="center",
        )

        table.auto_set_font_size(
            False
        )

        table.set_fontsize(
            10
        )

        table.scale(
            1,
            1.5,
        )

        ######################################################################
        # BLACK HEADER
        ######################################################################

        for i in range(2):

            cell = table[(0, i)]

            cell.set_facecolor(
                "black"
            )

            cell.get_text().set_color(
                "white"
            )

    ##########################################################################
    # SAVE
    ##########################################################################

    output_png = Path(output_png)

    output_png.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.tight_layout()

    plt.savefig(
        output_png,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print()
    print(
        f'Plot generated: "{output_png}"'
    )

    print(
        f"Plotted tables: {plotted}"
    )

    print(
        f"Psw = {100*psw:.3f}%"
    )

    print(
        f"Pnot = {100*punsw:.3f}%"
    )

    print(
        f"Pinvalid = {100*pinvalid:.3f}%"
    )


##############################################################################
# MAIN
##############################################################################

def main():

    ##########################################################################
    # CONFIG CONFIRMATION
    ##########################################################################

    print_config_confirmation()

    ##########################################################################
    # FIND PARAMETER SETS
    ##########################################################################

    print(
        "Searching for available parameter sets..."
    )

    parameter_sets = find_parameter_sets(
        TABLES_DIR
    )

    if len(parameter_sets) == 0:

        print()
        print(
            "No parameter sets with seed data were found."
        )
        print(
            f"Searched: {TABLES_DIR}"
        )
        return

    print(
        f"Found {len(parameter_sets)} parameter sets."
    )

    ##########################################################################
    # PARAMETER SELECTION
    ##########################################################################

    print_parameter_sets(
        parameter_sets
    )

    selected = choose_parameter_set(
        parameter_sets
    )

    ##########################################################################
    # SELECTED PARAMETER SUMMARY
    ##########################################################################

    print()
    print("=" * 70)
    print("SELECTED PARAMETER SET")
    print("=" * 70)

    print(
        f"Pulse       : {selected['pulse_ns']:.4f} ns"
    )

    print(
        f"Temperature : {selected['temperature_K']} K"
    )

    print(
        f"Current     : {selected['current_mA']:.3f} mA"
    )

    print(
        f"Folder      : {selected['folder']}"
    )

    print(
        f"Available   : {len(selected['seed_files'])} seeds"
    )

    print("=" * 70)

    ##########################################################################
    # SEED SELECTION
    ##########################################################################

    selected_seed_files = choose_seed_files(
        selected["seed_files"]
    )

    if len(selected_seed_files) == 0:

        print(
            "No seeds selected."
        )
        return

    ##########################################################################
    # STATS TOGGLE
    ##########################################################################

    show_stats = choose_stats()

    ##########################################################################
    # OUTPUT
    ##########################################################################

    n_iterations = len(
        selected_seed_files
    )

    plots_folder = (
        Path(PLOTS_DIR)
        / selected["folder"].name
    )

    plot_base = (
        f"manualplot_"
        f"{n_iterations}_"
        f"{SIM_PROTOCOL}_"
        f"{selected['pulse_ns']:.4f}ns_"
        f"{selected['temperature_K']}K_"
        f"{selected['current_mA']:.3f}mA"
    )

    output_png = (
        plots_folder
        / f"{plot_base}.png"
    )

    ##########################################################################
    # FINAL SUMMARY BEFORE PLOTTING
    ##########################################################################

    print()
    print("=" * 70)
    print("MANUAL PLOT SETTINGS")
    print("=" * 70)

    print(
        f"Parameter set : "
        f"{selected['pulse_ns']:.4f} ns | "
        f"{selected['temperature_K']} K | "
        f"{selected['current_mA']:.3f} mA"
    )

    print(
        f"Seeds         : "
        f"{selected_seed_files[0]['seed']} -> "
        f"{selected_seed_files[-1]['seed']}"
    )

    print(
        f"Iterations    : {n_iterations}"
    )

    print(
        f"Statistics    : "
        f"{'ON' if show_stats else 'OFF'}"
    )

    print(
        f"Output        : {output_png}"
    )

    print("=" * 70)
    print()

    ##########################################################################
    # CREATE PLOT
    ##########################################################################

    create_manualplot(
        tables_folder=selected["folder"],

        seed_files=selected_seed_files,

        output_png=output_png,

        pulse_ns=selected["pulse_ns"],

        temperature_K=selected["temperature_K"],

        current_mA=selected["current_mA"],

        pulse_start_ns=1.0,

        pulse_end_ns=1.0 + selected["pulse_ns"],

        threshold=MEASUREMENT_THRESHOLD,

        show_stats=show_stats,

        machine=MACHINE,

        protocol=SIM_PROTOCOL,
    )


##############################################################################
# ENTRY POINT
##############################################################################

if __name__ == "__main__":
    main()