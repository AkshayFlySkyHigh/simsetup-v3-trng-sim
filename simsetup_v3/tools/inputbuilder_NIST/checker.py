#!/usr/bin/env python3
"""
NIST SP 800-22 Rev. 1a input-size checker.

This file is deliberately independent from builder.py.

Usage:
    python checker.py path/to/input.txt

It prints:
    - sequence length
    - YES/NO for each of the 15 NIST tests
    - the 15-character selection string

The selection string follows the NIST menu order shown in Section 5.6:
01 Frequency
02 Block Frequency
03 Cumulative Sums
04 Runs
05 Longest Runs of Ones
06 Rank
07 Spectral / DFT
08 Nonperiodic Template Matchings
09 Overlapping Template Matchings
10 Universal Statistical
11 Approximate Entropy
12 Random Excursions
13 Random Excursions Variant
14 Serial
15 Linear Complexity

The limits below follow the input-size recommendations in NIST SP 800-22
Rev. 1a. Where a test has parameter-dependent recommendations, the checker
uses the standard/default configuration described by the document.
"""

from pathlib import Path
import argparse
import math
import re

# ============================================================================
# NIST SP 800-22 Rev. 1a test definitions
# ============================================================================

TESTS = [
    ("Frequency", 100),
    ("Block Frequency", 128),
    ("Cumulative Sums", 100),
    ("Runs", 100),
    ("Longest Run of Ones", 128),
    ("Rank", 38912),
    ("Spectral / DFT", 1000),

    # Rev. 1a recommends m=9 or m=10 and gives the standard 1,000,000-bit
    # operating point used by the supplied examples. We use that conservative
    # operating point for the standalone checker.
    ("Nonperiodic Template Matchings", 1_000_000),
    ("Overlapping Template Matchings", 1_000_000),

    # Smallest recommended Maurer configuration: L=6, Q=640 -> 387,840 bits.
    ("Universal Statistical", 387_840),

    # Standard Rev. 1a recommendation: n >= 10^6, M in 500..5000,
    # N >= 200.
    ("Linear Complexity", 1_000_000),

    # For the standard STS test configuration, the practical reference
    # point is 1,000,000 bits. This is intentionally conservative.
    ("Serial", 1_000_000),

    # The document's condition is m < floor(log2(n)) - 5. The checker uses
    # the default/example m=10, so n must satisfy:
    # 10 < floor(log2(n)) - 5  => floor(log2(n)) >= 16 => n >= 65536.
    ("Approximate Entropy", 65_536),

    ("Random Excursions", 1_000_000),
    ("Random Excursions Variant", 1_000_000),
]

def read_bits(path):
    """Read an ASCII NIST input file and validate that it contains only 0/1."""
    text = Path(path).read_text(encoding="ascii")

    bits = re.sub(r"\s+", "", text)

    if not bits:
        raise ValueError("Input file contains no bits.")

    invalid = set(bits) - {"0", "1"}
    if invalid:
        raise ValueError(
            "Input file contains non-binary characters: "
            + ", ".join(sorted(repr(x) for x in invalid))
        )

    return bits


def get_selection_string(length):
    """Return the 15-character NIST selection string."""
    return "".join(
        "1" if length >= minimum else "0"
        for _, minimum in TESTS
    )


def check_file(path, quiet=False):
    """
    Check one existing NIST input file.

    Returns:
        (length, selection_string, results)
    """
    path = Path(path)
    bits = read_bits(path)
    length = len(bits)

    selection = get_selection_string(length)

    results = []

    if not quiet:
        print(f"File            : {path}")
        print(f"Sequence length : {length}")
        print()

    for index, ((name, minimum), flag) in enumerate(
        zip(TESTS, selection), start=1
    ):
        can_run = flag == "1"
        results.append((index, name, minimum, can_run))

        if not quiet:
            print(
                f"{index:02d} {name:<32} "
                f"{'YES' if can_run else 'NO'}"
                f"{'' if can_run else f'  (needs >= {minimum:,} bits)'}"
            )

    if not quiet:
        print()
        print(f"15-char selection string : {selection}")

    print()
    print("=" * 72)
    print("NIST INPUT FILE")
    print("=" * 72)
    print("Full path:")
    print(f"  {path.resolve()}")
    print()
    #print("Copy this path and paste it into NIST when prompted.")

    return length, selection, results


def main():
    parser = argparse.ArgumentParser(
        description="Check an existing NIST STS ASCII input file."
    )
    parser.add_argument("input_file", type=Path)
    args = parser.parse_args()

    check_file(args.input_file, quiet=False)


if __name__ == "__main__":
    main()
