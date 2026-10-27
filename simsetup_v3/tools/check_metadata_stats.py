#!/usr/bin/env python3

from pathlib import Path
import sys
import re
import json


# ============================================================================
# PROJECT ROOT
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# CONFIG
# ============================================================================

from modules.config import (
    MEASUREMENT_THRESHOLD,
    TABLES_DIR,
    PLOTS_DIR,
)


# ============================================================================
# RESOLVE PATHS
# ============================================================================

TABLES_DIR = Path(TABLES_DIR)

if not TABLES_DIR.is_absolute():
    TABLES_DIR = PROJECT_ROOT / TABLES_DIR

PLOTS_DIR = Path(PLOTS_DIR)

if not PLOTS_DIR.is_absolute():
    PLOTS_DIR = PROJECT_ROOT / PLOTS_DIR


# Metadata is stored here
METADATA_DIR = PROJECT_ROOT / "results" / "metadata"


# ============================================================================
# CONFIG CONFIRMATION
# ============================================================================

def print_config_confirmation():

    print()
    print("=" * 70)
    print("IMPORTED CONFIGURATION")
    print("=" * 70)

    print(
        f"{'MEASUREMENT_THRESHOLD':<25}: "
        f"{MEASUREMENT_THRESHOLD}"
    )

    print(
        f"{'METADATA_DIR':<25}: "
        f"{METADATA_DIR}"
    )

    print("=" * 70)
    print()


# ============================================================================
# FIND PARAMETER SETS
# ============================================================================

