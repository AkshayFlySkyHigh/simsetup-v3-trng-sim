# modules/iter_run.py

from pathlib import Path
import subprocess
import shutil
import time
import json
import pandas as pd
from modules.config import *
import socket

from modules.utils import (
    make_hash,
    classify_state,
    make_result_paths,
    ensure_dirs,
    write_metadata,
)


# ============================================================
# TABLE READER
# ============================================================

def read_table(tablefile):
    """
    Read a Mumax table and return the dataframe with proper
    column names.
    """

    df = pd.read_csv(
        tablefile,
        sep=r"\s+",
        comment="#",
        header=None,
    )

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

        mz_col = "mz2"

    elif ncols == 4:

        df.columns = [
            "t",
            "mx",
            "my",
            "mz",
        ]

        mz_col = "mz"

    else:

        raise RuntimeError(
            f"Unexpected table format ({ncols} columns)"
        )

    return df, mz_col


# ============================================================
# FINAL STATE
# ============================================================

def get_final_state(tablefile):

    df, mz_col = read_table(tablefile)

    return {
        "simulation_time_ns":
            float(df["t"].iloc[-1] * 1e9),

        "mz":
            float(df[mz_col].iloc[-1]),
    }


# ============================================================
# LATEST STATE
# ============================================================

def get_latest_state(tablefile):

    try:

        df, mz_col = read_table(tablefile)

        if len(df) == 0:
            return None

        return {
            "simulation_time_ns":
                float(df["t"].iloc[-1] * 1e9),

            "mz":
                float(df[mz_col].iloc[-1]),
        }

    except Exception:

        return None


# ============================================================
# RUN ONE ITERATION
# ============================================================

