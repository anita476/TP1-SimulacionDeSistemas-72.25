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

from bench_common import aggregate, load, spans_orders

COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd"]
MARKERS = ["o", "s", "^", "D"]

METHOD_STYLE = {
    "cim": ("-", "vector por celda"),
    "cim-ll": ("--", "listas enlazadas"),
}


def main():
    p = argparse.ArgumentParser(description="Tiempo en funcion de M (punto 3)")
    p.add_argument("--csv", default="data/bench_p3.csv")
    p.add_argument("--out", default="images/tiempo_vs_M.png")
    p.add_argument("--methods", nargs="+", choices=("cim", "cim-ll"),
                   help="estructuras a graficar; por defecto todas las que haya en el "
                        "CSV. '--methods cim' da la figura del punto 3 sola, sin el "
                        "estudio extra de listas enlazadas encima")
    p.add_argument("--show", action="store_true")
    args = p.parse_args()

    if not args.show:
        matplotlib.use("Agg")

    try:
        rows = load(args.csv)
    except (OSError, ValueError) as err:
        sys.exit(f"error leyendo {args.csv}: {err}")

    if args.methods:
        rows = [r for r in rows if r["method"] in args.methods]
        if not rows:
            sys.exit(f"{args.csv}: no hay filas con --methods {' '.join(args.methods)}")

    # The plotted point and bar are the mean and standard deviation of the timed
    # searches, which is what the assignment asks for.
    stats = aggregate(rows, lambda r: (r["N"], r["method"], r["M"]))
    ns = sorted({n for n, _, _ in stats})
    methods = [m for m in METHOD_STYLE if any(k[1] == m for k in stats)]
    methods += sorted({k[1] for k in stats} - set(methods))

    fig, ax = plt.subplots(figsize=(8, 5.5))
    all_times, optima = [], {}

    for idx, N in enumerate(ns):
        for mi, method in enumerate(methods):
            keys = [k for k in stats if k[0] == N and k[1] == method]
            if not keys:
                continue
            points = sorted((k[2], *stats[k]) for k in keys)
            ms = [pt[0] for pt in points]
            means = [pt[1] for pt in points]
            reps = points[0][3]
            bars = [pt[2] for pt in points]
            # Una barra que llega al piso del eje no significa nada en escala
            # logaritmica y se dibuja como un pincho hasta el fondo de la
            # figura, asi que se recorta apenas por debajo de su punto.
            bars = [min(b, m * 0.95) for b, m in zip(bars, means)]
            all_times += means

            dash, method_label = METHOD_STYLE.get(method, ("-", method))
            label = f"N={N}" if len(methods) == 1 else f"N={N} · {method_label}"
            ax.errorbar(ms, means, yerr=bars, marker=MARKERS[mi % len(MARKERS)],
                        color=COLORS[idx % len(COLORS)], linestyle=dash, capsize=3,
                        markersize=5, linewidth=1.4, label=label)

            # The argmin alone is not a defensible answer: the tail of the curve is a
            # plateau and which M wins there flips with the noise, so the reported
            # optimum is the largest M that ties with it at 2 sigma of the error of
            # the mean (std/sqrt(n), not the spread of individual searches, which
            # would call almost everything a tie).
            def sem(m):
                _, std, count = stats[(N, method, m)]
                return std / math.sqrt(count) if count > 1 else float("inf")
            best_m = min((k[2] for k in keys), key=lambda m: stats[(N, method, m)][0])
            bm, bs = stats[(N, method, best_m)][0], sem(best_m)
            plateau = sorted(k[2] for k in keys
                             if abs(stats[(N, method, k[2])][0] - bm)
                             <= 2.0 * math.hypot(sem(k[2]), bs))
            choice = max(plateau)
            optima[(N, method)] = (best_m, choice, plateau, reps)
            # Las dos estructuras suelen elegir el mismo M, asi que las dos
            # etiquetas caerian una encima de la otra: se separan por metodo.
            ax.annotate(f"M={choice}", (choice, stats[(N, method, choice)][0]),
                        textcoords="offset points", xytext=(0, -18 - 13 * mi),
                        color=COLORS[idx % len(COLORS)], ha="center", fontsize=9)

    # The M=1 end is the brute force, an order of magnitude above the plateau.
    ax.set_yscale("log")

    if spans_orders([k[2] for k in stats]):
        ax.set_xscale("log")

    sample = rows[0]
    boundary = "contorno periódico" if sample["periodic"] else "paredes"
    ax.set_xlabel("M (celdas por lado)")
    ax.set_ylabel("tiempo de búsqueda [s]")
    ax.set_title(f"Tiempo de búsqueda de vecinas en función de M\n"
                 f"L={sample['L']:g}, rc={sample['rc']:g}, {boundary}, "
                 f"{reps} repeticiones por punto\n"
                 f"barra: desvío estándar de las búsquedas", fontsize=11)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()

    from pathlib import Path
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print(f"figura guardada en {args.out}")

    print("\nM optimo por N y estructura:")
    for (N, method), (best_m, choice, plateau, reps) in sorted(optima.items()):
        worst = max(stats[k][0] for k in stats if k[0] == N and k[1] == method)
        print(f"  N={N:<6} {method:<7} M={choice:<3} t={stats[(N, method, choice)][0]:.4e} s  "
              f"{worst / stats[(N, method, choice)][0]:.1f}x mas rapido que el peor M")
        if len(plateau) > 1:
            # Saying "el minimo esta en M=12" when 12 and 13 are a coin flip is
            # what makes this look like a result instead of noise.
            print(f"{'':<9} meseta a 2 sigma: M={plateau} (el argmin cayo en M={best_m}, "
                  f"pero no se distingue del resto de la meseta; se toma el mayor)")
        else:
            print(f"{'':<9} minimo neto, sin empate a 2 sigma "
                  f"({reps} busquedas por punto)")

    # El costo de armar la grilla crece con M y no crece igual para las dos, asi
    # que los optimos podrian no coincidir.
    if len(methods) > 1:
        print("\nComparacion entre estructuras, M optimo de cada una:")
        for N in ns:
            best = {m: optima[(N, m)][1] for m in methods if (N, m) in optima}
            times = {m: stats[(N, m, best[m])][0] for m in best}
            if len(times) == 2:
                (a, ta), (b, tb) = times.items()
                verdict = "el mismo M" if len(set(best.values())) == 1 else "DISTINTO M"
                print(f"  N={N:<6} {a}: M={best[a]} {ta:.3e} s | "
                      f"{b}: M={best[b]} {tb:.3e} s | {tb / ta:.2f}x | {verdict}")

    # Recommend the largest M that is inside every plateau of that method: on the
    # plateau they cost the same, and the criterion caps M anyway.
    picks = []
    for method in methods:
        plateaus = [set(v[2]) for k, v in optima.items() if k[1] == method]
        common = set.intersection(*plateaus) if plateaus else set()
        fallback = max(v[1] for k, v in optima.items() if k[1] == method)
        picks.append(f"{method}={max(common) if common else fallback}")
    # Esta linea la lee run_all.sh y se la pasa tal cual al punto 4.
    print(f"\n-> usar --M {' '.join(picks)} en el punto 4")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