def find_parameter_sets():

    if not METADATA_DIR.exists():

        print(
            "ERROR: Metadata directory does not exist:"
        )

        print(
            f"      {METADATA_DIR}"
        )

        return []

    parameter_sets = []

    for folder in sorted(
        METADATA_DIR.iterdir()
    ):

        if not folder.is_dir():
            continue

        # Expected:
        # 0.2088ns_298K_-0.100mA

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

        metadata_files = list(
            folder.glob("*.json")
        )

        if len(metadata_files) == 0:
            continue

        parameter_sets.append(
            {
                "folder": folder,
                "pulse_ns": pulse_ns,
                "temperature_K": temperature_K,
                "current_mA": current_mA,
                "metadata_files": metadata_files,
            }
        )

    return parameter_sets


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
        f"{'Metadata':>10}"
    )

    print("-" * 70)

    for i, parameter_set in enumerate(
        parameter_sets,
        start=1,
    ):

        print(
            f"{i:>4} "
            f"{parameter_set['pulse_ns']:>12.4f} "
            f"{parameter_set['temperature_K']:>10} "
            f"{parameter_set['current_mA']:>15.3f} "
            f"{len(parameter_set['metadata_files']):>10}"
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

            index = int(choice) - 1

            if (
                0 <= index
                < len(parameter_sets)
            ):

                return parameter_sets[index]

        except ValueError:
            pass

        print(
            "Invalid selection. "
            "Please enter a valid number."
        )


# ============================================================================
# GET AVAILABLE SEEDS FROM METADATA
# ============================================================================

def get_available_seeds(
    parameter_set
):

    seed_numbers = set()

    for metadata_file in parameter_set[
        "metadata_files"
    ]:

        match = re.search(
            r"seed(\d+)",
            metadata_file.name,
        )

        if match:

            seed_numbers.add(
                int(match.group(1))
            )

    return sorted(
        seed_numbers
    )


# ============================================================================
# CHOOSE SEED RANGE
# ============================================================================

def choose_seed_range(
    parameter_set
):

    available_seeds = get_available_seeds(
        parameter_set
    )

    if len(available_seeds) == 0:

        print(
            "No metadata seed files found."
        )

        return []

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
    print("1. All available seeds")
    print("2. Custom seed range")
    print()

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
        # CUSTOM
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
                            "No metadata seeds "
                            "exist in that range."
                        )

                        continue

                    print()
                    print(
                        f"Selected "
                        f"{len(selected)} "
                        f"metadata seeds."
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
# CALCULATE METADATA STATISTICS
# ============================================================================

def calculate_metadata_stats(
    parameter_set,
    selected_seeds,
):

    selected_seed_set = set(
        selected_seeds
    )

    switched = 0
    not_switched = 0
    invalid = 0

    missing_state = 0
    unreadable = 0

    processed = 0

    metadata_files = parameter_set[
        "metadata_files"
    ]

    for metadata_file in metadata_files:

        # --------------------------------------------------------------
        # Seed
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

                metadata = json.load(f)

        except Exception:

            unreadable += 1

            continue

        processed += 1

        # --------------------------------------------------------------
        # State
        # --------------------------------------------------------------

        state = metadata.get(
            "state"
        )

        if state == "SWITCHED":

            switched += 1

        elif state == "NOT_SWITCHED":

            not_switched += 1

        elif state == "INVALID":

            invalid += 1

        else:

            missing_state += 1

    return {
        "switched": switched,
        "not_switched": not_switched,
        "invalid": invalid,
        "processed": processed,
        "missing_state": missing_state,
        "unreadable": unreadable,
    }


# ============================================================================
# PRINT RESULTS
# ============================================================================

def print_results(
    parameter_set,
    selected_seeds,
    stats,
):

    switched = stats["switched"]
    not_switched = stats["not_switched"]
    invalid = stats["invalid"]

    processed = stats["processed"]
    missing_state = stats["missing_state"]
    unreadable = stats["unreadable"]

    total_classified = (
        switched
        + not_switched
        + invalid
    )

    # --------------------------------------------------------------
    # Probabilities
    # --------------------------------------------------------------

    if total_classified > 0:

        psw = (
            switched
            / total_classified
        )

        pnot = (
            not_switched
            / total_classified
        )

        pinvalid = (
            invalid
            / total_classified
        )

    else:

        psw = 0.0
        pnot = 0.0
        pinvalid = 0.0

    # --------------------------------------------------------------
    # Output
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("METADATA STATISTICS")
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

    print()

    print(
        f"{'Quantity':<25}"
        f"{'Count':>12}"
        f"{'Probability':>18}"
    )

    print("-" * 55)

    print(
        f"{'Switched':<25}"
        f"{switched:>12}"
        f"{100 * psw:>17.3f}%"
    )

    print(
        f"{'Not switched':<25}"
        f"{not_switched:>12}"
        f"{100 * pnot:>17.3f}%"
    )

    print(
        f"{'Invalid':<25}"
        f"{invalid:>12}"
        f"{100 * pinvalid:>17.3f}%"
    )

    print("-" * 55)

    print(
        f"{'Total classified':<25}"
        f"{total_classified:>12}"
        f"{100.0:>17.3f}%"
    )

    print()

    print(
        f"Metadata files processed : "
        f"{processed}"
    )

    if missing_state > 0:

        print(
            f"Missing/unknown state    : "
            f"{missing_state}"
        )

    if unreadable > 0:

        print(
            f"Unreadable metadata      : "
            f"{unreadable}"
        )

    print("=" * 70)


# ============================================================================
# MAIN
# ============================================================================

def main():

    # ------------------------------------------------------------------
    # CONFIG
    # ------------------------------------------------------------------

    print_config_confirmation()

    # ------------------------------------------------------------------
    # PARAMETER SETS
    # ------------------------------------------------------------------

    print(
        "Searching metadata for available "
        "parameter sets..."
    )

    parameter_sets = find_parameter_sets()

    if len(parameter_sets) == 0:

        print(
            "No parameter sets found."
        )

        return

    print(
        f"Found {len(parameter_sets)} "
        f"parameter sets."
    )

    # ------------------------------------------------------------------
    # SELECT PARAMETER SET
    # ------------------------------------------------------------------

    print_parameter_sets(
        parameter_sets
    )

    selected = choose_parameter_set(
        parameter_sets
    )

    # ------------------------------------------------------------------
    # DISPLAY SELECTION
    # ------------------------------------------------------------------

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
        f"Metadata    : "
        f"{selected['folder']}"
    )

    print("=" * 70)

    # ------------------------------------------------------------------
    # SELECT SEEDS
    # ------------------------------------------------------------------

    selected_seeds = choose_seed_range(
        selected
    )

    if len(selected_seeds) == 0:

        return

    # ------------------------------------------------------------------
    # CALCULATE
    # ------------------------------------------------------------------

    print()
    print(
        "Reading metadata and calculating statistics..."
    )

    stats = calculate_metadata_stats(
        selected,
        selected_seeds,
    )

    # ------------------------------------------------------------------
    # PRINT
    # ------------------------------------------------------------------

    print_results(
        selected,
        selected_seeds,
        stats,
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    main()