def run_iteration(
        pulse_ns,
        seed,
        mumax_exe=MUMAX_EXE,
        template_file=TEMPLATE_FILE,
        temperature_K=300,
        current_A=-0.0001,
        gpu_id=0,
        threshold=MEASUREMENT_THRESHOLD,
):

    start = time.time()

    # --------------------------------------------------------
    # READ TEMPLATE
    # --------------------------------------------------------

    template = Path(
        template_file
    ).read_text()

    # --------------------------------------------------------
    # HASH
    # --------------------------------------------------------

    hash_id = make_hash(
        pulse_ns,
        temperature_K,
        current_A,
        seed,
        template,
    )

    current_mA = current_A * 1000

    # --------------------------------------------------------
    # RESULT PATHS
    # --------------------------------------------------------

    paths = make_result_paths(
        pulse_ns,
        temperature_K,
        current_mA,
    )

    ensure_dirs(paths)

    table_file = (
        paths["tables"]
        / f"seed{seed:04d}_{hash_id}.txt"
    )

    metadata_file = (
        paths["metadata"]
        / f"seed{seed:04d}_{hash_id}.json"
    )

    # ========================================================
    # CACHE
    # ========================================================

    if ENABLE_CACHE and table_file.exists():

        final = get_final_state(
            table_file
        )

        mz = final["mz"]

        simulation_time_ns = (
            final["simulation_time_ns"]
        )

        return {
            "success": True,
            "cached": True,
            "seed": seed,
            "gpu": gpu_id,
            "mz": mz,

            "state": classify_state(
                mz,
                threshold,
            ),

            "runtime_s": 0,

            "simulation_time_ns":
                simulation_time_ns,

            "termination_reason":
                "CACHED",

            "stability_detected_at_ns":
                None,

            "hash":
                hash_id,
        }

    # ========================================================
    # CREATE MX3
    # ========================================================

    mx3 = (
        template

        .replace(
            "{PULSE}",
            str(pulse_ns)
        )

        .replace(
            "{TEMP}",
            str(temperature_K)
        )

        .replace(
            "{SEED}",
            str(seed)
        )

        .replace(
            "{CURRENT}",
            str(current_A)
        )

        .replace(
            "{TOT_TIME}",
            str(MAX_SIM_TIME_NS)
        )
    )

    mx3_name = (
        f"run_{hash_id}.mx3"
    )

    with open(
        mx3_name,
        "w"
    ) as f:

        f.write(mx3)

    # ========================================================
    # RUN
    # ========================================================

    success = False
    stderr = ""

    for attempt in [1, 2]:

        try:

            env = dict(
                **__import__("os").environ
            )

            env[
                "CUDA_VISIBLE_DEVICES"
            ] = str(gpu_id)

            process = subprocess.Popen(

                [
                    mumax_exe,
                    mx3_name,
                ],

                env=env,

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                text=True,
            )

            # ------------------------------------------------
            # MuMax3 output directory
            # ------------------------------------------------

            run_dir = Path(
                f"run_{hash_id}.out"
            )

            live_table = (
                run_dir
                / "table.txt"
            )

            # ------------------------------------------------
            # Stability tracking
            # ------------------------------------------------

            stability_start_ns = None

            stable_state = None

            termination_reason = (
                "MAX_TIME"
            )

            last_time_ns = None

            stability_detected_at_ns = None

            termination_time_ns = None

            # =================================================
            # MONITOR SIMULATION
            # =================================================

            while process.poll() is None:

                time.sleep(
                    CHECK_INTERVAL_S
                )

                latest = get_latest_state(
                    live_table
                )

                if latest is None:
                    continue

                if (
                    latest[
                        "simulation_time_ns"
                    ]
                    == last_time_ns
                ):
                    continue

                last_time_ns = (
                    latest[
                        "simulation_time_ns"
                    ]
                )

                current_time_ns = (
                    latest[
                        "simulation_time_ns"
                    ]
                )

                mz = latest["mz"]

                # ---------------------------------------------
                # Minimum simulation time
                # ---------------------------------------------

                if (
                    current_time_ns
                    < MIN_SIM_TIME_NS
                ):
                    continue

                # ---------------------------------------------
                # Classification
                # ---------------------------------------------

                current_state = classify_state(
                    mz,
                    threshold,
                )

                # ---------------------------------------------
                # Invalid region
                # ---------------------------------------------

                if (
                    current_state
                    == "INVALID"
                ):

                    stability_start_ns = None

                    stable_state = None

                    continue

                # ---------------------------------------------
                # First stable state
                # ---------------------------------------------

                if stable_state is None:

                    stable_state = (
                        current_state
                    )

                    stability_start_ns = (
                        current_time_ns
                    )

                    continue

                # ---------------------------------------------
                # State changed
                # ---------------------------------------------

                if (
                    current_state
                    != stable_state
                ):

                    stable_state = (
                        current_state
                    )

                    stability_start_ns = (
                        current_time_ns
                    )

                    continue

                # ---------------------------------------------
                # Stable long enough
                # ---------------------------------------------

                if (
                    current_time_ns
                    - stability_start_ns
                    >= STABILITY_WINDOW_NS
                ):

                    termination_reason = (
                        "EARLY_STABLE"
                    )

                    stability_detected_at_ns = (
                        stability_start_ns
                    )

                    termination_time_ns = (
                        current_time_ns
                    )

                    process.terminate()

                    try:

                        process.wait(
                            timeout=5
                        )

                    except subprocess.TimeoutExpired:

                        process.kill()

                    break

            # =================================================
            # PROCESS COMPLETE
            # =================================================

            stdout, stderr = (
                process.communicate()
            )

            # Early stopping intentionally terminates
            # MuMax3 with SIGTERM.
            if (
                process.returncode != 0
                and termination_reason
                != "EARLY_STABLE"
            ):

                raise subprocess.CalledProcessError(
                    process.returncode,
                    process.args,
                    output=stdout,
                    stderr=stderr,
                )

            success = True

            break

        except subprocess.CalledProcessError as e:

            stderr = e.stderr

            time.sleep(2)

    # ========================================================
    # FAILED
    # ========================================================

    if not success:

        failed_dir = (
            Path("failed_runs")
            /
            f"{pulse_ns:.3f}ns_"
            f"{temperature_K}K_"
            f"{current_mA:.3f}mA_"
            f"seed{seed:04d}_"
            f"{hash_id}"
        )

        failed_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.move(
            mx3_name,
            failed_dir / mx3_name,
        )

        with open(
            failed_dir / "stderr.txt",
            "w",
        ) as f:

            f.write(stderr)

        return {
            "success": False,

            "cached": False,

            "seed":
                seed,

            "gpu":
                gpu_id,

            "hash":
                hash_id,

            "error":
                stderr,

            "termination_reason":
                "MUMAX_ERROR",

            "simulation_time_ns":
                None,

            "stability_detected_at_ns":
                None,
        }

    # ========================================================
    # EXTRACT TABLE
    # ========================================================

    run_dir = Path(
        f"run_{hash_id}.out"
    )

    source = (
        run_dir
        / "table.txt"
    )

    # IMPORTANT:
    #
    # COPY the table instead of moving it.
    #
    # This means table.txt remains inside:
    #
    #     run_<hash>.out/
    #
    # while a copy is stored in the normal
    # results/tables directory.

    shutil.copy2(
        source,
        table_file,
    )

    # ========================================================
    # FINAL STATE
    # ========================================================

    final = get_final_state(
        table_file
    )

    mz = final["mz"]

    if (
        termination_reason
        == "EARLY_STABLE"
    ):

        simulation_time_ns = (
            termination_time_ns
        )

    else:

        simulation_time_ns = (
            final["simulation_time_ns"]
        )

    # ========================================================
    # CLASSIFY
    # ========================================================

    state = classify_state(
        mz,
        threshold,
    )

    # ========================================================
    # RUNTIME
    # ========================================================

    runtime = (
        time.time()
        - start
    )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = {

        # ----------------------------------------------------
        # Provenance
        # ----------------------------------------------------

        "machine_id":
            MACHINE_ID,

        "machine":
            MACHINE,

        "hostname":
            socket.gethostname(),

        "sim_protocol":
            SIM_PROTOCOL,

        "mumax_exe":
            MUMAX_EXE,

        # ----------------------------------------------------
        # Simulation
        # ----------------------------------------------------

        "seed":
            seed,

        "pulse_ns":
            pulse_ns,

        "temperature_K":
            temperature_K,

        "current_A":
            current_A,

        "gpu":
            gpu_id,

        "mz_final":
            mz,

        "state":
            state,

        "runtime_s":
            runtime,

        "simulation_time_ns":
            simulation_time_ns,

        "termination_reason":
            termination_reason,

        "stability_detected_at_ns":
            stability_detected_at_ns,

        "hash":
            hash_id,

        "cached":
            False,
    }

    write_metadata(
        metadata_file,
        metadata,
    )

    # ========================================================
    # CLEANUP
    # ========================================================

    if CLEANUP:

        # ----------------------------------------------------
        # CLEANUP ON
        # ----------------------------------------------------

        # Delete the temporary MX3 file.
        Path(mx3_name).unlink(
            missing_ok=True,
        )

        # Delete the complete MuMax3 output directory,
        # including table.txt and all OVF files.

        shutil.rmtree(
            run_dir,
            ignore_errors=True,
        )

        print()
        print(
            f"Cleanup ON: deleted "
            f"{run_dir}"
        )

    else:

        # ----------------------------------------------------
        # CLEANUP OFF
        # ----------------------------------------------------

        # Delete ONLY the temporary MX3 input file.
        #
        # Keep the entire MuMax3 output directory:
        #
        #     run_<hash>.out/
        #
        # including:
        #
        #     table.txt
        #     m000000.ovf
        #     m000001.ovf
        #     ...
        #

        Path(mx3_name).unlink(
            missing_ok=True,
        )

        print()
        print(
            f"Cleanup OFF: preserved "
            f"{run_dir}"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "success":
            True,

        "cached":
            False,

        "seed":
            seed,

        "gpu":
            gpu_id,

        "mz":
            mz,

        "state":
            state,

        "runtime_s":
            runtime,

        "simulation_time_ns":
            simulation_time_ns,

        "termination_reason":
            termination_reason,

        "stability_detected_at_ns":
            stability_detected_at_ns,

        "hash":
            hash_id,

        "table_file":
            str(table_file),

        "metadata_file":
            str(metadata_file),

        "ovf_directory":
            str(run_dir),
    }