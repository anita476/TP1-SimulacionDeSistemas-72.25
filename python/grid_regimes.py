#!/usr/bin/env python3
"""Why the two curves of point 4 separate: the same N drawn in both regimes.

Each panel is one configuration inside its M x M grid, with every cell shaded by
how many particles fall in it. That shading is the occupancy N_c = N/M^2, which
is what the cost of the sweep is proportional to.

    densidad libre (4.1)  L = 20 fixed  ->  rho = N/L^2 grows, cells fill up
    densidad fija  (4.2)  L propto sqrt(N) -> rho fixed, cells stay as full

At the reference N the two are the same configuration, which is why the curves
of tiempo_vs_N.png cross there and nowhere else.

    python3 python/grid_regimes.py
    python3 python/grid_regimes.py --ns 36 128 458 1071 --out images/regimenes.png
"""

import argparse
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Circle, Rectangle

from visualize import read_dynamic, read_static

EXE = "./build/CIM-TP1"

L_DEFAULT = 20.0
RC_DEFAULT = 1.0
R_MIN, R_MAX = 0.23, 0.26

FREE, FIXED = "densidad libre", "densidad fija"
IDENTITY = {FREE: "#d62728", FIXED: "#1f77b4"}
# Occupancy is a magnitude, so it gets one hue light->dark, kept clear of both
# identity colours so the shading is never read as "which regime is this".
OCCUPANCY_CMAP = "Purples"
PARTICLE_FACE = "#fdfdfd"
PARTICLE_EDGE = "#4a4a4a"


def cim_max_grid_side(L, rc, r_max=R_MAX):
    """Mirror of the C++ criterion: cells at least as wide as the interaction reach."""
    return int(math.floor(L / (rc + 2.0 * r_max)))


def generate(N, L, seed, tmp, tag):
    """Writes one configuration with the simulator and returns (L, radii, positions)."""
    static, dynamic = f"{tmp}/{tag}_s.txt", f"{tmp}/{tag}_d.txt"
    result = subprocess.run(
        [EXE, "-N", str(N), "-L", f"{L:.6f}", "--seed", str(seed),
         "--rmin", str(R_MIN), "--rmax", str(R_MAX), "--method", "none",
         "--static-out", static, "--dynamic-out", dynamic],
        capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"no se pudo generar N={N} L={L:.4f}: {result.stderr.strip().splitlines()[-1]}")
    box, radii = read_static(static)
    return box, radii, read_dynamic(dynamic, len(radii))


def occupancy(positions, L, M):
    """Particles per cell, as a list of M rows of M counts. Mirrors CellGrid::cell_coord."""
    counts = [[0] * M for _ in range(M)]
    for x, y in positions:
        cx = min(M - 1, max(0, int(x * M / L)))
        cy = min(M - 1, max(0, int(y * M / L)))
        counts[cy][cx] += 1
    return counts


def draw_panel(ax, cfg, vmax, rc):
    """One box: cells shaded by occupancy, grid lines, particles at true radius."""
    L, radii, positions, M, regime = cfg["L"], cfg["radii"], cfg["pos"], cfg["M"], cfg["regime"]
    cell = L / M

    counts = occupancy(positions, L, M)
    cmap = matplotlib.colormaps[OCCUPANCY_CMAP]
    for cy in range(M):
        for cx in range(M):
            shade = counts[cy][cx] / vmax if vmax else 0.0
            ax.add_patch(Rectangle((cx * cell, cy * cell), cell, cell,
                                   facecolor=cmap(0.08 + 0.82 * shade), edgecolor="none",
                                   zorder=0))

    # Grid lines thin enough to stay recessive once M gets to 38.
    width = 0.5 if M <= 16 else 0.25
    for k in range(M + 1):
        ax.axhline(k * cell, color="#ffffff", linewidth=width, zorder=1)
        ax.axvline(k * cell, color="#ffffff", linewidth=width, zorder=1)

    discs = [Circle((x, y), r) for (x, y), r in zip(positions, radii)]
    ax.add_collection(PatchCollection(discs, facecolor=PARTICLE_FACE, edgecolor=PARTICLE_EDGE,
                                      linewidths=0.35, zorder=2))

    # Every panel is normalised to its own box, so a bar of fixed physical length
    # is the only cue to how big the box actually is. rc is the natural choice:
    # it shrinks visibly across 4.2 as L grows, and it shows at a glance how the
    # interaction radius compares to the cell that has to contain it.
    bar_y = -0.055 * L
    ax.plot([0, rc], [bar_y, bar_y], color="#222222", linewidth=2.2,
            solid_capstyle="butt", clip_on=False, zorder=5)
    ax.text(rc * 0.5, bar_y - 0.02 * L, f"rc={rc:g}", ha="center", va="top",
            fontsize=7.5, color="#222222", clip_on=False)

    ax.add_patch(Rectangle((0, 0), L, L, fill=False, edgecolor=IDENTITY[regime],
                           linewidth=1.8, zorder=4))
    ax.set_xlim(-0.02 * L, 1.02 * L)
    ax.set_ylim(-0.10 * L, 1.02 * L)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    n = len(positions)
    ax.set_title(f"L={L:.2f}   M={M}   celda={cell:.2f}\n"
                 f"ρ={n / (L * L):.3f}      N$_c$={n / (M * M):.2f}",
                 fontsize=8.5, pad=4)


