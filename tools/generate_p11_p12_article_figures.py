"""Render P11/P12 article figures from the checked-in experiment records."""

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/p11-p12-article"
CLASSICAL = ROOT / "classical_simulations/p11_p12"
BACKGROUND = "#f8f7f3"
INK = "#172b3d"
MUTED = "#4e5f6b"
GRID = "#d6dcd9"
COLORS = {"P11": "#22628a", "P12": "#0a7866"}
ORANGE = "#ae4b26"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "figure.facecolor": BACKGROUND,
    "axes.facecolor": BACKGROUND,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "text.color": INK,
    "savefig.facecolor": BACKGROUND,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def read_json(path):
    return json.loads(path.read_text())


def heading(fig, label, title, description):
    fig.text(0.075, 0.94, label, fontsize=10, color=ORANGE, weight="bold")
    fig.text(0.075, 0.865, title, fontsize=23, weight="bold")
    fig.text(0.075, 0.811, description, fontsize=11, color=MUTED)


def save(fig, name, note):
    fig.text(0.075, 0.042, note, fontsize=9, color=MUTED)
    fig.savefig(OUTPUT / f"{name}.png", dpi=170)
    plt.close(fig)


def hardware(cores):
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.3), sharex=True)
    fig.subplots_adjust(left=0.105, right=0.94, top=0.755, bottom=0.16, hspace=0.44)
    heading(fig, "01   /   HELIOS-1 HARDWARE", "The accepted string was rarely sampled",
            "Hamming distance counts how many bits differ from the accepted 98-bit answer.")

    for ax, (circuit, core) in zip(axes, cores.items(), strict=True):
        raw = ROOT / "results/tracker_submissions" / circuit.lower() / "classical/raw"
        counts_record = read_json(next(raw.glob("*counts.json")))
        counts = counts_record.get("counts", counts_record)
        distances = Counter()
        for bits, multiplicity in counts.items():
            distance = sum(a != b for a, b in zip(bits, core["peak"], strict=True))
            distances[distance] += multiplicity
        n = sum(counts.values())
        exact = distances[0]
        ax.bar(list(distances), [100 * k / n for k in distances.values()],
               width=0.83, color=[ORANGE if d == 0 else COLORS[circuit] for d in distances])
        ax.set(xlim=(-1.8, 62.5), ylim=(0, 9.5), yticks=[0, 4, 8])
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=GRID, linewidth=0.7)
        ax.set_title(f"{circuit}   ·   {n} shots   ·   {len(counts)} distinct strings",
                     loc="left", fontsize=12, weight="bold")
        ax.annotate(f"{exact} exact {'match' if exact == 1 else 'matches'}",
                    xy=(0, 100 * exact / n), xytext=(4, 6.3), color=ORANGE,
                    arrowprops={"arrowstyle": "-", "color": ORANGE}, fontsize=10)
    axes[-1].set_xlabel("Hamming distance to the accepted answer")
    save(fig, "01-hardware-distances",
         "Corrected hardware counts. Distances are computed after recovery, using the accepted answer as the reference.")


