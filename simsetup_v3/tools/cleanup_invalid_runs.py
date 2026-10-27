#!/usr/bin/env python3
"""
cleanup_invalid_runs.py

Interactive cleanup of INVALID runs.

Workflow:
    1. Search results/tables for available parameter sets.
    2. Select one parameter set.
    3. Select ALL seeds or a custom seed range.
    4. Find INVALID runs from the selected seeds.
    5. Display seed, mz_final, and actual max runtime.
    6. Confirm cleanup.
    7. Delete corresponding table files.
    8. Rename corresponding plots using the actual max runtime.

Example:

    seed123_xxxxxxxx.json
        -> corresponding table is deleted

    plot:
        seed123_xxxxxxxx.png
        ->
        seed123_xxxxxxxx-max5ns.png

The max runtime is read from the run metadata rather than
being hard-coded.
"""

from pathlib import Path
import sys
import re
import json


# ============================================================================
# PROJECT PATH
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# IMPORTS
# ============================================================================

from modules.config import (
    MEASUREMENT_THRESHOLD,
    TABLES_DIR,
    PLOTS_DIR,
)

from modules.utils import (
    classify_state,
)


# ============================================================================
# SETTINGS
# ============================================================================

TABLE_EXT = ".txt"

PLOT_EXTENSIONS = [
    ".png",
    ".pdf",
]


# ============================================================================
# RESOLVE CONFIG PATHS
# ============================================================================

TABLES_DIR = Path(TABLES_DIR)

if not TABLES_DIR.is_absolute():
    TABLES_DIR = PROJECT_ROOT / TABLES_DIR


PLOTS_DIR = Path(PLOTS_DIR)

if not PLOTS_DIR.is_absolute():
    PLOTS_DIR = PROJECT_ROOT / PLOTS_DIR


# ============================================================================
# CONFIG CONFIRMATION
# ============================================================================

def print_config_confirmation():

    print()
    print("=" * 70)
    print("IMPORTED CONFIGURATION")
    print("=" * 70)

    config_items = [
        (
            "MEASUREMENT_THRESHOLD",
            MEASUREMENT_THRESHOLD,
        ),
        (
            "TABLES_DIR",
            TABLES_DIR,
        ),
        (
            "PLOTS_DIR",
            PLOTS_DIR,
        ),
    ]

    for name, value in config_items:

        print(
            f"{name:<25}: {value}"
        )

    print("=" * 70)
    print()


# ============================================================================
# PARAMETER SET DISCOVERY
# ============================================================================

def find_parameter_sets():

    if not TABLES_DIR.exists():

        print(
            "ERROR: Tables directory does not exist:"
        )

        print(
            f"      {TABLES_DIR}"
        )

        return []

    parameter_sets = []

    for folder in sorted(
        TABLES_DIR.iterdir()
    ):

        if not folder.is_dir():
            continue

        # Expected folder format:
        #
        # 0.2088ns_300K_-0.100mA

        match = re.fullmatch(
            r"([+-]?\d+(?:\.\d+)?)ns_"
            r"(\d+)K_"
            r"([+-]?\d+(?:\.\d+)?)mA",
            folder.name,
        )

        if match is None:
            continue

        pulse_ns = float(
            match.group(1)
        )

        temperature_K = int(
            match.group(2)
        )

        current_mA = float(
            match.group(3)
        )

        # Metadata uses the same parameter folder name.
        metadata_folder = (
            PROJECT_ROOT
            / "results"
            / "metadata"
            / folder.name
        )

        seed_files = get_all_seed_files(
            folder
        )

        metadata_files = (
            get_all_metadata_files(
                metadata_folder
            )
        )

        if (
            len(seed_files) == 0
            and len(metadata_files) == 0
        ):
            continue

        parameter_sets.append(
            {
                "folder": folder,
                "metadata_folder": metadata_folder,
                "pulse_ns": pulse_ns,
                "temperature_K": temperature_K,
                "current_mA": current_mA,
                "seed_files": seed_files,
                "metadata_files": metadata_files,
            }
        )

    return parameter_sets


# ============================================================================
# SEED FILE DISCOVERY
# ============================================================================

