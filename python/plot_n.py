#!/usr/bin/env python3
"""Point 4: computation time as a function of N, both curves superimposed.

4.1 "densidad libre": L stays at 20, so the density grows with N.
4.2 "densidad fija":  L grows with N to hold an intermediate density constant.

The fitted slope in log-log is the exponent k of t ~ N^k, which is what tells
the two regimes apart.

    python3 python/plot_n.py --csv data/bench_p4.csv
"""

import argparse
import math
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from bench_common import aggregate, fit_slope, load, spans_orders

FREE, FIXED = "densidad libre", "densidad fija"

STYLE = {
    FREE: ("#d62728", "o", "densidad libre (L=20 fijo)"),
    FIXED: ("#1f77b4", "s", "densidad fija (L ∝ √N)"),
}

# El color distingue el regimen de densidad y el trazo la estructura de celdas.
METHOD_STYLE = {
    "cim": ("-", "vector por celda"),
    "cim-ll": ("--", "listas enlazadas"),
}


def anchor_n(rows, stats):
    """The N where 4.2 was anchored: the one whose L it copied from 4.1.

    4.2 holds the density of an intermediate point of 4.1, so at that point both
    regimes have the same N *and* the same L, which makes them the same
    configuration. The curves cross there by construction, not by accident.
    Read off the data rather than hardcoded, so it follows --n-ref.
    """
    box = {(r["tag"], r["N"]): r["L"] for r in rows}
    shared = ({n for (t, n) in stats if t == FREE} & {n for (t, n) in stats if t == FIXED})
    same = [n for n in sorted(shared) if abs(box[(FREE, n)] - box[(FIXED, n)]) < 1e-6]
    return same[0] if same else None


def sample_M(rows, n):
    """The M actually used at this N (both regimes share it at the anchor)."""
    for r in rows:
        if r["N"] == n:
            return r["M"]
    return None


def empirical_crossing(points):
    """Where the two measured curves actually meet, interpolated in log-log.

    Should land on anchor_n(); how far it misses is a read on the timing noise,
    since at that N the two series time the identical configuration.
    """
    ns = sorted(set(points[FREE]) & set(points[FIXED]))
    diff = [(n, math.log(points[FREE][n]) - math.log(points[FIXED][n])) for n in ns]
    for (n0, d0), (n1, d1) in zip(diff, diff[1:]):
        if d0 == 0.0:
            return n0
        if d0 * d1 < 0.0:  # sign change: the curves swapped order between n0 and n1
            w = d0 / (d0 - d1)
            return math.exp(math.log(n0) + w * (math.log(n1) - math.log(n0)))
    return None


