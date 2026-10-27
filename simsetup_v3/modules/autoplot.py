# modules/autoplot.py
#
# Creates an overlay mz(t) plot for all iterations of a sweep point.
#
# Output:
#   autoplot_<machine>_<protocol>_<pulse>ns_<temp>K_<current>mA.png
#   autoplot_<machine>_<protocol>_<pulse>ns_<temp>K_<current>mA.pdf
#

from pathlib import Path
import glob

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

import re


def get_specific_table_files(
    tables_folder,
    seed_list,
):
    """
    Return only the table files corresponding to the
    requested seed numbers.
    """

    tables_folder = Path(tables_folder)

    table_files = sorted(
        glob.glob(
            str(tables_folder / "*")
        )
    )

    selected = []

    seed_set = set(seed_list)

    for table_file in table_files:

        match = re.search(
            r"seed(\d+)",
            Path(table_file).name,
        )

        if match is None:
            continue

        seed = int(match.group(1))

        if seed in seed_set:
            selected.append(table_file)

    return selected

def create_autoplot(
    tables_folder,
    output_png,
    output_pdf,
    pulse_ns,
    temperature_K,
    current_mA,
    pulse_start_ns,
    pulse_end_ns,
    threshold,
    machine="DGX",
    protocol="v1",
):
    """
    Automatically generates an overlay mz(t) plot for one sweep point.

    Parameters
    ----------
    tables_folder : str/path
        Folder containing mumax table files.

    output_png : str/path
        Output PNG filename.

    output_pdf : str/path
        Output PDF filename.

    pulse_ns : float
    temperature_K : int
    current_mA : float

    pulse_start_ns : float
    pulse_end_ns : float

    threshold : float
        Classification threshold.

    machine : str
        DGX / LAPTOP / 4070 etc.

    protocol : str
        Simulation protocol version.
    """

    tables_folder = Path(tables_folder)

    print()
    print("========== AUTOPLOT ==========")
    print("tables_folder =", tables_folder)
    print("exists        =", tables_folder.exists())
    print("is_dir        =", tables_folder.is_dir())
    
    table_files = sorted(
        glob.glob(
            str(tables_folder / "*")
        )
    )
    
    print("n_files       =", len(table_files))
    
    if len(table_files):
        print("first file    =", table_files[0])
    
    print("==============================")
    print()

    #print()
    #print("========== AUTOPLOT DEBUG ==========")
    #print("tables folder :", tables_folder)
    #print("exists        :", tables_folder.exists())
    #print("num files     :", len(table_files))
#
    #if len(table_files):
    #    print("first file    :", table_files[0])