def get_all_seed_files(
    tables_folder
):

    tables_folder = Path(
        tables_folder
    )

    files = []

    if not tables_folder.exists():
        return files

    for table_file in tables_folder.iterdir():

        if not table_file.is_file():
            continue

        match = re.search(
            r"seed(\d+)",
            table_file.name,
        )

        if match is None:
            continue

        seed = int(
            match.group(1)
        )

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


# ============================================================================
# METADATA FILE DISCOVERY
# ============================================================================

def get_all_metadata_files(
    metadata_folder
):

    metadata_folder = Path(
        metadata_folder
    )

    files = []

    if not metadata_folder.exists():
        return files

    for metadata_file in metadata_folder.glob(
        "*.json"
    ):

        match = re.search(
            r"seed(\d+)",
            metadata_file.name,
        )

        if match is None:
            continue

        seed = int(
            match.group(1)
        )

        files.append(
            {
                "seed": seed,
                "file": metadata_file,
            }
        )

    return sorted(
        files,
        key=lambda x: x["seed"],
    )


# ============================================================================
# DISPLAY PARAMETER SETS
# ============================================================================

def print_parameter_sets(
    parameter_sets
):

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

    for i, parameter_set in enumerate(
        parameter_sets,
        start=1,
    ):

        seed_numbers = set()

        # --------------------------------------------------------------
        # Seeds from tables
        # --------------------------------------------------------------

        for table_file in parameter_set[
            "folder"
        ].iterdir():

            if not table_file.is_file():
                continue

            match = re.search(
                r"seed(\d+)",
                table_file.name,
            )

            if match:

                seed_numbers.add(
                    int(match.group(1))
                )

        # --------------------------------------------------------------
        # Seeds from metadata
        # --------------------------------------------------------------

        metadata_folder = (
            parameter_set[
                "metadata_folder"
            ]
        )

        if metadata_folder.exists():

            for metadata_file in (
                metadata_folder.glob(
                    "*.json"
                )
            ):

                match = re.search(
                    r"seed(\d+)",
                    metadata_file.name,
                )

                if match:

                    seed_numbers.add(
                        int(match.group(1))
                    )

        print(
            f"{i:>4} "
            f"{parameter_set['pulse_ns']:>12.4f} "
            f"{parameter_set['temperature_K']:>10} "
            f"{parameter_set['current_mA']:>15.3f} "
            f"{len(seed_numbers):>10}"
        )

    print("=" * 70)
    print()


# ============================================================================
# CHOOSE PARAMETER SET
# ============================================================================

def choose_parameter_set(
    parameter_sets
):

    while True:

        try:

            choice = input(
                f"Choose parameter set "
                f"[1-{len(parameter_sets)}]: "
            ).strip()

            index = int(
                choice
            ) - 1

            if (
                0 <= index
                < len(parameter_sets)
            ):

                return parameter_sets[
                    index
                ]

        except ValueError:
            pass

        print(
            "Invalid selection. "
            "Please enter a valid number."
        )


# ============================================================================
# CHOOSE SEED RANGE
# ============================================================================

