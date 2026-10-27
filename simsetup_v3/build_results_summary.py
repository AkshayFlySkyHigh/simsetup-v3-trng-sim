#!/usr/bin/env python3

import os
import re
import sys
import pandas as pd
from modules.config import *

##############################################################################
# CONFIG
##############################################################################

DEFAULT_THRESHOLD = MEASUREMENT_THRESHOLD

TABLES_ROOT = "results/tables"
OUTPUT_FILE = "results/results_summary.csv"

##############################################################################
# TABLE PARSER
##############################################################################


def get_final_mz(table_file):

    df = pd.read_csv(
        table_file,
        sep=r"\s+",
        comment="#",
        header=None,
        engine="python",
    )

    # mumax tableAdd(m) produces:
    # t mx my mz mx my mz

    return float(df.iloc[-1, -1])


##############################################################################
# CLASSIFICATION
##############################################################################


def classify(mz, threshold):

    if mz <= -threshold:
        return "SWITCHED"

    elif mz >= threshold:
        return "NOT_SWITCHED"

    else:
        return "INVALID"


##############################################################################
# MAIN
##############################################################################


def main():

    threshold = DEFAULT_THRESHOLD

    if len(sys.argv) > 1:
        threshold = float(sys.argv[1])

    print()
    print("=" * 70)
    print("Building results_summary.csv")
    print("=" * 70)
    print()
    print(f"Threshold = {threshold}")
    print()

    rows = []

    if not os.path.isdir(TABLES_ROOT):
        print("No tables directory found.")
        return
    
    folder_regex = re.compile(
        r"([0-9.]+)ns_([0-9]+)K_(-?[0-9.]+)mA"
    )

    folders = sorted(
        [
            f for f in os.listdir(TABLES_ROOT)
            if os.path.isdir(
                os.path.join(TABLES_ROOT, f)
            )
        ]
    )

    for folder in folders:

        match = folder_regex.match(folder)

        if not match:
            print(
                f"Skipping invalid folder: {folder}"
            )
            continue

        pulse_ns = float(match.group(1))
        temperature_K = int(match.group(2))
        current_mA = float(match.group(3))

        folder_path = os.path.join(
            TABLES_ROOT,
            folder
        )

        table_files = sorted(
            [
                f for f in os.listdir(folder_path)
                if f.endswith(".txt")
            ]
        )

        switched = 0
        not_switched = 0
        invalid = 0

        for table in table_files:

            table_path = os.path.join(
                folder_path,
                table
            )

            try:

                mz = get_final_mz(
                    table_path
                )

                state = classify(
                    mz,
                    threshold
                )

                if state == "SWITCHED":
                    switched += 1

                elif state == "NOT_SWITCHED":
                    not_switched += 1

                else:
                    invalid += 1

            except Exception as e:

                print(
                    f"ERROR: {table}"
                )
                print(e)

        iterations = (
            switched
            + not_switched
            + invalid
        )

        if iterations > 0:

            psw = (
                switched
                / iterations
            )

            pnot = (
                not_switched
                / iterations
            )

            pinvalid = (
                invalid
                / iterations
            )

        else:

            psw = 0
            pnot = 0
            pinvalid = 0

        rows.append(
            {
                "pulse_ns":
                    pulse_ns,

                "temperature_K":
                    temperature_K,

                "current_mA":
                    current_mA,

                "iterations":
                    iterations,

                "switched":
                    switched,

                "not_switched":
                    not_switched,

                "invalid":
                    invalid,

                "psw":
                    psw,

                "pnot":
                    pnot,

                "pinvalid":
                    pinvalid,
            }
        )

        print(
            f"{folder:<30} "
            f"N={iterations:<5} "
            f"Psw={psw:.4f}"
        )

    df = pd.DataFrame(rows)

    if len(df) > 0:

        df = df.sort_values(
            [
                "pulse_ns",
                "temperature_K",
                "current_mA",
            ]
        )

    os.makedirs(
        "results",
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 70)
    print(
        f"Wrote {len(df)} rows"
    )
    print(
        OUTPUT_FILE
    )
    print("=" * 70)


if __name__ == "__main__":
    main()