#
    #print("====================================")
    #print()

    switched = 0
    unswitched = 0
    invalid = 0

    fig = plt.figure(
        figsize=(14, 10)
    )

    gs = GridSpec(
        2,
        1,
        height_ratios=[5, 2],
        hspace=0.25,
    )

    ax = fig.add_subplot(gs[0])

    ##############################################################
    # PLOT ALL TABLES
    ##############################################################

    for table_file in table_files:

        #print("reading:", table_file)

        try:
        
            df = pd.read_csv(
                table_file,
                sep=r"\s+",
                comment="#",
                header=None,
            )

        except Exception as e:
        
            print(f"AUTOPLOT PARSE ERROR: {table_file}")
            print(e)
            continue
        
        if len(df) == 0:
            continue
        
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

            mz = df["mz2"]

        elif ncols == 4:
        
            df.columns = [
                "t",
                "mx",
                "my",
                "mz",
            ]

            mz = df["mz"]

        else:
        
            print(
                f"AUTOPLOT BAD TABLE: "
                f"{table_file} "
                f"({ncols} columns)"
            )

            continue
        
        t_ns = df["t"] * 1e9

        final_mz = mz.iloc[-1]

        ##########################################################
        # CLASSIFY
        ##########################################################

        if final_mz < -threshold:

            linestyle = "-"
            switched += 1

        elif final_mz > threshold:

            linestyle = "--"
            unswitched += 1

        else:

            linestyle = ":"
            invalid += 1

        ##########################################################
        # PLOT
        ##########################################################

        ax.plot(
            t_ns,
            mz,
            linestyle=linestyle,
            linewidth=0.8,
        )

    ##############################################################
    # STATISTICS
    ##############################################################

    total = (
        switched
        + unswitched
        + invalid
    )

    if total > 0:

        psw = switched / total
        punsw = unswitched / total
        pinvalid = invalid / total

    else:

        psw = 0
        punsw = 0
        pinvalid = 0

    ##############################################################
    # PULSE REGION
    ##############################################################

    ax.axvspan(
        pulse_start_ns,
        pulse_end_ns,
        alpha=0.20,
    )

    ##############################################################
    # THRESHOLDS
    ##############################################################

    ax.axhline(
        threshold,
        linewidth=1,
    )

    ax.axhline(
        -threshold,
        linewidth=1,
    )

    ##############################################################
    # AXES
    ##############################################################

    ax.set_xlabel(
        "Time (ns)"
    )

    ax.set_ylabel(
        "m$_z$"
    )

    ax.set_ylim(
        [-1.1, 1.1]
    )

    ax.grid(True)

    ##############################################################
    # TITLE
    ##############################################################

    
    title = (
        f"AUTOPLOT | {machine} | "
        f"protocol={protocol}\n"
        f"solid=switched | "
        f"dashed=unswitched | "
        f"dotted=invalid\n"
        f"pulse={pulse_ns:.4f} ns    "
        f"T={temperature_K} K    "
        f"I={current_mA:.3f} mA\n"
        f"Psw={100*psw:.3f}%"
    )

    ax.set_title(
        title
    )

    ##############################################################
    # SUMMARY TABLE
    ##############################################################

    ax2 = fig.add_subplot(
        gs[1]
    )

    ax2.axis("off")
    ax2.set_anchor("N")

    table_data = [

        [
            "Iterations",
            total
        ],

        [
            "Switched",
            switched
        ],

        [
            "Not switched",
            unswitched
        ],

        [
            "Invalid",
            invalid
        ],

        [
            "Psw",
            f"{100*psw:.3f}%"
        ],

        [
            "Pnot",
            f"{100*punsw:.3f}%"
        ],

        [
            "Pinvalid",
            f"{100*pinvalid:.3f}%"
        ],

        [
            "Threshold",
            threshold
        ],

        [
            "Machine",
            machine
        ],

        [
            "Protocol",
            protocol
        ],
    ]

    table = ax2.table(
        cellText=table_data,
        colLabels=[
            "Parameter",
            "Value",
        ],
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(
        False
    )

    table.set_fontsize(
        10
    )

    table.scale(
        1,
        1.5,
    )

    ##############################################################
    # BLACK HEADER
    ##############################################################

    for i in range(2):

        cell = table[(0, i)]

        cell.set_facecolor(
            "black"
        )

        cell.get_text().set_color(
            "white"
        )

    plt.tight_layout()

    ##############################################################
    # SAVE
    ##############################################################

    plt.savefig(
        output_png,
        dpi=300,
        bbox_inches="tight",
    )


#    plt.savefig(
#        output_pdf,
#        bbox_inches="tight",
#    )

    
    plt.close(fig)

    ##############################################################
    # PRINT
    ##############################################################

    run_name = (
        f"{pulse_ns:.4f}ns_"
        f"{temperature_K}K_"
        f"{current_mA:.3f}mA"
    )
    print()
    print(
        f'Plot generated for "{run_name}"'
    )

def create_autoplot_specific(
    tables_folder,
    seed_list,
    output_png,
    output_pdf,
    pulse_ns,
    temperature_K,
    current_mA,
    pulse_start_ns,
    pulse_end_ns,
    threshold,
    machine="DGX",
    protocol="v1",
    total_time_ns = 10,
):
    """
    Automatically generates an overlay mz(t) plot for one sweep point.

    Parameters
    ----------
    tables_folder : str/path
        Folder containing mumax table files.

    output_png : str/path
        Output PNG filename.

    output_pdf : str/path
        Output PDF filename.

    pulse_ns : float
    temperature_K : int
    current_mA : float

    pulse_start_ns : float
    pulse_end_ns : float

    threshold : float
        Classification threshold.

    machine : str
        DGX / LAPTOP / 4070 etc.

    protocol : str
        Simulation protocol version.
    """

    tables_folder = Path(tables_folder)

    print()
    print("========== AUTOPLOT ==========")
    print("tables_folder =", tables_folder)
    print("exists        =", tables_folder.exists())
    print("is_dir        =", tables_folder.is_dir())
    
    table_files = get_specific_table_files(
        tables_folder,
        seed_list,
    )
    
    print("n_files       =", len(table_files))
    
    if len(table_files):
        print("first file    =", table_files[0])
    
    print("==============================")
    print()

#    print()
#    print("========== AUTOPLOT DEBUG ==========")
#    print("tables folder :", tables_folder)
#    print("exists        :", tables_folder.exists())
#    print("num files     :", len(table_files))
#
#    if len(table_files):
#        print("first file    :", table_files[0])
#
#    print("====================================")
#    print()

    switched = 0
    unswitched = 0
    invalid = 0

    fig = plt.figure(
        figsize=(14, 10)
    )

    gs = GridSpec(
        2,
        1,
        height_ratios=[5, 2],
        hspace=0.25,
    )

    ax = fig.add_subplot(gs[0])

    ##############################################################
    # PLOT ALL TABLES
    ##############################################################

    for table_file in table_files:

        #print("reading:", table_file)

        try:
        
            df = pd.read_csv(
                table_file,
                sep=r"\s+",
                comment="#",
                header=None,
            )

        except Exception as e:
        
            print(f"AUTOPLOT PARSE ERROR: {table_file}")
            print(e)
            continue
        
        if len(df) == 0:
            continue
        
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

            mz = df["mz2"]

        elif ncols == 4:
        
            df.columns = [
                "t",
                "mx",
                "my",
                "mz",
            ]

            mz = df["mz"]

        else:
        
            print(
                f"AUTOPLOT BAD TABLE: "
                f"{table_file} "
                f"({ncols} columns)"
            )

            continue
        
        t_ns = df["t"] * 1e9

        final_mz = mz.iloc[-1]

        ##########################################################
        # CLASSIFY
        ##########################################################

        if final_mz < -threshold:

            linestyle = "-"
            switched += 1

        elif final_mz > threshold:

            linestyle = "--"
            unswitched += 1

        else:

            linestyle = ":"
            invalid += 1

        ##########################################################
        # PLOT
        ##########################################################

        ax.plot(
            t_ns,
            mz,
            linestyle=linestyle,
            linewidth=0.8,
        )

    ##############################################################
    # STATISTICS
    ##############################################################

    total = (
        switched
        + unswitched
        + invalid
    )

    if total > 0:

        psw = switched / total
        punsw = unswitched / total
        pinvalid = invalid / total

    else:

        psw = 0
        punsw = 0
        pinvalid = 0

    ##############################################################
    # PULSE REGION
    ##############################################################

    ax.axvspan(
        pulse_start_ns,
        pulse_end_ns,
        alpha=0.20,
    )

    ##############################################################
    # THRESHOLDS
    ##############################################################

    ax.axhline(
        threshold,
        linewidth=1,
    )

    ax.axhline(
        -threshold,
        linewidth=1,
    )

    ##############################################################
    # AXES
    ##############################################################

    ax.set_xlabel(
        "Time (ns)"
    )

    ax.set_ylabel(
        "m$_z$"
    )

    ax.set_ylim(
        [-1.1, 1.1]
    )

    ax.grid(True)

    ##############################################################
    # TITLE
    ##############################################################

    title = (
        f"AUTOPLOT (SPECIFIC) | {machine} | "
        f"protocol={protocol}\n"
        f"solid=switched | "
        f"dashed=unswitched | "
        f"dotted=invalid\n"
        f"pulse={pulse_ns:.4f} ns    "
        f"T={temperature_K} K    "
        f"I={current_mA:.3f} mA\n"
        f"no. of seeds={len(seed_list)}    "
        f"Total time={total_time_ns:.3f} ns\n"
        f"Psw={100*psw:.3f}%"
    )

    ax.set_title(
        title
    )

    ##############################################################
    # SUMMARY TABLE
    ##############################################################

    ax2 = fig.add_subplot(
        gs[1]
    )

    ax2.axis("off")
    ax2.set_anchor("N")

    table_data = [

        [
            "Iterations",
            total
        ],

        [
            "Switched",
            switched
        ],

        [
            "Not switched",
            unswitched
        ],

        [
            "Invalid",
            invalid
        ],

        [
            "Psw",
            f"{100*psw:.3f}%"
        ],

        [
            "Pnot",
            f"{100*punsw:.3f}%"
        ],

        [
            "Pinvalid",
            f"{100*pinvalid:.3f}%"
        ],

        [
            "Threshold",
            threshold
        ],

        [
            "Machine",
            machine
        ],

        [
            "Protocol",
            protocol
        ],
    ]

    table = ax2.table(
        cellText=table_data,
        colLabels=[
            "Parameter",
            "Value",
        ],
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(
        False
    )

    table.set_fontsize(
        10
    )

    table.scale(
        1,
        1.5,
    )

    ##############################################################
    # BLACK HEADER
    ##############################################################

    for i in range(2):

        cell = table[(0, i)]

        cell.set_facecolor(
            "black"
        )

        cell.get_text().set_color(
            "white"
        )

    plt.tight_layout()

    ##############################################################
    # SAVE
    ##############################################################

    plt.savefig(
        output_png,
        dpi=300,
        bbox_inches="tight",
    )


#    plt.savefig(
#        output_pdf,
#        bbox_inches="tight",
#    )

    
    plt.close(fig)

    ##############################################################
    # PRINT
    ##############################################################

    run_name = (
        f"{pulse_ns:.4f}ns_"
        f"{temperature_K}K_"
        f"{current_mA:.3f}mA"
    )
    print()
    print(
        f'Plot generated for specific seeds "{run_name}"'
    )