def choose_seed_range(
    parameter_set
):

    seed_numbers = set()

    # ------------------------------------------------------------------
    # Get seeds from tables
    # ------------------------------------------------------------------

    tables_folder = parameter_set[
        "folder"
    ]

    if tables_folder.exists():

        for table_file in (
            tables_folder.iterdir()
        ):

            if not table_file.is_file():
                continue

            match = re.search(
                r"seed(\d+)",
                table_file.name,
            )

            if match:

                seed_numbers.add(
                    int(match.group(1))
                )

    # ------------------------------------------------------------------
    # Get seeds from metadata
    # ------------------------------------------------------------------

    metadata_folder = (
        parameter_set[
            "metadata_folder"
        ]
    )

    if metadata_folder.exists():

        for metadata_file in (
            metadata_folder.glob(
                "*.json"
            )
        ):

            match = re.search(
                r"seed(\d+)",
                metadata_file.name,
            )

            if match:

                seed_numbers.add(
                    int(match.group(1))
                )

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------

    if len(seed_numbers) == 0:

        print(
            "No seed files found for "
            "this parameter set."
        )

        return []

    available_seeds = sorted(
        seed_numbers
    )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    print()
    print("=" * 70)
    print("AVAILABLE SEEDS")
    print("=" * 70)

    print(
        f"Available seeds: "
        f"{available_seeds[0]} -> "
        f"{available_seeds[-1]}"
    )

    print(
        f"Number available: "
        f"{len(available_seeds)}"
    )

    print()
    print(
        "1. All available seeds"
    )

    print(
        "2. Custom seed range"
    )

    print()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    while True:

        choice = input(
            "Choose seed selection [1/2]: "
        ).strip()

        # --------------------------------------------------------------
        # ALL
        # --------------------------------------------------------------

        if choice == "1":

            return available_seeds

        # --------------------------------------------------------------
        # CUSTOM RANGE
        # --------------------------------------------------------------

        if choice == "2":

            while True:

                try:

                    start_seed = int(
                        input(
                            "Start seed: "
                        ).strip()
                    )

                    end_seed = int(
                        input(
                            "End seed: "
                        ).strip()
                    )

                    if start_seed > end_seed:

                        print(
                            "Start seed must be "
                            "<= end seed."
                        )

                        continue

                    selected = [
                        seed
                        for seed in available_seeds
                        if (
                            start_seed
                            <= seed
                            <= end_seed
                        )
                    ]

                    if len(selected) == 0:

                        print(
                            "No available seeds "
                            "exist inside that range."
                        )

                        continue

                    print()

                    print(
                        f"Selected "
                        f"{len(selected)} "
                        f"available seeds."
                    )

                    print(
                        f"Requested range: "
                        f"{start_seed} -> "
                        f"{end_seed}"
                    )

                    return selected

                except ValueError:

                    print(
                        "Please enter integer "
                        "seed numbers."
                    )

        else:

            print(
                "Please enter 1 or 2."
            )


# ============================================================================
# EXTRACT MAX RUNTIME
# ============================================================================

