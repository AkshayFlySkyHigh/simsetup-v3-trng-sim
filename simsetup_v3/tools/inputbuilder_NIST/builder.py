#!/usr/bin/env python3
"""
NIST input-file builder.

Expected layout:
simsetup_v3/
└── tools/
    └── inputbuilder_NIST/
        ├── builder.py
        ├── checker.py
        ├── params_inputfiles.csv
        └── generated_files/

Each CSV row describes one set of generated tables to turn into an ASCII
0/1 stream for the NIST STS.

Required CSV columns:
    pulse_ns
    temperature_K
    current_mA
    threshold

The tables directory is built automatically from pulse_ns, temperature_K,
and current_mA using the project layout:
    simsetup_v3/results/tables/<pulse>ns_<temperature>K_<current>mA

No iteration-count column is used.
"""

from pathlib import Path
import argparse
import csv
import math
import re
import sys

# ============================================================================
# USER TOGGLE
# ============================================================================

DISCARD_INVALIDS = True
# True  -> invalid mz values are discarded.
# False -> invalid mz values are forcibly converted:
#          mz > 0 -> 1
#          mz < 0 -> 0
#          mz == 0 -> ERROR (cannot assign a sign)

# ============================================================================
# PATHS
# ============================================================================

HERE = Path(__file__).resolve().parent
DEFAULT_PARAMS_FILE = HERE / "params_inputfiles.csv"
GENERATED_DIR = HERE / "generated_files"
PROJECT_ROOT = HERE.parent.parent
TABLES_ROOT = PROJECT_ROOT / "results" / "tables"

# Table extensions we will inspect.
TABLE_EXTENSIONS = {".txt", ".csv", ".dat"}

# ============================================================================
# HELPERS
# ============================================================================

def natural_key(path: Path):
    """Sort names containing numbers naturally: seed2 before seed10."""
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def parse_float(value, name):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}: {value!r}")


def format_number(value, decimals=4):
    """Filename-safe number formatting."""
    text = f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")
    return text.replace("-", "m").replace(".", "p")


def format_current(value):
    """Current in mA, filename-safe."""
    return format_number(value, 4)


def build_tables_path(pulse_ns, temperature_K, current_mA):
    """Build the MuMax results/tables path from the physical parameters."""
    pulse = f"{float(pulse_ns):.4f}"
    temperature = f"{float(temperature_K):g}"
    current = f"{float(current_mA):.3f}"

    return TABLES_ROOT / f"{pulse}ns_{temperature}K_{current}mA"


def find_mz_index(header):
    """Find an mz column, allowing common MuMax capitalization variants."""
    normalized = [h.strip().lower() for h in header]

    for candidate in ("mz", "<mz>"):
        if candidate in normalized:
            return normalized.index(candidate)

    # Handle headers such as "m.z" or "m_z".
    for i, h in enumerate(normalized):
        compact = re.sub(r"[^a-z0-9]", "", h)
        if compact == "mz":
            return i

    raise ValueError(
        f"Could not find an mz column in header: {header}"
    )


def read_table_mz(table_path):
    """
    Read final mz from a MuMax3 table file.

    Expected header:
        # t (s)    mx ()    my ()    mz ()    mx ()    my ()    mz ()
    """

    header_names = None
    data_rows = []

    with table_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            # Parse commented MuMax3 header
            if line.startswith("#"):
                header_text = line.lstrip("#").strip()

                # Extract variable names from "name (unit)" pairs
                header_names = re.findall(
                    r'([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)',
                    header_text
                )

                continue

            # Parse numerical row
            try:
                row = [float(x) for x in re.split(r"\s+", line)]
            except ValueError:
                continue

            data_rows.append(row)

    if header_names is None:
        raise ValueError("Could not find MuMax3 table header")

    mz_indices = [
        i for i, name in enumerate(header_names)
        if name.lower() == "mz"
    ]

    if not mz_indices:
        raise ValueError(
            f"Could not find an mz column in header: {header_names}"
        )

    if not data_rows:
        raise ValueError("No numerical data rows found")

    mz_index = mz_indices[0]
    final_row = data_rows[-1]

    if mz_index >= len(final_row):
        raise ValueError(
            f"mz column {mz_index} unavailable in row with "
            f"{len(final_row)} columns"
        )

    return final_row[mz_index]