def structure():
    fig = plt.figure(figsize=(10, 5.7))
    heading(fig, "02   /   CIRCUIT STRUCTURE", "What the classical solver keeps",
            "Surviving inverse rotations expose mirror blocks inside the long middle section.")
    ax = fig.add_axes([0.075, 0.17, 0.86, 0.56])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")

    def block(x, y, w, label, fill):
        ax.add_patch(FancyBboxPatch((x, y), w, 0.22,
                                  boxstyle="round,pad=0.008,rounding_size=0.017",
                                  fc=fill, ec="none"))
        ax.text(x + w / 2, y + 0.11, label, ha="center", va="center",
                fontsize=11, weight="bold")

    ax.text(0, 0.91, "PUBLISHED CIRCUIT", color=MUTED, weight="bold", fontsize=9)
    block(0.01, 0.61, 0.17, "Prefix R", "#dcebf3")
    block(0.21, 0.61, 0.56, "Obfuscated middle with nested mirror blocks", "#f0dfd4")
    block(0.80, 0.61, 0.19, "Suffix P", "#dcebf3")
    ax.annotate("", xy=(0.49, 0.33), xytext=(0.49, 0.58),
                arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": ORANGE})
    ax.text(0.515, 0.46, "Infer wire mapping from inverse pairs", va="center", color=ORANGE)
    ax.text(0, 0.39, "REDUCED MODEL", color=MUTED, weight="bold", fontsize=9)
    block(0.01, 0.055, 0.28, "Prefix + frontier gates", "#dcebf3")
    block(0.32, 0.055, 0.33, "Wire permutation", "#dbede7")
    block(0.68, 0.055, 0.31, "Suffix", "#dcebf3")
    save(fig, "02-structural-reduction",
         "Schematic, with widths drawn for readability. The permutation approximates the obfuscated middle.")


def repair(cores):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    fig.subplots_adjust(left=0.105, right=0.90, top=0.74, bottom=0.18)
    heading(fig, "03   /   BOUNDARY SEARCH", "A few frontier gates changed the core",
            "Each point scores that reduced model’s candidate using its exact contracted amplitude.")
    for circuit, core in cores.items():
        stages = [core["initial_core_probability"]] + [r["probability"] for r in core["repairs"]]
        ax.plot(range(len(stages)), [100 * p for p in stages], marker="o", ms=8,
                linewidth=2.5, color=COLORS[circuit])
        gates = ["Initial"] + [f"Gate {r['gate']}" for r in core["repairs"]]
        for stage, (probability, gate) in enumerate(zip(stages, gates, strict=True)):
            label = f"{circuit}  {100 * probability:.2f}%" if stage == 0 else f"{gate}  ·  {100 * probability:.2f}%"
            rising_from_point = stage < len(stages) - 1
            offset = (-7, 9) if rising_from_point else (0, 11)
            align = "right" if rising_from_point else "center"
            if stage == 0:
                offset = (0, -18) if circuit == "P11" else (0, 11)
                align = "center"
            ax.annotate(label, (stage, 100 * probability), xytext=offset,
                        textcoords="offset points", ha=align,
                        fontsize=10, weight="bold", color=COLORS[circuit])
    ax.set(xlim=(-0.23, 2.26), ylim=(0, 36), xticks=[0, 1, 2],
           xticklabels=["Initial core", "First move", "Second move"],
           ylabel="Candidate probability")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    save(fig, "03-boundary-repair",
         "Each score applies to the reduced core at that step. The candidate can change between steps.")


def runtime():
    fig, ax = plt.subplots(figsize=(10, 5.1))
    fig.subplots_adjust(left=0.18, right=0.91, top=0.742, bottom=0.205)
    heading(fig, "04   /   SAME-SEARCH BENCHMARK", "Caching made both solves about 3× faster",
            "The same deterministic search on a MacBook M3 Pro, with and without caches.")
    records = read_json(CLASSICAL / "benchmark-summary.json")["results"]
    for idx, result in enumerate(records):
        cached = result["solver_seconds"]
        uncached = result["uncached_solver_seconds"]
        color = COLORS[result["circuit"]]
        ax.barh(idx - 0.18, uncached, color="#cbd7dc", height=0.27)
        ax.barh(idx + 0.18, cached, color=color, height=0.27)
        ax.text(uncached + 1.6, idx - 0.18, f"Uncached  ·  {uncached:.1f} s",
                va="center", fontsize=10)
        ax.text(cached + 1.6, idx + 0.18, f"Cached  ·  {cached:.1f} s  ·  {result['speedup_vs_same_search_uncached']:.2f}×",
                va="center", fontsize=10, weight="bold", color=color)
    ax.set(xlim=(0, 112), yticks=range(len(records)),
           yticklabels=[row["circuit"] for row in records], xlabel="Solver time (seconds)")
    ax.invert_yaxis()
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    save(fig, "04-caching-benchmark",
         "One run per setting. Solve times exclude imports, numerical certification, and extra cache validation.")


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cores = {circuit: read_json(CLASSICAL / f"results/{circuit}.json")
             for circuit in ("P11", "P12")}
    hardware(cores)
    structure()
    repair(cores)
    runtime()
