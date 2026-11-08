"""Build measured-data illustrations and LaTeX equations for the P11/P12 article."""

import json
import subprocess
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/p11-p12-article"
CLASSICAL = ROOT / "classical_simulations/p11_p12"
PAPER = "#fbfaf7"
INK = "#172d3a"
MUTED = "#586974"
GRID = "#dce3e3"
BLUE = "#286a98"
TEAL = "#087d76"
CORAL = "#bd563b"
PALE_BLUE = "#d9e9f2"
PALE_TEAL = "#d7eae4"
COLORS = {"P11": BLUE, "P12": TEAL}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": INK,
    "axes.labelcolor": MUTED,
    "axes.edgecolor": GRID,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "mathtext.fontset": "stix",
})


def read_json(path):
    return json.loads(path.read_text())


def load_records():
    records = {}
    benchmark = read_json(CLASSICAL / "benchmark-summary.json")
    for row in benchmark["results"]:
        name = row["circuit"]
        core = read_json(CLASSICAL / f"results/{name}.json")
        directory = ROOT / "results/tracker_submissions" / name.lower() / "classical"
        counts_record = read_json(next((directory / "raw").glob("*counts.json")))
        counts = counts_record.get("counts", counts_record)
        candidates = read_json(directory / "runtime_audit.json")["candidates"]
        sections = core["sections"]
        prefix = sections[0][1] - sections[0][0] + 1
        suffix = sections[-1][1] - sections[-1][0] + 1
        records[name] = {
            "core": core,
            "benchmark": row,
            "counts": counts,
            "candidates": candidates,
            "prefix": prefix,
            "suffix": suffix,
            "core_units": prefix + suffix + len(core["repairs"]),
            "full_units": sections[-1][1] + 1,
        }
    return records


def heading(fig, kicker, title, subtitle):
    fig.text(0.075, 0.945, kicker, color=TEAL, fontsize=10, weight="bold")
    fig.text(0.075, 0.862, title, fontsize=22, weight="bold")
    fig.text(0.075, 0.795, textwrap.fill(subtitle, width=112),
             fontsize=10.5, color=MUTED, linespacing=1.4)


def save(fig, name, note):
    fig.text(0.075, 0.042, note, fontsize=9, color=MUTED)
    fig.savefig(OUTPUT / f"{name}.png", dpi=180)
    plt.close(fig)


def distances(record):
    peak = record["core"]["peak"]
    result = Counter()
    for bits, count in record["counts"].items():
        result[sum(a != b for a, b in zip(bits, peak, strict=True))] += count
    return result