def main():
    p = argparse.ArgumentParser(description="Tiempo en funcion de N (punto 4)")
    p.add_argument("--csv", default="data/bench_p4.csv")
    p.add_argument("--out", default="images/tiempo_vs_N.png")
    p.add_argument("--methods", nargs="+", choices=("cim", "cim-ll"),
                   help="estructuras a graficar; por defecto todas las que haya en el "
                        "CSV. '--methods cim' da la figura del punto 4 sola, sin el "
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

    methods = [m for m in METHOD_STYLE if any(r["method"] == m for r in rows)]
    methods += sorted({r["method"] for r in rows} - set(methods))

    # El cruce de las dos curvas es una propiedad de los regimenes de densidad,
    # no de la estructura de celdas: las dos estructuras miden la misma
    # configuracion y se cruzan en el mismo N. Se calcula sobre una sola de
    # ellas, la primera, para no repetir la misma anotacion dos veces.
    reference = methods[0]
    ref_rows = [r for r in rows if r["method"] == reference]
    ref_stats = aggregate(ref_rows, lambda r: (r["tag"], r["N"]))

    stats = aggregate(rows, lambda r: (r["tag"], r["method"], r["N"]))
    tags = [t for t in STYLE if any(k[0] == t for k in stats)]
    if not tags:
        sys.exit(f"{args.csv}: no encuentro las etiquetas de 4.1 y 4.2")

    fig, ax = plt.subplots(figsize=(8.5, 6))
    all_times, slopes, curves = [], {}, {}

    for tag in tags:
        for method in methods:
            keys = [k for k in stats if k[0] == tag and k[1] == method]
            if not keys:
                continue
            points = sorted((k[2], *stats[k]) for k in keys)
            ns = [pt[0] for pt in points]
            means = [pt[1] for pt in points]
            reps = points[0][3]
            bars = [pt[2] for pt in points]
            # A bar that reaches the axis floor is meaningless on a log scale and
            # renders as a spike to the bottom of the figure, so it is clipped to
            # just under the point it belongs to.
            bars = [min(b, m * 0.95) for b, m in zip(bars, means)]
            all_times += means
            if method == reference:
                curves[tag] = dict(zip(ns, means))

            color, marker, label = STYLE[tag]
            dash, method_label = METHOD_STYLE.get(method, ("-", method))
            # The small-N end is dominated by the fixed cost of sweeping the M*M
            # cells, so the asymptotic behaviour only shows in the upper half. Both
            # fits are reported; the legend carries the asymptotic one.
            half = len(ns) // 2
            slopes[(tag, method)] = (fit_slope(ns, means), fit_slope(ns[half:], means[half:]), ns[half])

            head = label if len(methods) == 1 else f"{label} · {method_label}"
            ax.errorbar(ns, means, yerr=bars, marker=marker, color=color, capsize=3,
                        markersize=5, linewidth=1.4, linestyle=dash,
                        label=f"{head}\n    t ~ N^{slopes[(tag, method)][1]:.2f} para N ≥ {ns[half]}")

    # Both axes span several decades here, so both go logarithmic.
    if spans_orders([k[2] for k in stats]):
        ax.set_xscale("log")
    if spans_orders(all_times):
        ax.set_yscale("log")

    # The crossing is the anchor of 4.2 and worth naming on the figure: left of
    # it the L=20 box is the emptier of the two, right of it the denser one.
    anchor = anchor_n(ref_rows, ref_stats) if len(tags) == 2 else None
    crossing = empirical_crossing(curves) if len(tags) == 2 else None
    if anchor is not None:
        t_anchor = 0.5 * (curves[FREE][anchor] + curves[FIXED][anchor])
        ax.axvline(anchor, color="#666666", linestyle=(0, (4, 3)), linewidth=1.1, zorder=0)
        ax.plot([anchor], [t_anchor], marker="o", markersize=11, markerfacecolor="none",
                markeredgecolor="#333333", markeredgewidth=1.4, zorder=5)
        ax.annotate(f"se cruzan en N = {anchor}\nmisma configuración:\nL=20, M={sample_M(ref_rows, anchor)}, ρ={anchor / 400:.3f}",
                    xy=(anchor, t_anchor), xytext=(14, -78), textcoords="offset points",
                    fontsize=9, color="#333333", ha="left",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff",
                              edgecolor="#bbbbbb", linewidth=0.8),
                    arrowprops=dict(arrowstyle="-", color="#999999", linewidth=0.9))

    sample = rows[0]
    boundary = "contorno periódico" if sample["periodic"] else "paredes"
    ax.set_xlabel("N (cantidad de partículas)")
    ax.set_ylabel("tiempo de búsqueda [s]")
    ax.set_title(f"Tiempo de búsqueda de vecinas en función de N\n"
                 f"rc={sample['rc']:g}, {boundary}, {reps} repeticiones por punto, "
                 f"barra = desvío estándar de las búsquedas")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print(f"figura guardada en {args.out}")

    print("\nExponente ajustado  t ~ N^k:")
    for (tag, method), (global_k, tail_k, n_from) in slopes.items():
        expected = "~2 (cuadratico)" if tag == FREE else "~1 (lineal)"
        print(f"  {tag:<16} {method:<7} k = {tail_k:.3f} para N >= {n_from:<6} "
              f"(global {global_k:.3f})   esperado {expected}")
    if len(methods) > 1:
        print("  el exponente de las dos estructuras deberia coincidir (mismo barrido);")
        print("  lo que las separa es el prefactor")

    if anchor is not None:
        free, fixed = curves[FREE][anchor], curves[FIXED][anchor]
        print(f"\nCruce de las dos curvas:")
        print(f"  por construccion   N = {anchor}  (es el N de referencia del que 4.2 copio "
              f"L=20, asi que ahi las dos curvas miden la MISMA configuracion)")
        if crossing is not None:
            print(f"  medido             N = {crossing:.1f}  "
                  f"(desvio de {abs(crossing - anchor) / anchor * 100:.1f}% respecto del anterior: es ruido de medicion)")
        gap = abs(free - fixed) / min(free, fixed) * 100
        print(f"  tiempos en N={anchor}:  libre {free * 1e6:.2f} us   fija {fixed * 1e6:.2f} us   "
              f"difieren {gap:.1f}%")

        # Las dos series miden ahi el mismo archivo, asi que su diferencia no
        # puede ser fisica: es el piso de ruido de esta corrida, medido en vez de
        # supuesto. Sirve para saber si el barrido salio limpio antes de usarlo.
        verdict = ("corrida limpia" if gap < 2.0 else
                   "aceptable" if gap < 5.0 else
                   "CORRIDA SUCIA: repetir con la maquina libre")
        print(f"\n  Piso de ruido de esta corrida: {gap:.1f}%  ({verdict})")
        print(f"  (en N={anchor} las dos curvas cronometran el MISMO archivo, asi que todo lo "
              f"que difieran es error de medicion)")

    print("\nCosto por particula (la evidencia mas directa):")
    for tag in tags:
        for method in methods:
            points = sorted((k[2], stats[k][0]) for k in stats
                            if k[0] == tag and k[1] == method)
            if not points:
                continue
            first, last = points[0], points[-1]
            print(f"  {tag:<16} {method:<7} N={first[0]:<5} {1e9 * first[1] / first[0]:6.1f} ns/part"
                  f"   ->   N={last[0]:<5} {1e9 * last[1] / last[0]:6.1f} ns/part")

    if len(methods) > 1:
        print("\nListas enlazadas contra vector por celda, por N:")
        for tag in tags:
            ns = sorted({k[2] for k in stats if k[0] == tag})
            ratios = []
            for n in ns:
                have = [stats[(tag, m, n)][0] for m in methods if (tag, m, n) in stats]
                if len(have) == 2:
                    ratios.append((n, have[1] / have[0]))
            if ratios:
                worst = min(ratios, key=lambda p: p[1])
                print(f"  {tag:<16} N={ratios[0][0]:<5} {ratios[0][1]:.2f}x   ->   "
                      f"N={ratios[-1][0]:<5} {ratios[-1][1]:.2f}x"
                      f"   (mejor: {worst[1]:.2f}x en N={worst[0]})")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
