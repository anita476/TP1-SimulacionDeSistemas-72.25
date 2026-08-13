#!/usr/bin/env python3
"""Point 3: computation time as a function of M, with error bars.

One curve per value of N. Each point is the mean of the repeated searches and
the bar is their sample standard deviation. Also prints the M that minimises the
time, which is the input point 4 needs.

    python3 python/plot_m.py --csv data/bench_p3.csv
"""

import argparse
import math
import sys

import matplotlib
import matplotlib.pyplot as plt

from bench_common import aggregate, load, spans_orders, sweep_error

COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd"]
MARKERS = ["o", "s", "^", "D"]


def main():
    p = argparse.ArgumentParser(description="Tiempo en funcion de M (punto 3)")
    p.add_argument("--csv", default="data/bench_p3.csv")
    p.add_argument("--out", default="figures/tiempo_vs_M.png")
    p.add_argument("--show", action="store_true")
    args = p.parse_args()

    if not args.show:
        matplotlib.use("Agg")

    try:
        rows = load(args.csv)
    except (OSError, ValueError) as err:
        sys.exit(f"error leyendo {args.csv}: {err}")

    # The plotted point and bar are the mean and standard deviation of the timed
    # searches, which is what the assignment asks for. `sems` is only used to
    # decide which M are actually distinguishable.
    stats = aggregate(rows, lambda r: (r["N"], r["M"]))
    sems = sweep_error(rows, lambda r: (r["N"], r["M"]))
    ns = sorted({n for n, _ in stats})

    fig, ax = plt.subplots(figsize=(8, 5.5))
    all_times, optima = [], {}

    for idx, N in enumerate(ns):
        points = sorted((m, *stats[(N, m)]) for (n, m) in stats if n == N)
        ms = [pt[0] for pt in points]
        means = [pt[1] for pt in points]
        stds = [pt[2] for pt in points]
        reps = points[0][3]
        all_times += means

        ax.errorbar(ms, means, yerr=stds, marker=MARKERS[idx % len(MARKERS)],
                    color=COLORS[idx % len(COLORS)], capsize=3, markersize=5,
                    linewidth=1.4, label=f"N={N}")

        # The minimum alone is not a defensible answer: the tail of the curve is
        # a plateau and which M wins there flips between sweeps. The decision
        # uses the between-sweep error, not the spread of individual searches,
        # which would call almost everything a tie.
        best_m = min((m for (n, m) in stats if n == N), key=lambda m: sems[(N, m)][0])
        bm, bs, sweeps = sems[(N, best_m)]
        plateau = sorted(m for (n, m) in stats if n == N
                         and abs(sems[(N, m)][0] - bm)
                         <= 2.0 * math.hypot(sems[(N, m)][1], bs))
        optima[N] = (best_m, plateau, bm, bs, sweeps, reps)
        ax.annotate(f"M={best_m}", (best_m, stats[(N, best_m)][0]),
                    textcoords="offset points", xytext=(0, -16),
                    color=COLORS[idx % len(COLORS)], ha="center", fontsize=9)

    # The M=1 end is the brute force, an order of magnitude above the plateau.
    ax.set_yscale("log")

    if spans_orders([m for _, m in stats]):
        ax.set_xscale("log")

    sample = rows[0]
    boundary = "contorno periódico" if sample["periodic"] else "paredes"
    ax.set_xlabel("M (celdas por lado)")
    ax.set_ylabel("tiempo de búsqueda [s]")
    ax.set_title(f"Tiempo de búsqueda de vecinas en función de M\n"
                 f"L={sample['L']:g}, rc={sample['rc']:g}, {boundary}, "
                 f"{reps} repeticiones por punto")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()

    from pathlib import Path
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print(f"figura guardada en {args.out}")

    print("\nM optimo por N:")
    for N, (M, plateau, mean, sem, sweeps, reps) in sorted(optima.items()):
        worst = max(stats[(N, m)][0] for (n, m) in stats if n == N)
        error = f" (+-{sem:.1e} entre vueltas)" if sweeps > 1 else ""
        print(f"  N={N:<6} minimo en M={M:<3} t={mean:.4e} s{error}  "
              f"{worst / mean:.1f}x mas rapido que el peor M")
        if sweeps < 2:
            print(f"{'':<9} una sola vuelta: sin estimacion de error, corre benchmark.py "
                  f"con --rounds > 1")
        elif len(plateau) > 1:
            print(f"{'':<9} equivalentes al minimo a 2 sigma: M={plateau} "
                  f"({sweeps} vueltas x {reps // sweeps} busquedas)")

    # Recommend the largest M that is inside every N's plateau: on the plateau
    # they cost the same, and the criterion caps M anyway.
    common = set.intersection(*(set(v[1]) for v in optima.values()))
    choice = max(common) if common else max(v[0] for v in optima.values())
    print(f"\n-> usar --M {choice} en el punto 4")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