def hero(records):
    fig = plt.figure(figsize=(11, 7))
    fig.text(0.065, 0.935, "PEAKED CIRCUITS  /  P11 + P12", color=TEAL,
             fontsize=11, weight="bold")
    fig.text(0.065, 0.847, "Two 98-qubit peaks.", fontsize=30, weight="bold")
    fig.text(0.065, 0.777, "Two routes to the same answers.", fontsize=25)
    fig.text(0.065, 0.684, "QUANTUM", fontsize=12, weight="bold", color=BLUE)
    fig.text(0.565, 0.684, "CLASSICAL", fontsize=12, weight="bold", color=TEAL)
    fig.text(0.065, 0.636, "Run the circuit. Decode the noisy shots.", fontsize=12)
    fig.text(0.565, 0.636, "Expose the mirror. Contract the core.", fontsize=12)
    left = fig.add_axes([0.075, 0.395, 0.35, 0.19])
    for name, record in records.items():
        dist = distances(record)
        n = sum(dist.values())
        cumulative = np.cumsum([dist[d] for d in range(99)]) / n * 100
        left.step(range(99), cumulative, where="post", color=COLORS[name],
                  lw=2.2, label=f"{name} · {n} shots")
    left.set(xlim=(0, 98), ylim=(0, 104), yticks=[0, 50, 100], xticks=[0, 49, 98],
             xlabel="Bit differences from the accepted answer", ylabel="Shots within distance (%)")
    left.tick_params(labelsize=9)
    left.xaxis.label.set_size(9)
    left.yaxis.label.set_size(9)
    left.legend(loc="upper left", fontsize=8, frameon=False)
    right = fig.add_axes([0.565, 0.395, 0.36, 0.19])
    for i, (name, record) in enumerate(records.items()):
        total = record["full_units"]
        core = record["core_units"]
        right.barh(i, total, height=0.5, color="#d9e0e1")
        right.barh(i, core, height=0.5, color=COLORS[name])
        right.text(core + 60, i, f"{core:,} retained / {total:,} published",
                   va="center", fontsize=9, color=INK)
    right.set(yticks=[0, 1], yticklabels=["P11", "P12"], xlim=(0, 2600),
              xticks=[0, 1000, 2000], xlabel="Two-qubit units in each circuit model")
    right.invert_yaxis()
    right.tick_params(labelsize=9)
    right.xaxis.label.set_size(9)
    fig.patches.append(FancyArrowPatch((0.48, 0.64), (0.48, 0.30),
                                      transform=fig.transFigure, arrowstyle="-",
                                      color=GRID, linewidth=1))
    fig.text(0.065, 0.265, "Both routes recover the same 98 bits for each instance.",
             fontsize=14, weight="bold")
    for i, (name, record) in enumerate(records.items()):
        ax = fig.add_axes([0.14, 0.187 - i * 0.054, 0.75, 0.027])
        bits = np.array([int(bit) for bit in record["core"]["peak"]])[None, :]
        ax.imshow(bits, aspect="auto", interpolation="nearest",
                  cmap=ListedColormap(["#e2e7e5", COLORS[name]]), vmin=0, vmax=1)
        ax.set_xticks(np.arange(-0.5, 98, 1), minor=True)
        ax.grid(which="minor", axis="x", color=PAPER, linewidth=1)
        ax.tick_params(which="both", bottom=False, left=False,
                       labelbottom=False, labelleft=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.text(0.065, 0.19 - i * 0.054, name, fontsize=11, weight="bold")
    save(fig, "00-project-overview",
         "Measured hardware counts and inferred reduced-core sizes. Each bottom strip shows the actual accepted bitstring.")


def hardware(records):
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True)
    fig.subplots_adjust(left=0.105, right=0.93, top=0.70, bottom=0.16, hspace=0.52)
    heading(fig, "QUANTUM  /  THE MEASUREMENTS", "Where did the hardware shots land?",
            "One exact-match bar, followed by five-bit distance bins. All corrected shots are included.")
    bins = [(start, min(start + 4, 98)) for start in range(1, 99, 5)]
    for ax, (name, record) in zip(axes, records.items(), strict=True):
        dist = distances(record)
        n = sum(dist.values())
        centers = [(lo + hi) / 2 for lo, hi in bins]
        heights = [sum(dist[d] for d in range(lo, hi + 1)) for lo, hi in bins]
        ax.bar(centers, heights, width=4.35, color=COLORS[name], zorder=3)
        ax.bar(0, dist[0], width=1.5, color=CORAL, zorder=4)
        ax.set(xlim=(-2, 99), ylabel="Number of shots")
        ax.grid(axis="y", color=GRID, zorder=0)
        ax.set_title(f"{name}   ·   {n} shots   ·   {len(record['counts'])} distinct strings",
                     loc="left", fontsize=12, weight="bold", pad=14)
        ax.annotate(f"{dist[0]} exact / {n}", xy=(0, dist[0]),
                    xytext=(9, max(heights) * 0.66), fontsize=11, color=CORAL,
                    arrowprops={"arrowstyle": "-", "color": CORAL})
        ax.set_ylim(0, max(heights) * 1.22)
    axes[-1].set_xlabel("Hamming distance from the accepted 98-bit answer")
    axes[-1].set_xticks([0, 20, 40, 60, 80, 98])
    save(fig, "01-hardware-distances",
         "Distances use the accepted answer after recovery. Bins preserve every recorded count. Last bin spans distances 96–98.")


