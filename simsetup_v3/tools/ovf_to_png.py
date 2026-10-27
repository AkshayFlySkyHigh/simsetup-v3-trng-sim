#!/usr/bin/env python3

"""
Convert all MuMax3 OVF files in the current .out directory
to PNG using MuMax3's own mumax3-convert tool.

Spin arrows are added by MuMax3 during conversion.

Usage:

    python3 ovf_to_png.py

Run this from inside the .out directory, e.g.:

    cd ~/simsetup_v3/run_f80848a9.out
    python3 ovf_to_png.py
"""

import sys
import subprocess
from pathlib import Path


# ============================================================
# SETTINGS
# ============================================================

# Arrow size / spacing used by mumax3-convert.
#
# Smaller = more arrows
# Larger  = fewer arrows
#
# Try:
#
#   8   dense
#   12  fairly dense
#   16  medium
#   24  sparse
#   32  very sparse

ARROW_SIZE = 16


# ============================================================
# PROJECT ROOT
# ============================================================

# This script is expected to be inside:
#
# ~/simsetup_v3/run_xxxxx.out/
#
# Therefore:
#
# parent      = ~/simsetup_v3/
#
# We use that to access modules/config.py.

SCRIPT_DIR = Path(
    __file__
).resolve().parent

PROJECT_ROOT = (
    SCRIPT_DIR.parent
)


# ============================================================
# IMPORT MuMax3 PATH FROM CONFIG
# ============================================================

sys.path.insert(
    0,
    str(PROJECT_ROOT)
)

from modules.config import MUMAX_EXE


# ============================================================
# FIND mumax3-convert
# ============================================================

def get_mumax_converter():

    mumax_exe = Path(
        MUMAX_EXE
    ).resolve()

    # Example:
    #
    # MUMAX_EXE =
    # /path/to/mumax3.10/mumax3
    #
    # Converter:
    #
    # /path/to/mumax3.10/mumax3-convert

    return (
        mumax_exe.parent
        / "mumax3-convert"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Current .out directory
    # --------------------------------------------------------

    ovf_dir = Path.cwd().resolve()


    # --------------------------------------------------------
    # Find OVF files
    # --------------------------------------------------------

    ovf_files = sorted(
        ovf_dir.glob("*.ovf")
    )


    if not ovf_files:

        print()
        print("=" * 60)
        print("NO OVF FILES FOUND")
        print("=" * 60)

        print(
            f"Directory: {ovf_dir}"
        )

        print()
        print(
            "Run this script from inside a MuMax3 "
            ".out directory."
        )

        print("=" * 60)

        sys.exit(1)


    # --------------------------------------------------------
    # Find MuMax3 converter
    # --------------------------------------------------------

    mumax_converter = (
        get_mumax_converter()
    )


    print()
    print("=" * 60)
    print("MuMax3 OVF → PNG")
    print("=" * 60)

    print(
        f"Directory:     {ovf_dir}"
    )

    print(
        f"OVF files:     {len(ovf_files)}"
    )

    print(
        f"MuMax3:        {MUMAX_EXE}"
    )

    print(
        f"Converter:     {mumax_converter}"
    )

    print(
        f"Arrow size:    {ARROW_SIZE}"
    )

    print("=" * 60)


    # --------------------------------------------------------
    # Check converter
    # --------------------------------------------------------

    if not mumax_converter.exists():

        print()
        print("=" * 60)
        print("ERROR: mumax3-convert NOT FOUND")
        print("=" * 60)

        print()
        print(
            f"Expected:"
        )

        print(
            f"  {mumax_converter}"
        )

        print()
        print(
            "Check MUMAX_EXE in:"
        )

        print(
            "  modules/config.py"
        )

        print("=" * 60)

        sys.exit(1)


    # --------------------------------------------------------
    # Build command
    # --------------------------------------------------------

    command = [

        str(mumax_converter),

        "-png",

        "-arrows",
        str(ARROW_SIZE),

    ]


    # Add OVF files
    command.extend(
        str(ovf)
        for ovf in ovf_files
    )


    # --------------------------------------------------------
    # Run conversion
    # --------------------------------------------------------

    print()
    print("Converting with MuMax3...")
    print()


    try:

        result = subprocess.run(

            command,

            cwd=ovf_dir,

            text=True,

            capture_output=True,

        )

    except FileNotFoundError:

        print()
        print("=" * 60)
        print("ERROR: mumax3-convert could not be executed")
        print("=" * 60)

        print(
            f"Path: {mumax_converter}"
        )

        sys.exit(1)


    except PermissionError:

        print()
        print("=" * 60)
        print("ERROR: mumax3-convert is not executable")
        print("=" * 60)

        print(
            f"Path: {mumax_converter}"
        )

        print()
        print(
            "Check with:"
        )

        print(
            f"ls -l {mumax_converter}"
        )

        print("=" * 60)

        sys.exit(1)


    # --------------------------------------------------------
    # Print MuMax3 output
    # --------------------------------------------------------

    if result.stdout:

        print(
            result.stdout
        )


    if result.stderr:

        print(
            result.stderr
        )


    # --------------------------------------------------------
    # Check result
    # --------------------------------------------------------

    if result.returncode != 0:

        print()
        print("=" * 60)
        print("CONVERSION FAILED")
        print("=" * 60)

        print(
            f"Return code: {result.returncode}"
        )

        print()
        print("Command:")

        print(
            " ".join(command)
        )

        print("=" * 60)

        sys.exit(
            result.returncode
        )


    # --------------------------------------------------------
    # Find generated PNG files
    # --------------------------------------------------------

    png_files = sorted(
        ovf_dir.glob("*.png")
    )


    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)

    print(
        f"OVF files:     {len(ovf_files)}"
    )

    print(
        f"PNG files:     {len(png_files)}"
    )

    print(
        f"Arrow size:    {ARROW_SIZE}"
    )

    print(
        f"Location:      {ovf_dir}"
    )

    print("=" * 60)


    if png_files:

        print()
        print("Generated PNG files:")

        for png in png_files[:10]:

            print(
                f"  {png.name}"
            )

        if len(png_files) > 10:

            print(
                f"  ... and "
                f"{len(png_files) - 10} more"
            )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()