def main():
    p = argparse.ArgumentParser(description="Los dos regimenes de densidad del punto 4")
    p.add_argument("--ns", type=int, nargs="+", default=[36, 128, 458, 1071],
                   help="valores de N a dibujar (uno por columna)")
    p.add_argument("--n-ref", type=int, default=128,
                   help="N de referencia: donde 4.2 fija la densidad y las curvas se cruzan")
    p.add_argument("-L", type=float, default=L_DEFAULT)
    p.add_argument("--rc", type=float, default=RC_DEFAULT)
    p.add_argument("--M", type=int, default=13, help="M optimo del punto 3")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="images/regimenes.png")
    p.add_argument("--show", action="store_true")
    args = p.parse_args()

    if not args.show:
        matplotlib.use("Agg")
    if not os.path.exists(EXE):
        sys.exit(f"no encuentro {EXE}: compila primero con cmake --build build")

    density = args.n_ref / (args.L * args.L)

    with tempfile.TemporaryDirectory() as tmp:
        panels = {}
        for N in args.ns:
            L_free, M_free = args.L, args.M
            L_fix = math.sqrt(N / density)
            M_fix = min(cim_max_grid_side(L_fix, args.rc), max(1, round(args.M * L_fix / args.L)))
            for regime, L, M, tag in ((FREE, L_free, M_free, f"a{N}"),
                                      (FIXED, L_fix, M_fix, f"b{N}")):
                box, radii, pos = generate(N, L, args.seed, tmp, tag)
                panels[(regime, N)] = {"L": box, "radii": radii, "pos": pos,
                                       "M": M, "regime": regime}

        vmax = max(max(max(row) for row in occupancy(c["pos"], c["L"], c["M"]))
                   for c in panels.values())

        rows = [FREE, FIXED]
        fig, axes = plt.subplots(len(rows), len(args.ns),
                                 figsize=(3.05 * len(args.ns), 3.5 * len(rows) + 1.5),
                                 squeeze=False)
        # Placed by hand rather than by tight_layout: the column headers live
        # outside their axes and a colorbar attached to `axes` would reflow them.
        fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.13,
                            wspace=0.10, hspace=0.24)

        for i, regime in enumerate(rows):
            for j, N in enumerate(args.ns):
                draw_panel(axes[i][j], panels[(regime, N)], vmax, args.rc)
            axes[i][0].set_ylabel(
                f"4.1  densidad libre\nL={args.L:g} fijo" if regime == FREE
                else "4.2  densidad fija\nL ∝ √N",
                fontsize=10, color=IDENTITY[regime], labelpad=12)

        for j, N in enumerate(args.ns):
            reference = N == args.n_ref
            axes[0][j].text(0.5, 1.30, f"N = {N}", transform=axes[0][j].transAxes,
                            ha="center", va="bottom", fontsize=12,
                            fontweight="bold" if reference else "normal", color="#222222")
            if reference:
                # The two regimes are one configuration here by construction, and
                # that is the whole reason the curves of point 4 meet at this N.
                axes[0][j].text(0.5, 1.19, "misma configuración\nen ambos regímenes",
                                transform=axes[0][j].transAxes, ha="center", va="bottom",
                                fontsize=8, style="italic", color="#555555", linespacing=1.2)

        sm = plt.cm.ScalarMappable(cmap=OCCUPANCY_CMAP,
                                   norm=matplotlib.colors.Normalize(0, vmax))
        cax = fig.add_axes([0.18, 0.055, 0.64, 0.016])
        cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
        cbar.set_label("partículas en la celda   (el sombreado es N$_c$, "
                       "y el costo del barrido es proporcional a N·N$_c$)", fontsize=9)

        fig.suptitle(
            f"Los dos regímenes del punto 4, con la grilla M×M que realmente se barre\n"
            f"densidad de referencia ρ = {density:.3f} part/área, tomada de N={args.n_ref}",
            fontsize=13, y=0.965)

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.out, dpi=150)
        print(f"figura guardada en {args.out}\n")

        print(f"{'N':>6} {'regimen':>16} {'L':>8} {'M':>4} {'celda':>7} {'rho':>8} {'N_c':>7}")
        for N in args.ns:
            for regime in rows:
                c = panels[(regime, N)]
                n = len(c["pos"])
                print(f"{N:>6} {regime:>16} {c['L']:>8.3f} {c['M']:>4} {c['L'] / c['M']:>7.3f} "
                      f"{n / (c['L'] ** 2):>8.4f} {n / c['M'] ** 2:>7.2f}")
            print()

        if args.show:
            plt.show()


if __name__ == "__main__":
    main()