def decoder_bits(records):
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.4))
    fig.subplots_adjust(left=0.24, right=0.84, top=0.68, bottom=0.24, hspace=1.1)
    heading(fig, "QUANTUM  /  THE DECODERS", "Which bits did each decoder recover?",
            "Each cell is one output bit, compared with the accepted answer after decoding.")
    methods = ["bitwise_majority", "weighted_observed_medoid", "cluster_consensus"]
    labels = ["All-shot majority", "Observed medoid", "Cluster consensus"]
    for ax, (name, record) in zip(axes, records.items(), strict=True):
        peak = record["core"]["peak"]
        wrong = np.array([[a != b for a, b in zip(record["candidates"][method], peak, strict=True)]
                          for method in methods])
        ax.imshow(wrong, aspect="auto", interpolation="nearest",
                  cmap=ListedColormap([PALE_TEAL, CORAL]), vmin=0, vmax=1)
        ax.set(yticks=[0, 1, 2], yticklabels=labels, xticks=[0, 19, 39, 59, 79, 97],
               xticklabels=["0", "19", "39", "59", "79", "97"], xlabel="Qubit index")
        ax.tick_params(axis="both", length=0, labelsize=10)
        ax.set_title(name, loc="left", fontsize=12, weight="bold", pad=9, color=COLORS[name])
        for i, errors in enumerate(wrong.sum(axis=1)):
            ax.text(100, i, f"{errors} bits differ", va="center", fontsize=10,
                    color=CORAL if errors else TEAL)
        ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
        ax.grid(which="minor", axis="y", color=PAPER, linewidth=5)
        ax.tick_params(which="minor", left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.text(0.24, 0.095, "Pale green  ·  agrees", fontsize=10, color=TEAL)
    fig.text(0.49, 0.095, "Coral  ·  differs", fontsize=10, color=CORAL)
    save(fig, "05-decoder-bits",
         "Candidates are taken from the archived deterministic reanalysis. The accepted answer is used only for this comparison.")


def structure(records):
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.4))
    fig.subplots_adjust(left=0.16, right=0.94, top=0.70, bottom=0.18, hspace=0.8)
    heading(fig, "CLASSICAL  /  STRUCTURAL REDUCTION", "A smaller core behind the obfuscation",
            "Bar lengths count atomic two-qubit units. The reduced model retains the prefix, suffix, and repairs.")
    for ax, (name, record) in zip(axes, records.items(), strict=True):
        prefix, suffix = record["prefix"], record["suffix"]
        full = record["full_units"]
        middle = full - prefix - suffix
        core = record["core_units"]
        ax.barh(0, prefix, color=COLORS[name], height=0.36)
        ax.barh(0, middle, left=prefix, color="#eed9cf", height=0.36)
        ax.barh(0, suffix, left=prefix + middle, color=COLORS[name], height=0.36)
        ax.barh(1, core, color=COLORS[name], height=0.36)
        ax.text(prefix + middle / 2, 0, "Obfuscated middle", ha="center",
                va="center", fontsize=10, color=CORAL)
        ax.text(full + 35, 0, f"{full:,}", va="center", fontsize=10, weight="bold")
        ax.text(core + 35, 1, f"{core} units retained", va="center", fontsize=10, weight="bold")
        ax.set(yticks=[0, 1], yticklabels=["Published QASM", "Reduced core"],
               xticks=[0, 500, 1000, 1500, 2000, 2500], xlim=(0, 2660), ylim=(1.5, -0.6))
        ax.tick_params(axis="y", length=0, labelsize=10)
        ax.tick_params(axis="x", labelsize=9)
        ax.set_title(f"{name}   ·   {record['core']['anchors']} inverse-pair anchors",
                     loc="left", fontsize=12, weight="bold", pad=10, color=COLORS[name])
        ax.spines["left"].set_visible(False)
    axes[-1].set_xlabel("Atomic two-qubit units")
    save(fig, "02-structural-reduction",
         "Middle-block replacement is an approximation. Counts describe the inferred core, including accepted frontier moves.")


