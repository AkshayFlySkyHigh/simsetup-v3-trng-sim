# runner_scheduled.py
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timedelta
import pandas as pd
import os
import csv
from modules.iter_run import run_iteration
from modules.autoplot import create_autoplot
import socket
from collections import deque

##############################################################################
# CONFIG
##############################################################################

from modules.config import *

##############################################################################
# CONFIG
##############################################################################

from modules.utils import format_termination, format_state, format_gpu, format_title

##############################################################################
# MAIN
##############################################################################

def main():

    params = pd.read_csv(
        "params.csv"
    )
    
    print()
    print(format_title("="*70))
    print(f"Machine        : {MACHINE}")
    print(f"Machine ID     : {MACHINE_ID}")
    print(f"Hostname       : {socket.gethostname()}")
    print(f"Protocol       : {SIM_PROTOCOL}")
    print(f"MuMax3         : {MUMAX_EXE}")
    print(f"GPUs           : {GPU_IDS}")
    print(format_title("="*70))
    print()

    ##############################################################
    # STARTUP SUMMARY
    ##############################################################

    print()
    print(format_title("Sweep parameters loaded:"))
    print()

    print(
        f"{'pulse_ns':>10} "
        f"{'temp_K':>8} "
        f"{'current_mA':>12} "
        f"{'start':>8} "
        f"{'end':>8} "
        f"{'step':>8} "
        f"{'count':>8}"
    )

    total_simulations = 0

    for _, row in params.iterrows():

        pulse = float(
            row["pulse_ns"]
        )

        temp = int(
            row["temperature_K"]
        )

        current = float(
            row["current_A"]
        )

        start_seed = int(
            row["start_seed"]
        )

        end_seed = int(
            row["end_seed"]
        )

        seed_step = int(
            row["seed_step"]
        )

        iterations = (
            (end_seed - start_seed)
            // seed_step
            + 1
        )

        total_simulations += iterations

        print(
            f"{pulse:10.4f} "
            f"{temp:8d} "
            f"{current*1000:12.3f} "
            f"{start_seed:8d} "
            f"{end_seed:8d} "
            f"{seed_step:8d} "
            f"{iterations:8d}"
        )

    print()

    print(
        f"Total simulations to run: "
        f"{total_simulations}"
    )

    print(
        f"GPU_IDS: {len(GPU_IDS)} | "
        f"Cache: {'ON' if ENABLE_CACHE else 'OFF'}"
    )

    print()

    if sys.stdin.isatty():

        input(
            "Press Enter to start simulations..."
        )

        print()

    total_rows = len(params)

    overall = {

        "completed": 0,

        "simulated": 0,

        "cached": 0,

        "failed": 0,

        "switched": 0,

        "not_switched": 0,

        "invalid": 0,

        "early_stable": 0,

        "max_time": 0,

        "mumax_error": 0,

        "runtime": 0.0,

        "simulation_times": [],
    }

    global_start = time.time()

    RUN_SUMMARY_FILE = (
    "results/run_summary.csv"
)

    for row_index, row in params.iterrows():

        pulse_ns = float(
            row["pulse_ns"]
        )

        temperature_K = int(
            row["temperature_K"]
        )

        current_A = float(
            row["current_A"]
        )

        start_seed = int(
            row["start_seed"]
        )

        end_seed = int(
            row["end_seed"]
        )

        seed_step = int(
            row["seed_step"]
        )

        iterations = (
            (end_seed - start_seed)
            // seed_step
            + 1
        )

        ##################################################################
        # STATS
        ##################################################################

        stats = {

            "total":
                iterations,

            "completed":
                0,

            "cached":
                0,

            "simulated":
                0,

            "failed":
                0,

            "switched":
                0,

            "not_switched":
                0,

            "invalid":
                0,

            "early_stable":
                0,

            "max_time":
                0,

            "mumax_error":
                0,

            "runtime":
                0.0,

            "runtime_history":
                deque(maxlen=ETA_AVERAGE_WINDOW),

            "simulation_times":
                [],
        }

        row_start = time.time()

        print()
        print(format_title("=" * 70))
        print(
            format_title(
                f"ROW {row_index+1}/{total_rows}"
            )
        )
        print(
            f"pulse={pulse_ns} ns | "
            f"T={temperature_K} K | "
            f"I={current_A*1000:.3f} mA | "
            f"N={iterations}"
        )
        print(format_title("=" * 70))

        ##################################################################
        # CREATE JOBS
        ##################################################################

        pending = []

        iteration = 1

        for seed in range(
            start_seed,
            end_seed + 1,
            seed_step,
        ):

            pending.append(
                {
                    "iteration":
                        iteration,

                    "seed":
                        seed + SEED_SHIFT,

                    "pulse_ns":
                        pulse_ns,

                    "temperature_K":
                        temperature_K,

                    "current_A":
                        current_A,
                }
            )

            iteration += 1

        ##################################################################
        # SCHEDULER
        ##################################################################

        executor = ThreadPoolExecutor(
            max_workers=len(GPU_IDS)
        )

        running = {}

        while pending or running:

            ##############################################################
            # FILL FREE GPU_IDS
            ##############################################################

            free = [
                gpu
                for gpu in GPU_IDS
                if gpu not in running
            ]

            while free and pending:

                gpu = free.pop(0)

                job = pending.pop(0)

                future = executor.submit(
                    run_iteration,

                    pulse_ns=job["pulse_ns"],
                    temperature_K=job["temperature_K"],
                    current_A=job["current_A"],
                    seed=job["seed"],
                    gpu_id=gpu,
                    mumax_exe=MUMAX_EXE,
                    template_file=TEMPLATE_FILE,
                    threshold=MEASUREMENT_THRESHOLD
                )

                running[gpu] = {
                    "future": future,
                    "iteration": job["iteration"],
                    "seed": job["seed"],
                }

            ##############################################################
            # WAIT
            ##############################################################

            if running:

                done, _ = wait(
                    [
                        info["future"]
                        for info in running.values()
                    ],
                    return_when=FIRST_COMPLETED,
                )

                print()

                for future in done:
                
                    ##############################################################
                    # FIND FINISHED GPU
                    ##############################################################

                    gpu_finished = None

                    for gpu, info in running.items():
                    
                        if info["future"] == future:
                            gpu_finished = gpu
                            break
                        
                    result = future.result()

                    running_iteration = (
                        running[gpu_finished]["iteration"]
                    )

                    del running[gpu_finished]

                    ##############################################################
                    # UPDATE STATS
                    ##############################################################

                    stats["completed"] += 1

                    if result["success"]:
                    
                        if result["cached"]:
                        
                            stats["cached"] += 1

                        else:
                        
                            stats["simulated"] += 1

                            stats["runtime"] += result["runtime_s"]

                            stats["runtime_history"].append(
                                result["runtime_s"]
                            )

                            stats["simulation_times"].append(
                                result["simulation_time_ns"]
                            )

                        if result["state"] == "SWITCHED":
                        
                            stats["switched"] += 1

                        elif result["state"] == "NOT_SWITCHED":
                        
                            stats["not_switched"] += 1

                        else:
                        
                            stats["invalid"] += 1

                        if result["termination_reason"] == "EARLY_STABLE":
                        
                            stats["early_stable"] += 1

                        elif result["termination_reason"] == "MAX_TIME":
                        
                            stats["max_time"] += 1

                    else:
                    
                        stats["failed"] += 1

                        stats["mumax_error"] += 1

                    ##############################################################
                    # PROGRESS
                    ##############################################################

                    progress = (
                        100
                        * stats["completed"]
                        / stats["total"]
                    )

                    ##############################################################
                    # ETA
                    ##############################################################
                    
                    elapsed = (
                        time.time()
                        - row_start
                    )
                    
                    if stats["runtime_history"]:
                    
                        avg_runtime = (
                            sum(stats["runtime_history"])
                            / len(stats["runtime_history"])
                        )
                    
                        remaining = max(
                            0,
                            stats["total"] - stats["completed"]
                        )
                    
                        eta_seconds = (
                            avg_runtime
                            * remaining
                            / len(GPU_IDS)
                        )
                    
                    else:
                    
                        avg_runtime = 0
                    
                        eta_seconds = 0
                    
                    now = datetime.now()
                    
                    etc = (
                        now
                        + timedelta(
                            seconds=eta_seconds
                        )
                    )
                    
                    ##############################################################
                    # PRINT
                    ##############################################################

                    finished_text = (
                        f"GPU{gpu_finished} "
                        f"finished "
                        f"i{running_iteration}/s{result['seed']}"
                    )

                    if pending:
                    
                        next_job = pending[0]

                        next_text = (
                            f"GPU{gpu_finished} "
                            f"next "
                            f"i{next_job['iteration']}"
                            f"/s{next_job['seed']}"
                        )

                    else:
                    
                        next_text = (
                            f"GPU{gpu_finished} "
                            f"next idle"
                        )

                    other_running = []

                    for gpu in GPU_IDS:
                    
                        if gpu == gpu_finished:
                            continue
                        
                        if gpu in running:
                        
                            other_running.append(
                                f"GPU{gpu} "
                                f"running "
                                f"i{running[gpu]['iteration']}"
                                f"/s{running[gpu]['seed']}"
                            )

                        else:
                        
                            other_running.append(
                                f"GPU{gpu} idle"
                            )

                    print(
                        f"{progress:6.3f}% Complete | "
                        f"{finished_text} | "
                        f"{next_text}"
                        + (
                            " | " + " | ".join(other_running)
                            if other_running else ""
                        )
                    )

                    print(
                        f"iter={running_iteration}/{stats['total']} | "
                        f"seed={result['seed']} | "
                        f"P={pulse_ns:.4f}ns | "
                        f"T={temperature_K}K | "
                        f"I={current_A*1000:.3f}mA | "
                        f"{format_gpu(result['gpu'])} | "
                        f"mz={result['mz']:+.4f} | "
                        f"{format_state(result['state'])}"
                    )

                    if result["success"]:
                        t_sim = f"{result['simulation_time_ns']:.2f}ns"
                    else:
                        t_sim = "N/A"
                    
                    print(
                        f"{format_termination(result['termination_reason'])} | "
                        f"t_sim={t_sim} | "
                        f"Completed={stats['completed']} | "
                        f"Simulated={stats['simulated']} | "
                        f"Cached={stats['cached']} | "
                        f"Failed={stats['failed']}"
                    )

                    ##############################################################
                    # RUNNING PROBABILITIES
                    ##############################################################

                    if stats["completed"] > 0:

                        psw = (
                            100
                            * stats["switched"]
                            / stats["completed"]
                        )

                        pnot = (
                            100
                            * stats["not_switched"]
                            / stats["completed"]
                        )

                        pinv = (
                            100
                            * stats["invalid"]
                            / stats["completed"]
                        )

                    else:

                        psw = 0
                        pnot = 0
                        pinv = 0

                    print(
                        f"Switched={stats['switched']} "
                        f"({psw:.3f}%) | "
                        f"Not switched={stats['not_switched']} "
                        f"({pnot:.3f}%) | "
                        f"Invalid={stats['invalid']} "
                        f"({pinv:.3f}%)"
                    )

                    print(
                        f"NOW: {now.strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"t_elap={timedelta(seconds=int(elapsed))} | "
                        f"ETC: {etc.strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"t_rem={timedelta(seconds=int(eta_seconds))}"
                    )

        executor.shutdown()

        ##############################################################
        # FINAL STATISTICS
        ##############################################################

        elapsed = (
            time.time()
            - row_start
        )

        if stats["completed"] > 0:

            psw = (
                100
                * stats["switched"]
                / stats["completed"]
            )

            pnot = (
                100
                * stats["not_switched"]
                / stats["completed"]
            )

            pinv = (
                100
                * stats["invalid"]
                / stats["completed"]
            )

        else:

            psw = 0
            pnot = 0
            pinv = 0

        if stats["simulated"] > 0:

            if stats["runtime_history"]:

                avg_runtime = (
                    sum(stats["runtime_history"])
                    / len(stats["runtime_history"])
                )

            else:
            
                avg_runtime = 0

        else:

            avg_runtime = 0

        run_summary = {

            "timestamp":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "pulse_ns":
                pulse_ns,

            "temperature_K":
                temperature_K,

            "current_mA":
                current_A * 1000,

            "iterations":
                iterations,

            "seed_shift":
                SEED_SHIFT,

            "threshold":
                MEASUREMENT_THRESHOLD,

            "switched":
                stats["switched"],

            "not_switched":
                stats["not_switched"],

            "invalid":
                stats["invalid"],

            "psw":
                psw / 100,

            "pnot":
                pnot / 100,

            "pinvalid":
                pinv / 100,

            "completed":
                stats["completed"],

            "simulated":
                stats["simulated"],

            "cached":
                stats["cached"],

            "failed":
                stats["failed"],

            "early_stable":
                stats["early_stable"],

            "max_time":
                stats["max_time"],

            "mumax_error":
                stats["mumax_error"],

            "elapsed_s":
                int(elapsed),

            "avg_runtime_s":
                avg_runtime,

            "avg_simulation_time_ns":
                (
                    sum(stats["simulation_times"])
                    / len(stats["simulation_times"])
                )
                if stats["simulation_times"]
                else 0,

            "min_simulation_time_ns":
                min(stats["simulation_times"])
                if stats["simulation_times"]
                else 0,

            "max_simulation_time_ns":
                max(stats["simulation_times"])
                if stats["simulation_times"]
                else 0,

            "saved_percent":
                (
                    100
                    * (
                        1
                        - (
                            (
                                sum(stats["simulation_times"])
                                / len(stats["simulation_times"])
                            )
                            / MAX_SIM_TIME_NS
                        )
                    )
                )
                if stats["simulation_times"]
                else 0,

            "gpu_count":
                len(GPU_IDS),

            "gpu_list":
                ";".join(
                    str(g)
                    for g in GPU_IDS
                ),

            "cache_enabled":
                ENABLE_CACHE,
        }

        os.makedirs(
            "results",
            exist_ok=True,
        )

        file_exists = os.path.exists(
            RUN_SUMMARY_FILE
        )

        with open(
                RUN_SUMMARY_FILE,
                "a",
                newline="") as f:

            writer = csv.DictWriter(
                f,
                fieldnames=
                    run_summary.keys()
            )

            if not file_exists:
            
                writer.writeheader()

            writer.writerow(
                run_summary
            )

        ##############################################################
        # AUTOPLOT PATHS
        ##############################################################

        run_name = (
            f"{pulse_ns:.4f}ns_"
            f"{temperature_K}K_"
            f"{current_A*1000:.3f}mA"
        )

        tables_folder = os.path.join(
            TABLES_DIR,
            run_name
        )

        plots_folder = os.path.join(
            PLOTS_DIR,
            run_name
        )

        os.makedirs(
            plots_folder,
            exist_ok=True
        )

        plot_base = (
            f"autoplot_"
            f"{MACHINE_ID}_"
            f"{SIM_PROTOCOL}_"
            f"{pulse_ns:.4f}ns_"
            f"{temperature_K}K_"
            f"{current_A*1000:.3f}mA"
        )

        output_png = os.path.join(
            plots_folder,
            plot_base + ".png"
        )

        output_pdf = os.path.join(
            plots_folder,
            plot_base + ".pdf"
        )

        ##############################################################
        # AUTOPLOT
        ##############################################################

        try:

            create_autoplot(
            
                tables_folder=tables_folder,

                output_png=output_png,

                output_pdf=output_pdf,

                pulse_ns=pulse_ns,

                temperature_K=temperature_K,

                current_mA=current_A * 1000,

                pulse_start_ns=1.0,

                pulse_end_ns=1.0 + pulse_ns,

                threshold=MEASUREMENT_THRESHOLD,

                machine=MACHINE,

                protocol=SIM_PROTOCOL,
            )

        except Exception as e:

            print(
                f'AUTOPLOT FAILED: {e}'
            )

        ##############################################################
        # UPDATE OVERALL STATS
        ##############################################################

        overall["completed"] += (
            stats["completed"]
        )

        overall["simulated"] += (
            stats["simulated"]
        )

        overall["cached"] += (
            stats["cached"]
        )

        overall["failed"] += (
            stats["failed"]
        )

        overall["switched"] += (
            stats["switched"]
        )

        overall["not_switched"] += (
            stats["not_switched"]
        )

        overall["invalid"] += (
            stats["invalid"]
        )

        overall["early_stable"] += (
            stats["early_stable"]
        )

        overall["max_time"] += (
            stats["max_time"]
        )

        overall["mumax_error"] += (
            stats["mumax_error"]
        )

        overall["runtime"] += (
            stats["runtime"]
        )

        overall["simulation_times"].extend(
            stats["simulation_times"]
        )

        ##############################################################
        # ROW SUMMARY
        ##############################################################
        avg_sim_time = (
            sum(stats["simulation_times"])
            / len(stats["simulation_times"])
            if stats["simulation_times"]
            else 0
        )

        min_sim_time = (
            min(stats["simulation_times"])
            if stats["simulation_times"]
            else 0
        )

        max_sim_time = (
            max(stats["simulation_times"])
            if stats["simulation_times"]
            else 0
        )

        saved_percent = (
            100
            * (1 - avg_sim_time / MAX_SIM_TIME_NS)
            if stats["simulation_times"]
            else 0
        )

        print()
        print(format_title("=" * 70))
        print(
            format_title(    
                f"ROW {row_index+1}/{total_rows} SUMMARY"
            )
        )
        print(format_title("=" * 70))

        print()
        print("Runs")
        print("-" * 70)
        print(
            f"Completed={stats['completed']} | "
            f"Simulated={stats['simulated']} | "
            f"Cached={stats['cached']} | "
            f"Failed={stats['failed']}"
        )

        print()
        print("Termination")
        print("-" * 70)
        print(
            f"Early Stable={stats['early_stable']} | "
            f"Max Time={stats['max_time']} | "
            f"Errors={stats['mumax_error']}"
        )

        print()
        print("Classification")
        print("-" * 70)
        print(
            f"Switched={stats['switched']} ({psw:.3f}%) | "
            f"Not switched={stats['not_switched']} ({pnot:.3f}%) | "
            f"Invalid={stats['invalid']} ({pinv:.3f}%)"
        )

        print()
        print("Simulation")
        print("-" * 70)
        print(
            f"Avg={avg_sim_time:.2f}ns | "
            f"Min={min_sim_time:.2f}ns | "
            f"Max={max_sim_time:.2f}ns | "
            f"Saved={saved_percent:.1f}%"
        )

        print()
        print("Runtime")
        print("-" * 70)
        print(
            f"Elapsed={timedelta(seconds=int(elapsed))} | "
            f"Avg Runtime={avg_runtime:.1f}s"
        )

    ##############################################################
    # FINAL SUMMARY
    ##############################################################

    total_elapsed = (
        time.time()
        - global_start
    )

    if overall["simulated"] > 0:

        overall_avg_runtime = (
            overall["runtime"]
            / overall["simulated"]
        )

    else:

        overall_avg_runtime = 0

    print()
    print(format_title("=" * 70))
    print(format_title("FINAL SUMMARY"))
    print(format_title("=" * 70))

    print()
    print("Runs")
    print("-" * 70)
    print(
        f"Completed={overall['completed']} | "
        f"Simulated={overall['simulated']} | "
        f"Cached={overall['cached']} | "
        f"Failed={overall['failed']}"
    )

    print()
    print("Runtime")
    print("-" * 70)
    print(
        f"Elapsed={timedelta(seconds=int(total_elapsed))} | "
        f"Avg Runtime={overall_avg_runtime:.1f}s"
    )

    if overall["failed"] > 0:

        print()
        print("CHECK ERROR LOG")

    print()
    print("=" * 70)

if __name__ == "__main__":
    main()