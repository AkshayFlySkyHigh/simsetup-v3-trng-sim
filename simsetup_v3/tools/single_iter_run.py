#!/usr/bin/env python3

import sys
import os
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

# This file is:
#
#   ~/simsetup_v3/tools/single_iter_run.py
#
# Project root:
#
#   ~/simsetup_v3/

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Make project root available to Python BEFORE importing
# anything from modules.
sys.path.insert(0, str(PROJECT_ROOT))

# Your config.py and iter_run.py use relative paths.
# Always run from the project root.
os.chdir(PROJECT_ROOT)


# ============================================================
# IMPORT EXISTING SIMULATION CODE
# ============================================================

from modules.iter_run import run_iteration
from modules.config import (
    MUMAX_EXE,
    TEMPLATE_FILE,
    MEASUREMENT_THRESHOLD,
)


# ============================================================
# INPUT FUNCTIONS
# ============================================================

def get_float(prompt):

    while True:

        try:
            return float(input(prompt))

        except ValueError:
            print("Please enter a valid number.")


def get_int(prompt):

    while True:

        try:
            return int(input(prompt))

        except ValueError:
            print("Please enter a valid integer.")


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("SINGLE MuMax3 ITERATION")
    print("=" * 60)

    # --------------------------------------------------------
    # INPUTS
    # --------------------------------------------------------

    current_mA = get_float(
        "Current (mA): "
    )

    pulse_ns = get_float(
        "Pulse width (ns): "
    )

    temperature_K = get_float(
        "Temperature (K): "
    )

    seed = get_int(
        "Seed: "
    )

    # Convert mA -> A
    current_A = current_mA / 1000.0

    # --------------------------------------------------------
    # DISPLAY PARAMETERS
    # --------------------------------------------------------

    print()
    print("Simulation parameters")
    print("-" * 60)

    print(
        f"Current:          "
        f"{current_mA:.4f} mA"
    )

    print(
        f"Pulse width:      "
        f"{pulse_ns:.4f} ns"
    )

    print(
        f"Temperature:      "
        f"{temperature_K:g} K"
    )

    print(
        f"Seed:              "
        f"{seed}"
    )

    print(
        f"GPU:               "
        f"0"
    )

    print(
        f"MuMax3:            "
        f"{MUMAX_EXE}"
    )

    print(
        f"Template:          "
        f"{TEMPLATE_FILE}"
    )

    print(
        f"OVF interval:      "
        f"0.0500 ns"
    )

    enable_ovf = input(
        "Create OVF files? [Y/n]: "
    ).strip().lower() not in {"n", "no"}

    print("-" * 60)


    # ========================================================
    # CHECK TEMPLATE
    # ========================================================

    template_path = Path(TEMPLATE_FILE)

    if not template_path.exists():

        print()
        print("=" * 60)
        print("ERROR: TEMPLATE FILE NOT FOUND")
        print("=" * 60)

        print(
            f"Configured path: "
            f"{TEMPLATE_FILE}"
        )

        print(
            f"Resolved path:   "
            f"{template_path.resolve()}"
        )

        print()

        print("Available .mx3 files:")

        mx3_files = list(
            PROJECT_ROOT.rglob("*.mx3")
        )

        if mx3_files:

            for file in mx3_files:

                print(
                    f"  "
                    f"{file.relative_to(PROJECT_ROOT)}"
                )

        else:

            print(
                "  No .mx3 files found."
            )

        print()

        sys.exit(1)


    # ========================================================
    # CREATE OVF-ENABLED TEMPLATE
    # ========================================================

    original_template = (
        template_path.read_text()
    )

    if enable_ovf:

        print()
        print("Creating OVF-enabled template...")

        # ----------------------------------------------------
        # OVF COMMAND
        # ----------------------------------------------------
        #
        # Save the complete magnetization field every 50 ps.
        #
        # 50 ps = 0.05 ns
        #
        # MuMax3 will create files such as:
        #
        #   m000000.ovf
        #   m000001.ovf
        #   m000002.ovf
        #
        # inside run_<hash>.out/
        #

        ovf_command = """

// ============================================================
// OVF OUTPUT
// Added automatically by tools/single_iter_run.py
// ============================================================

autosave(m, 50e-12)

"""

        ovf_template_text = (
            ovf_command
            + original_template
        )

    else:

        print()
        print("OVF output disabled; using plain template.")
        ovf_template_text = original_template

    # Temporary template used only for this run.
    temp_template = (
        PROJECT_ROOT
        / "single_iter_ovf_template.mx3"
    )

    temp_template.write_text(
        ovf_template_text
    )


    # ========================================================
    # RUN ONE ITERATION
    # ========================================================

    print()
    print("=" * 60)
    print("STARTING MuMax3")
    print("=" * 60)

    print(
        f"Current:       "
        f"{current_mA:.4f} mA"
    )

    print(
        f"Pulse width:   "
        f"{pulse_ns:.4f} ns"
    )

    print(
        f"Temperature:   "
        f"{temperature_K:g} K"
    )

    print(
        f"Seed:           "
        f"{seed}"
    )

    print(
        f"OVF interval:   "
        f"{ '0.0500 ns' if enable_ovf else 'disabled' }"
    )

    print("=" * 60)


    try:

        result = run_iteration(

            pulse_ns=pulse_ns,

            seed=seed,

            temperature_K=temperature_K,

            current_A=current_A,

            gpu_id=0,

            mumax_exe=MUMAX_EXE,

            template_file=str(
                temp_template
            ),

            threshold=MEASUREMENT_THRESHOLD,

        )


    except KeyboardInterrupt:

        print()
        print()
        print("=" * 60)
        print("SIMULATION INTERRUPTED")
        print("=" * 60)

        sys.exit(1)


    except Exception as e:

        print()
        print("=" * 60)
        print("ERROR WHILE RUNNING SIMULATION")
        print("=" * 60)

        print(
            f"{type(e).__name__}: {e}"
        )

        print("=" * 60)

        raise


    finally:

        # Remove only the temporary template.
        #
        # DO NOT remove the MuMax3 .out directory.
        #

        temp_template.unlink(
            missing_ok=True
        )


    # ========================================================
    # RESULTS
    # ========================================================

    print()
    print("=" * 60)


    if result["success"]:

        print("SIMULATION FINISHED")
        print("=" * 60)

        print(
            f"State:              "
            f"{result['state']}"
        )

        print(
            f"mz:                 "
            f"{result['mz']:+.6f}"
        )

        print(
            f"Simulation time:    "
            f"{result['simulation_time_ns']:.4f} ns"
        )

        print(
            f"Runtime:             "
            f"{result['runtime_s']:.2f} s"
        )

        print(
            f"Termination:        "
            f"{result['termination_reason']}"
        )

        print(
            f"Cached:              "
            f"{'YES' if result.get('cached', False) else 'NO'}"
        )

        if "hash" in result:

            print(
                f"Hash:               "
                f"{result['hash']}"
            )

        if "table_file" in result:

            print(
                f"Table:              "
                f"{result['table_file']}"
            )

        if "metadata_file" in result:

            print(
                f"Metadata:           "
                f"{result['metadata_file']}"
            )


        # ----------------------------------------------------
        # OVF DIRECTORY
        # ----------------------------------------------------

        if "ovf_directory" in result:

            ovf_directory = Path(
                result["ovf_directory"]
            )

        else:

            # run_iteration currently returns the hash,
            # so construct the directory from it.
            ovf_directory = (
                PROJECT_ROOT
                / f"run_{result['hash']}.out"
            )


        print()
        print("-" * 60)
        print("OVF OUTPUT")
        print("-" * 60)

        print(
            f"Directory: "
            f"{ovf_directory}"
        )


        # ----------------------------------------------------
        # LIST OVF FILES
        # ----------------------------------------------------

        if ovf_directory.exists():

            ovf_files = sorted(
                ovf_directory.glob("*.ovf")
            )

            print(
                f"OVF files: "
                f"{len(ovf_files)}"
            )

            if ovf_files:

                print()
                print("First few OVF files:")

                for ovf in ovf_files[:10]:

                    print(
                        f"  {ovf.name}"
                    )

                if len(ovf_files) > 10:

                    print(
                        f"  ... "
                        f"and {len(ovf_files) - 10} more"
                    )

            else:

                print()
                print(
                    "WARNING: No OVF files were found."
                )

                print(
                    "Check that MuMax3 accepted the "
                    "autosave(m, 50e-12) command."
                )

        else:

            print()
            print(
                "WARNING: OVF directory does not exist."
            )

    else:

        print("SIMULATION FAILED")
        print("=" * 60)

        print(
            result.get(
                "error",
                "Unknown MuMax3 error."
            )
        )


    print()
    print("=" * 60)
    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()