def repair(records):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
    fig.subplots_adjust(left=0.10, right=0.94, top=0.68, bottom=0.20, wspace=0.25)
    heading(fig, "CLASSICAL  /  BOUNDARY REPAIR", "A few gates sharpen the reduced-core peak",
            "Columns score the candidate of each trial model. Both panels use the same probability scale.")
    for ax, (name, record) in zip(axes, records.items(), strict=True):
        core = record["core"]
        values = [core["initial_core_probability"]] + [r["probability"] for r in core["repairs"]]
        labels = ["Initial"] + [f"+ gate {r['gate']}" for r in core["repairs"]]
        bars = ax.bar(range(len(values)), np.array(values) * 100,
                      width=0.52, color=COLORS[name])
        for bar, value in zip(bars, values, strict=True):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.3,
                    f"{value:.2%}", ha="center", fontsize=11, weight="bold", color=COLORS[name])
        ax.set(xticks=range(len(values)), xticklabels=labels, ylim=(0, 37), yticks=[0, 10, 20, 30])
        ax.set_title(name, loc="left", fontsize=12, color=COLORS[name], weight="bold", pad=9)
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=GRID)
    axes[0].set_ylabel("Reduced-core candidate probability (%)", fontsize=10)
    save(fig, "03-boundary-repair",
         "The core and candidate can change between stages. These probabilities refer to the reduced models.")


def runtime(records):
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.4), gridspec_kw={"width_ratios": [1.25, 1]})
    fig.subplots_adjust(left=0.11, right=0.94, top=0.64, bottom=0.27, wspace=0.47)
    heading(fig, "CLASSICAL  /  REUSING THE WORK", "Unchanged causal cones can be cached",
            "Recorded MacBook M3 Pro runs of the same deterministic search, with caches switched off or on.")
    time_ax, reuse_ax = axes
    for idx, (name, record) in enumerate(records.items()):
        row = record["benchmark"]
        uncached, cached = row["uncached_solver_seconds"], row["solver_seconds"]
        time_ax.barh(idx - 0.18, uncached, height=0.27, color="#d4dddf")
        time_ax.barh(idx + 0.18, cached, height=0.27, color=COLORS[name])
        time_ax.text(uncached + 2, idx - 0.18, f"{uncached:.1f} s", va="center", fontsize=10)
        time_ax.text(cached + 2, idx + 0.18, f"{cached:.1f} s", va="center", fontsize=10, weight="bold")
        stats = record["core"]["statistics"]
        new, reused = stats["marginal_computations"], stats["marginal_cache_hits"]
        total = new + reused
        reuse_ax.barh(idx, new / total * 100, height=0.4, color="#d4dddf")
        reuse_ax.barh(idx, reused / total * 100, left=new / total * 100,
                      height=0.4, color=COLORS[name])
        reuse_ax.text(new / total * 100 + reused / total * 50, idx,
                      f"{reused / total:.1%}\nreused", color="white",
                      ha="center", va="center", fontsize=10, weight="bold")
    time_ax.set(yticks=[0, 1], yticklabels=["P11", "P12"], xlim=(0, 106), xticks=[0, 30, 60, 90],
                xlabel="Solver time (seconds)")
    reuse_ax.set(yticks=[0, 1], yticklabels=["P11", "P12"], xlim=(0, 100),
                 xticks=[0, 50, 100], xlabel="Requested marginals (%)")
    for ax in axes:
        ax.invert_yaxis()
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
    time_ax.set_title("Solve duration", loc="left", fontsize=12, weight="bold", pad=17)
    reuse_ax.set_title("Marginal reuse", loc="left", fontsize=12, weight="bold", pad=17)
    fig.text(0.11, 0.12, "Grey  ·  caches off / newly computed", fontsize=10, color=MUTED)
    fig.text(0.56, 0.12, "Colour  ·  caches on / reused", fontsize=10, color=MUTED)
    save(fig, "04-caching-benchmark",
         "One run per mode. Solve times exclude imports, certification, and extra cache validation. No repeated-run error bars.")