def classify_mz(mz, threshold):
    """
    Convert mz to a NIST bit.

    Normal:
        mz >= +threshold -> 1
        mz <= -threshold -> 0

    Invalid:
        -threshold < mz < +threshold

    If DISCARD_INVALIDS is False:
        positive -> 1
        negative -> 0
        zero     -> error
    """
    if mz >= threshold:
        return "1", "VALID_1"

    if mz <= -threshold:
        return "0", "VALID_0"

    if DISCARD_INVALIDS:
        return None, "INVALID_DISCARDED"

    if mz > 0:
        return "1", "INVALID_FORCED_1"

    if mz < 0:
        return "0", "INVALID_FORCED_0"

    raise ValueError(
        "Encountered mz == 0 while DISCARD_INVALIDS=False; "
        "zero has no positive/negative sign."
    )


def collect_table_files(tables_dir):
    """Recursively collect generated table files."""
    tables_dir = Path(tables_dir)

    if not tables_dir.exists():
        raise FileNotFoundError(f"Tables directory does not exist: {tables_dir}")

    files = [
        p for p in tables_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in TABLE_EXTENSIONS
    ]

    # Do not accidentally consume a previously generated NIST input.
    files = [
        p for p in files
        if "generated_files" not in p.parts
    ]

    return sorted(files, key=natural_key)


def build_sequence(tables_dir, threshold):
    """Build one bit sequence from all generated tables."""
    table_files = collect_table_files(tables_dir)

    if not table_files:
        raise RuntimeError(f"No table files found in {tables_dir}")

    bits = []
    stats = {
        "tables": len(table_files),
        "valid_0": 0,
        "valid_1": 0,
        "invalid_discarded": 0,
        "invalid_forced_0": 0,
        "invalid_forced_1": 0,
        "failed_tables": 0,
    }

    for table in table_files:
        try:
            mz = read_table_mz(table)
            bit, status = classify_mz(mz, threshold)

            if bit is None:
                stats["invalid_discarded"] += 1
                continue

            bits.append(bit)

            if status == "VALID_0":
                stats["valid_0"] += 1
            elif status == "VALID_1":
                stats["valid_1"] += 1
            elif status == "INVALID_FORCED_0":
                stats["invalid_forced_0"] += 1
            elif status == "INVALID_FORCED_1":
                stats["invalid_forced_1"] += 1

        except Exception as exc:
            stats["failed_tables"] += 1
            print(f"WARNING: skipped {table}: {exc}", file=sys.stderr)

    if not bits:
        raise RuntimeError("No bits were produced.")

    if stats["failed_tables"]:
        print(
            f"WARNING: {stats['failed_tables']} table(s) could not be read."
        )

    return "".join(bits), stats


def load_parameter_rows(csv_path):
    """Read parameter rows from params_inputfiles.csv."""
    with Path(csv_path).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    required = {
        "pulse_ns",
        "temperature_K",
        "current_mA",
        "threshold",
    }

    if not rows:
        raise ValueError(f"No parameter rows found in {csv_path}")

    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(
            "Missing CSV columns: " + ", ".join(sorted(missing))
        )

    return rows


def make_output_name(row, length):
    pulse = format_number(parse_float(row["pulse_ns"], "pulse_ns"), 4)
    temp = format_number(parse_float(row["temperature_K"], "temperature_K"), 2)
    current = format_current(parse_float(row["current_mA"], "current_mA"))

    return (
        f"T{temp}K_"
        f"P{pulse}ns_"
        f"I{current}mA_"
        f"L{length}.txt"
    )