def get_max_runtime_ns(
    metadata
):

    # Preferred/current metadata field.
    max_runtime = metadata.get(
        "max_sim_time_ns"
    )

    # Compatibility with possible
    # older metadata naming.
    if max_runtime is None:

        max_runtime = metadata.get(
            "max_runtime_ns"
        )

    if max_runtime is None:

        return None

    try:

        return float(
            max_runtime
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================================
# FORMAT MAX RUNTIME
# ============================================================================

def format_max_runtime(
    max_runtime_ns
):

    if max_runtime_ns is None:
        return "unknown"

    value = float(
        max_runtime_ns
    )

    if value.is_integer():

        return f"{int(value)}ns"

    return f"{value:g}ns"


# ============================================================================
# FIND INVALID RUNS
# ============================================================================

def find_invalid_runs(
    parameter_set,
    selected_seeds,
):

    metadata_folder = (
        parameter_set[
            "metadata_folder"
        ]
    )

    invalid_runs = []

    if not metadata_folder.exists():

        print()
        print(
            "WARNING: Metadata directory "
            "does not exist:"
        )

        print(
            f"        {metadata_folder}"
        )

        return invalid_runs

    selected_seed_set = set(
        selected_seeds
    )

    for metadata_file in sorted(
        metadata_folder.glob(
            "*.json"
        )
    ):

        # --------------------------------------------------------------
        # Extract seed
        # --------------------------------------------------------------

        match = re.search(
            r"seed(\d+)",
            metadata_file.name,
        )

        if match is None:
            continue

        seed = int(
            match.group(1)
        )

        if seed not in selected_seed_set:
            continue

        # --------------------------------------------------------------
        # Read metadata
        # --------------------------------------------------------------

        try:

            with open(
                metadata_file,
                "r",
            ) as f:

                meta = json.load(f)

        except Exception as e:

            print(
                f"Skipping "
                f"{metadata_file}: {e}"
            )

            continue

        # --------------------------------------------------------------
        # Final mz
        # --------------------------------------------------------------

        mz = meta.get(
            "mz_final"
        )

        if mz is None:

            print(
                f"Skipping "
                f"{metadata_file.name}: "
                f"no mz_final"
            )

            continue

        # --------------------------------------------------------------
        # Classify
        # --------------------------------------------------------------

        state = classify_state(
            mz,
            MEASUREMENT_THRESHOLD,
        )

        if state != "INVALID":
            continue

        # --------------------------------------------------------------
        # Max runtime
        # --------------------------------------------------------------

        max_runtime_ns = (
            get_max_runtime_ns(
                meta
            )
        )

        # --------------------------------------------------------------
        # Save invalid run
        # --------------------------------------------------------------

        invalid_runs.append(
            {
                "seed": seed,
                "metadata": metadata_file,
                "mz_final": mz,
                "max_runtime_ns": max_runtime_ns,
                "stem": metadata_file.stem,
            }
        )

    return sorted(
        invalid_runs,
        key=lambda x: x["seed"],
    )


# ============================================================================
# DISPLAY INVALID RUNS
# ============================================================================

def print_invalid_runs(
    invalid_runs,
    selected_seeds,
):

    print()
    print("=" * 70)
    print("INVALID RUNS FOUND")
    print("=" * 70)

    if len(invalid_runs) == 0:

        print(
            "No INVALID runs found "
            "in the selected seed range."
        )

        print("=" * 70)

        return

    print(
        f"Selected seeds : "
        f"{selected_seeds[0]} -> "
        f"{selected_seeds[-1]}"
    )

    print(
        f"Invalid runs   : "
        f"{len(invalid_runs)}"
    )

    print()

    print(
        f"{'Seed':>8} "
        f"{'mz_final':>12} "
        f"{'Max runtime':>15} "
        f"{'Metadata':>40}"
    )

    print("-" * 85)

    for run in invalid_runs:

        max_runtime_str = (
            format_max_runtime(
                run["max_runtime_ns"]
            )
        )

        print(
            f"{run['seed']:>8} "
            f"{run['mz_final']:>12.6f} "
            f"{max_runtime_str:>15} "
            f"{run['metadata'].name:>40}"
        )

    print("=" * 70)


# ============================================================================
# CONFIRM CLEANUP
# ============================================================================

def confirm_cleanup(
    parameter_set,
    selected_seeds,
    invalid_runs,
):

    print()
    print("=" * 70)
    print("CLEANUP CONFIRMATION")
    print("=" * 70)

    print(
        f"Parameter set : "
        f"{parameter_set['pulse_ns']:.4f} ns | "
        f"{parameter_set['temperature_K']} K | "
        f"{parameter_set['current_mA']:.3f} mA"
    )

    print(
        f"Seed range    : "
        f"{selected_seeds[0]} -> "
        f"{selected_seeds[-1]}"
    )

    print(
        f"Invalid runs  : "
        f"{len(invalid_runs)}"
    )

    print()
    print(
        "This will DELETE the corresponding "
        "table files."
    )

    print(
        "Existing plots will be renamed using "
        "their actual max runtime."
    )

    print()

    while True:

        choice = input(
            "Proceed with cleanup? [Y/N]: "
        ).strip().upper()

        if choice == "Y":

            return True

        if choice == "N":

            return False

        print(
            "Please enter Y or N."
        )


# ============================================================================
# CLEANUP
# ============================================================================

def cleanup_invalid_runs(
    parameter_set,
    invalid_runs,
):

    tables_dir = parameter_set[
        "folder"
    ]

    plots_dir = (
        PLOTS_DIR
        / parameter_set["folder"].name
    )

    deleted_tables = 0
    renamed_plots = 0

    # ------------------------------------------------------------------
    # Process each invalid run
    # ------------------------------------------------------------------

    for run in invalid_runs:

        stem = run["stem"]

        # ==============================================================
        # DELETE TABLE
        # ==============================================================

        table_file = (
            tables_dir
            / f"{stem}{TABLE_EXT}"
        )

        if table_file.exists():

            table_file.unlink()

            deleted_tables += 1

            print(
                f"Deleted table : "
                f"{table_file}"
            )

        else:

            print(
                f"Table missing : "
                f"{table_file}"
            )

        # ==============================================================
        # RENAME PLOTS
        # ==============================================================

        max_runtime_ns = (
            run["max_runtime_ns"]
        )

        if max_runtime_ns is None:

            print(
                f"Plot not renamed : "
                f"{run['metadata'].name} "
                f"(max runtime not found)"
            )

            continue

        max_runtime_str = (
            format_max_runtime(
                max_runtime_ns
            )
        )

        for ext in PLOT_EXTENSIONS:

            plot_file = (
                plots_dir
                / f"{stem}{ext}"
            )

            if not plot_file.exists():
                continue

            renamed = plot_file.with_name(
                f"{plot_file.stem}"
                f"-max{max_runtime_str}"
                f"{plot_file.suffix}"
            )

            # ----------------------------------------------------------
            # Avoid overwriting an existing renamed plot
            # ----------------------------------------------------------

            if renamed.exists():

                print(
                    f"Plot already renamed: "
                    f"{renamed.name}"
                )

                continue

            plot_file.rename(
                renamed
            )

            renamed_plots += 1

            print(
                f"Renamed plot  : "
                f"{plot_file.name} -> "
                f"{renamed.name}"
            )

    return (
        deleted_tables,
        renamed_plots,
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    # ==================================================================
    # CONFIG
    # ==================================================================

    print_config_confirmation()

    # ==================================================================
    # FIND PARAMETER SETS
    # ==================================================================

    print(
        "Searching for available parameter sets..."
    )

    parameter_sets = find_parameter_sets()

    if len(parameter_sets) == 0:

        print()
        print(
            "No parameter sets with data "
            "were found."
        )

        print(
            f"Searched: {TABLES_DIR}"
        )

        return

    print(
        f"Found {len(parameter_sets)} "
        f"parameter sets."
    )

    # ==================================================================
    # PARAMETER SELECTION
    # ==================================================================

    print_parameter_sets(
        parameter_sets
    )

    selected = choose_parameter_set(
        parameter_sets
    )

    # ==================================================================
    # PARAMETER SUMMARY
    # ==================================================================

    print()
    print("=" * 70)
    print("SELECTED PARAMETER SET")
    print("=" * 70)

    print(
        f"Pulse       : "
        f"{selected['pulse_ns']:.4f} ns"
    )

    print(
        f"Temperature : "
        f"{selected['temperature_K']} K"
    )

    print(
        f"Current     : "
        f"{selected['current_mA']:.3f} mA"
    )

    print(
        f"Tables      : "
        f"{selected['folder']}"
    )

    print(
        f"Metadata    : "
        f"{selected['metadata_folder']}"
    )

    print("=" * 70)

    # ==================================================================
    # SEED SELECTION
    # ==================================================================

    selected_seeds = choose_seed_range(
        selected
    )

    if len(selected_seeds) == 0:

        return

    # ==================================================================
    # FIND INVALID RUNS
    # ==================================================================

    print()
    print(
        "Searching for INVALID runs..."
    )

    invalid_runs = find_invalid_runs(
        selected,
        selected_seeds,
    )

    # ==================================================================
    # DISPLAY INVALID RUNS
    # ==================================================================

    print_invalid_runs(
        invalid_runs,
        selected_seeds,
    )

    if len(invalid_runs) == 0:

        return

    # ==================================================================
    # CONFIRM
    # ==================================================================

    confirmed = confirm_cleanup(
        selected,
        selected_seeds,
        invalid_runs,
    )

    if not confirmed:

        print()
        print(
            "Cleanup cancelled. "
            "No files were modified."
        )

        return

    # ==================================================================
    # CLEAN
    # ==================================================================

    print()
    print(
        "Starting cleanup..."
    )

    print()

    (
        deleted_tables,
        renamed_plots,
    ) = cleanup_invalid_runs(
        selected,
        invalid_runs,
    )

    # ==================================================================
    # SUMMARY
    # ==================================================================

    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)

    print(
        f"Parameter set    : "
        f"{selected['pulse_ns']:.4f} ns | "
        f"{selected['temperature_K']} K | "
        f"{selected['current_mA']:.3f} mA"
    )

    print(
        f"Seed range       : "
        f"{selected_seeds[0]} -> "
        f"{selected_seeds[-1]}"
    )

    print(
        f"Invalid runs     : "
        f"{len(invalid_runs)}"
    )

    print(
        f"Tables deleted   : "
        f"{deleted_tables}"
    )

    print(
        f"Plots renamed    : "
        f"{renamed_plots}"
    )

    print("=" * 70)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    main()