EQUATIONS = {
    "eq-01-problem": r"""
\begin{aligned}
p_U(x)&=\left|\langle x|U|0^{98}\rangle\right|^2,
\qquad x_\star\in\underset{x\in\{0,1\}^{98}}{\arg\max}\;p_U(x),\\[5pt]
q_H(x)&=\langle x|\rho_H|x\rangle,\qquad
x^{(t)}\sim q_H.
\end{aligned}
""",
    "eq-02-decoders": r"""
\begin{aligned}
d_H(x,y)&=\sum_{j=0}^{97}\mathbf{1}[x_j\ne y_j],\\[5pt]
\widehat{x}_{\mathrm{med}}&\in\underset{x\in S_{\mathrm{obs}}}{\arg\min}
\sum_{y\in S_{\mathrm{obs}}}c(y)\,d_H(x,y),\\[5pt]
\widehat{x}^{(C)}_j&=\mathbf{1}\!\left[
\sum_{y\in C}c(y)y_j>\frac{1}{2}\sum_{y\in C}c(y)\right].
\end{aligned}
""",
    "eq-03-mirror": r"""
\begin{aligned}
B&\simeq e^{i\phi}A^\dagger
\quad\Longleftrightarrow\quad BA\simeq e^{i\phi}I,\\[5pt]
U&=PMR,
\qquad M\approx\Pi,
\qquad U_{\mathrm{core}}=P\Pi R.
\end{aligned}
""",
    "eq-04-marginals": r"""
\begin{aligned}
z_j&=\langle 0^{98}|
U_{\mathrm{core}}^\dagger Z_jU_{\mathrm{core}}|0^{98}\rangle,\\[5pt]
q_j(0)&=\frac{1+z_j}{2},\qquad q_j(1)=\frac{1-z_j}{2},\\[5pt]
\widehat{x}_j&=\mathbf{1}[z_j\le0],\qquad
s=\left|\langle\widehat{x}|U_{\mathrm{core}}|0^{98}\rangle\right|^2.
\end{aligned}
""",
    "eq-05-cone": r"""
\begin{aligned}
K_j(U)&=\text{ordered gates in the backward causal cone of }Z_j,\\[5pt]
K_j(U')&=K_j(U)\quad\Longrightarrow\quad z_j(U')=z_j(U).
\end{aligned}
""",
    "eq-06-certificate": r"""
\begin{aligned}
y_j\ne\widehat{x}_j\quad&\Longrightarrow\quad
p_{\mathrm{core}}(y)\le q_j(1-\widehat{x}_j),\\[5pt]
q_j(1-\widehat{x}_j)&<p_{\mathrm{core}}(\widehat{x})
\quad\Longrightarrow\quad y\text{ cannot beat }\widehat{x}.
\end{aligned}
""",
}


def equations():
    """Render actual LaTeX with consistent physical width for Medium image blocks."""
    with tempfile.TemporaryDirectory(prefix="peaked-equations-") as temporary:
        folder = Path(temporary)
        for name, expression in EQUATIONS.items():
            source = (
                r"\documentclass[border={8pt 3pt}]{standalone}" "\n"
                r"\usepackage{amsmath,amssymb,xcolor}" "\n"
                r"\definecolor{ink}{HTML}{172D3A}" "\n"
                r"\begin{document}\begin{minipage}{17cm}" "\n"
                r"\fontsize{15}{23}\selectfont\color{ink}" "\n"
                r"\[" + expression + r"\]" "\n"
                r"\end{minipage}\end{document}" "\n"
            )
            tex = folder / f"{name}.tex"
            tex.write_text(source)
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                           cwd=folder, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            subprocess.run(["pdftoppm", "-png", "-singlefile", "-r", "200",
                            str(folder / f"{name}.pdf"), str(OUTPUT / name)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = load_records()
    hero(data)
    hardware(data)
    decoder_bits(data)
    structure(data)
    repair(data)
    runtime(data)
    equations()
    print(f"Wrote six figures and {len(EQUATIONS)} LaTeX equation images to {OUTPUT}")
