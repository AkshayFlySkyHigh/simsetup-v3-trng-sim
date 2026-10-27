# build_specific_iter_params.py

import os
import re
import pandas as pd

from modules.config import (
    TABLES_DIR,
    MEASUREMENT_THRESHOLD,
)


##############################################################################
# HELPERS
##############################################################################

def classify_mz(mz):

    if mz < -MEASUREMENT_THRESHOLD:
        return "SWITCHED"

    elif mz > MEASUREMENT_THRESHOLD:
        return "NOT_SWITCHED"

    else:
        return "INVALID"


def extract_seed(filename):

    match = re.search(
        r"seed(\d+)",
        filename,
    )

    if match:
        return int(match.group(1))

    return None


def read_final_mz(filepath):

    df = pd.read_csv(
        filepath,
        sep="\t",
        comment="#",
    )

    if "mz" not in df.columns:
        raise ValueError(
            "column 'mz' not found"
        )

    return float(
        df["mz"].iloc[-1]
    )


##############################################################################
# MAIN
##############################################################################

def main():

    print()
    print("=" * 70)
    print("Searching invalid runs")
    print("=" * 70)
    print()

    params = pd.read_csv(
        "params.csv"
    )

    output_rows = []

    total_tables = 0
    total_invalid = 0

    for _, row in params.iterrows():

        pulse_ns = float(
            row["pulse_ns"]
        )

        temperature_K = int(
            row["temperature_K"]
        )

        current_A = float(
            row["current_A"]
        )

        run_name = (
            f"{pulse_ns:.3f}ns_"
            f"{temperature_K}K_"
            f"{current_A*1000:.3f}mA"
        )

        tables_folder = os.path.join(
            TABLES_DIR,
            run_name
        )

        print(
            f"{pulse_ns:.3f} ns | "
            f"{temperature_K} K | "
            f"{current_A*1000:.3f} mA"
        )

        if not os.path.isdir(
                tables_folder):

            print(
                "Folder not found:"
            )
            print(
                tables_folder
            )
            print()

            continue

        table_files = sorted(
            [
                f
                for f in os.listdir(
                    tables_folder
                )
                if f.endswith(
                    ".txt"
                )
            ]
        )

        print(
            f"Found "
            f"{len(table_files)} "
            f"tables"
        )

        invalid_here = 0

        for filename in table_files:

            total_tables += 1

            filepath = os.path.join(
                tables_folder,
                filename
            )

            try:

                mz = read_final_mz(
                    filepath
                )

            except Exception as e:

                print(
                    f"ERROR reading:"
                )

                print(
                    filepath
                )

                print(
                    f"Reason: {e}"
                )

                continue

            state = classify_mz(
                mz
            )

            if state == "INVALID":

                seed = extract_seed(
                    filename
                )

                if seed is None:

                    print(
                        f"Could not "
                        f"extract seed:"
                    )

                    print(
                        filename
                    )

                    continue

                output_rows.append(
                    {
                        "pulse_ns":
                            pulse_ns,

                        "temperature_K":
                            temperature_K,

                        "current_A":
                            current_A,

                        "seed_number":
                            seed,
                    }
                )

                invalid_here += 1
                total_invalid += 1

                print(
                    f"INVALID: "
                    f"seed={seed}"
                )

        if invalid_here == 0:

            print(
                "No invalid runs"
            )

        print()

    ##########################################################################
    # WRITE OUTPUT
    ##########################################################################

    output = pd.DataFrame(
        output_rows,
        columns=[
            "pulse_ns",
            "temperature_K",
            "current_A",
            "seed_number",
        ]
    )

    output.to_csv(
        "specific_iter_params.csv",
        index=False,
    )

    ##########################################################################
    # SUMMARY
    ##########################################################################

    print()
    print("=" * 70)
    print("Finished")
    print("=" * 70)
    print()

    print(
        f"Tables scanned : "
        f"{total_tables}"
    )

    print(
        f"Invalid found  : "
        f"{total_invalid}"
    )

    print()

    print(
        "Written:"
    )

    print(
        "specific_iter_params.csv"
    )

    print()


if __name__ == "__main__":
    main()