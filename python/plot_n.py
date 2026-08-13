#!/usr/bin/env python3
"""Point 4: computation time as a function of N, both curves superimposed.

4.1 "densidad libre": L stays at 20, so the density grows with N.
4.2 "densidad fija":  L grows with N to hold an intermediate density constant.

The fitted slope in log-log is the exponent k of t ~ N^k, which is what tells
the two regimes apart.

    python3 python/plot_n.py --csv data/bench_p4.csv
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from bench_common import aggregate, fit_slope, load, spans_orders

STYLE = {
    "densidad libre": ("#d62728", "o", "densidad libre (L=20 fijo)"),
    "densidad fija": ("#1f77b4", "s", "densidad fija (L ∝ √N)"),
}


def main():
    p = argparse.ArgumentParser(description="Tiempo en funcion de N (punto 4)")
    p.add_argument("--csv", default="data/bench_p4.csv")
    p.add_argument("--out", default="figures/tiempo_vs_N.png")
    p.add_argument("--show", action="store_true")
    args = p.parse_args()

    if not args.show:
        matplotlib.use("Agg")

    try:
        rows = load(args.csv)
    except (OSError, ValueError) as err:
        sys.exit(f"error leyendo {args.csv}: {err}")

    stats = aggregate(rows, lambda r: (r["tag"], r["N"]))
    tags = [t for t in STYLE if any(tag == t for tag, _ in stats)]
    if not tags:
        sys.exit(f"{args.csv}: no encuentro las etiquetas de 4.1 y 4.2")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    all_times, slopes = [], {}

    for tag in tags:
        points = sorted((n, *stats[(tag, n)]) for (t, n) in stats if t == tag)
        ns = [pt[0] for pt in points]
        means = [pt[1] for pt in points]
        stds = [pt[2] for pt in points]
        reps = points[0][3]
        all_times += means

        color, marker, label = STYLE[tag]
        # The small-N end is dominated by the fixed cost of sweeping the M*M
        # cells, so the asymptotic behaviour only shows in the upper half. Both
        # fits are reported; the legend carries the asymptotic one.
        half = len(ns) // 2
        slopes[tag] = (fit_slope(ns, means), fit_slope(ns[half:], means[half:]), ns[half])

        ax.errorbar(ns, means, yerr=stds, marker=marker, color=color, capsize=3,
                    markersize=5, linewidth=1.4,
                    label=f"{label}\n    t ~ N^{slopes[tag][1]:.2f} para N ≥ {ns[half]}")

    # Both axes span several decades here, so both go logarithmic.
    #if spans_orders([n for _, n in stats]):
    #    ax.set_xscale("log")
    #if spans_orders(all_times):
    #    ax.set_yscale("log")

    sample = rows[0]
    boundary = "contorno periódico" if sample["periodic"] else "paredes"
    ax.set_xlabel("N (cantidad de partículas)")
    ax.set_ylabel("tiempo de búsqueda [s]")
    ax.set_title(f"Tiempo de búsqueda de vecinas en función de N\n"
                 f"rc={sample['rc']:g}, {boundary}, {reps} repeticiones por punto")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print(f"figura guardada en {args.out}")

    print("\nExponente ajustado  t ~ N^k:")
    for tag, (global_k, tail_k, n_from) in slopes.items():
        expected = "~2 (cuadratico)" if tag == "densidad libre" else "~1 (lineal)"
        print(f"  {tag:<16} k = {tail_k:.3f} para N >= {n_from:<6} "
              f"(global {global_k:.3f})   esperado {expected}")

    print("\nCosto por particula (la evidencia mas directa):")
    for tag in tags:
        points = sorted((n, stats[(tag, n)][0]) for (t, n) in stats if t == tag)
        first, last = points[0], points[-1]
        print(f"  {tag:<16} N={first[0]:<5} {1e9 * first[1] / first[0]:6.1f} ns/part"
              f"   ->   N={last[0]:<5} {1e9 * last[1] / last[0]:6.1f} ns/part")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