def build_from_csv(params_file):
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_parameter_rows(params_file)

    print("=" * 72)
    print("NIST INPUT BUILDER")
    print("=" * 72)
    print(f"Parameters : {params_file}")
    print(
        f"Discard invalids : "
        f"{'YES' if DISCARD_INVALIDS else 'NO (force sign -> bit)'}"
    )
    print()
    # Import checker only here so checker.py remains independently usable.
    from checker import check_file

    for row_number, row in enumerate(rows, start=1):
        threshold = parse_float(row["threshold"], "threshold")

        if threshold < 0:
            raise ValueError(
                f"Row {row_number}: threshold must be >= 0."
            )

        tables_dir = build_tables_path(
            parse_float(row["pulse_ns"], "pulse_ns"),
            parse_float(row["temperature_K"], "temperature_K"),
            parse_float(row["current_mA"], "current_mA"),
        )

        bits, stats = build_sequence(tables_dir, threshold)
        length = len(bits)

        output_name = make_output_name(row, length)
        output_path = GENERATED_DIR / output_name

        with output_path.open("w", encoding="ascii", newline="") as f:
            f.write(bits)
            f.write("\n")

        print("-" * 72)
        print(f"Row                 : {row_number}")
        print(f"Tables directory    : {tables_dir}")
        print(f"Threshold           : ±{threshold:g}")
        print(f"Tables found        : {stats['tables']}")
        print(f"Valid 0             : {stats['valid_0']}")
        print(f"Valid 1             : {stats['valid_1']}")
        print(f"Invalid discarded   : {stats['invalid_discarded']}")
        print(f"Invalid forced 0    : {stats['invalid_forced_0']}")
        print(f"Invalid forced 1    : {stats['invalid_forced_1']}")
        print(f"Failed tables       : {stats['failed_tables']}")
        print(f"Sequence length     : {length}")
        print(f"Output              : {output_path}")
        print()
        print("NIST CHECK")
        check_file(output_path, quiet=False)

    print("=" * 72)
    print("BUILD COMPLETE")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description="Build ASCII 0/1 input files for NIST STS."
    )
    parser.add_argument(
        "--params",
        type=Path,
        default=DEFAULT_PARAMS_FILE,
        help="CSV parameter file.",
    )

    parser.add_argument("--pulse", type=float)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--current", type=float)
    parser.add_argument("--threshold", type=float)
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for --tables mode.",
    )
    parser.add_argument(
        "--check-only",
        type=Path,
        help="Check an existing NIST input file without building it.",
    )

    args = parser.parse_args()

    if args.check_only:
        from checker import check_file
        check_file(args.check_only, quiet=False)
        return

    # Optional single-row mode: the tables path is still constructed from
    # pulse, temperature and current; the user never supplies it.
    single_mode_values = (args.pulse, args.temperature, args.current, args.threshold)
    if any(value is not None for value in single_mode_values):
        missing = [
            name for name, value in (
                ("--pulse", args.pulse),
                ("--temperature", args.temperature),
                ("--current", args.current),
                ("--threshold", args.threshold),
            )
            if value is None
        ]

        if missing:
            parser.error(
                "single-row mode requires: " + ", ".join(missing)
            )

        tables_dir = build_tables_path(args.pulse, args.temperature, args.current)
        bits, stats = build_sequence(tables_dir, args.threshold)
        length = len(bits)

        output = args.output
        if output is None:
            row = {
                "pulse_ns": args.pulse,
                "temperature_K": args.temperature,
                "current_mA": args.current,
            }
            output = GENERATED_DIR / make_output_name(row, length)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(bits + "\n", encoding="ascii")

        print(f"Tables directory : {tables_dir}")
        print(f"Sequence length  : {length}")
        print(f"Output           : {output}")

        from checker import check_file
        check_file(output, quiet=False)
        return

    build_from_csv(args.params)


if __name__ == "__main__":
    main()
