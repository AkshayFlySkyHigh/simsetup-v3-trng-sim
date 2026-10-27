# modules/utils.py

from pathlib import Path
import hashlib
import json
from datetime import timedelta
import csv
from modules.config import *

###################################################
# ANSI COLORS
###################################################

RESET = "\033[0m"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
PURPLE = "\033[95m"
CYAN = "\033[96m"

WHITE = "\033[97m"

GREY = "\033[90m"

##############################################################################
# HASHING
##############################################################################

def make_hash(
    pulse_ns,
    temperature_K,
    current_A,
    seed,
    template_text,
    version=SIM_PROTOCOL,
):
    """
    Generate a unique hash for a simulation.

    Includes:
        pulse width
        temperature
        current
        thermal seed
        template contents
        code version
    """

    text = (
        f"{pulse_ns}|"
        f"{temperature_K}|"
        f"{current_A}|"
        f"{seed}|"
        f"{version}|"
        f"{template_text}"
    )

    return hashlib.sha256(
        text.encode()
    ).hexdigest()[:8]


##############################################################################
# SWITCH CLASSIFICATION
##############################################################################

def classify_state(mz, threshold=0.8):
    """
    Classify final state from mz.
    """

    if mz < -threshold:
        return "SWITCHED"

    if mz > threshold:
        return "NOT_SWITCHED"

    return "INVALID"

##############################################################################
# COLORING
##############################################################################

def format_termination(reason):
    """
    Return a colored, padded termination reason.
    """

    colors = {
        "EARLY_STABLE": GREEN,
        "MAX_TIME": BLUE,
        "MUMAX_ERROR": RED,
        "CACHED": GREY,
    }

    color = colors.get(reason, "")

    return f"{color}{reason:<14}{RESET}"

def format_state(state):
    """
    Return colored switching state.
    """

    colors = {
        "SWITCHED": GREEN,
        "NOT_SWITCHED": BLUE,
        "INVALID": RED,
    }

    color = colors.get(state, WHITE)

    return f"{color}{state:<13}{RESET}"

def format_gpu(gpu_id):
    """
    Return colored GPU label.
    """

    gpu_colors = [
        RED,
        PURPLE,
        YELLOW,
        CYAN,
        BLUE,
        GREEN,
    ]

    color = gpu_colors[gpu_id % len(gpu_colors)]

    return f"{color}GPU{gpu_id}{RESET}"

def format_title(title):
    """
    Return a red section title.
    """

    return f"{RED}{title}{RESET}"

##############################################################################
# TIME FORMATTER
##############################################################################

def format_duration(seconds):
    """
    Convert seconds to HH:MM:SS.
    """

    return str(
        timedelta(
            seconds=int(seconds)
        )
    )


##############################################################################
# RESULT PATHS
##############################################################################

def make_result_paths(
    pulse_ns,
    temperature_K,
    current_mA,
):
    """
    Generate folder names.
    """

    folder = (
        f"{pulse_ns:.4f}ns_"
        f"{temperature_K}K_"
        f"{current_mA:.3f}mA"
    )

    table_dir = (
        Path(RESULTS_DIR)
        / "tables"
        / folder
    )

    plot_dir = (
        Path(RESULTS_DIR)
        / "plots"
        / folder
    )

    metadata_dir = (
        Path(RESULTS_DIR)
        / "metadata"
        / folder
    )

    return {
        "folder": folder,
        "tables": table_dir,
        "plots": plot_dir,
        "metadata": metadata_dir,
    }


##############################################################################
# CREATE DIRECTORY TREE
##############################################################################

def ensure_dirs(paths):

    for p in paths.values():

        if isinstance(p, Path):
            p.mkdir(
                parents=True,
                exist_ok=True,
            )


##############################################################################
# STATUS LOGGER
##############################################################################

def write_status(text):

    logfile = Path(RESULTS_DIR)/"status.log"

    logfile.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        logfile,
        "a",
        encoding="utf-8",
    ) as f:

        f.write(text + "\n")


##############################################################################
# ERROR LOGGER
##############################################################################

def write_error(text):

    logfile = Path(RESULTS_DIR)/"mumax_errors.log"

    logfile.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        logfile,
        "a",
        encoding="utf-8",
    ) as f:

        f.write(text + "\n")


##############################################################################
# METADATA WRITER
##############################################################################

def write_metadata(
    filename,
    data,
):

    filename.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
        )


##############################################################################
# SUMMARY WRITER
##############################################################################

def append_summary(row):

    file = Path(RESULTS_DIR) / "summary.csv"

    file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    exists = file.exists()

    with open(
        file,
        "a",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=row.keys(),
        )

        if not exists:
            writer.writeheader()

        writer.writerow(row)