#!/usr/bin/env python3
"""Compara las dos estructuras de celdas, en cuatro paneles.

Las dos miden los mismos pares (columna pair_tests del CSV), asi que el tiempo
total no dice por si solo de donde sale la diferencia. Estos cuatro paneles si:

  1. armado de la grilla     <- el resultado medido
  2. barrido                 <- el control: tiene que dar empate
  3. memoria de la estructura, sin contar las listas de salida
  4. bloques vivos           <- la explicacion del panel 1

Los paneles 3 y 4 no son mediciones: son propiedades de cada estructura, iguales
en cada corrida y calculables de antemano. Estan para explicar de donde sale la
diferencia del panel 1, no como un resultado aparte.

'Bloques vivos' es cuantos bloques del heap tiene la estructura una vez armada,
no cuantos le pidio al allocator para llegar ahi. En CellGrid cada celda crece
duplicando, asi que una celda que termina con 6 particulas pidio cuatro veces
(1, 2, 4, 8) y libero tres: queda 1 bloque vivo de 4 pedidos. Se cuenta lo vivo
para que vaya en par con grid_bytes, que tambien es lo que se tiene. La cifra de
pedidos es ~4x mayor con esta ocupancia, o sea que este panel es la version
CONSERVADORA de la diferencia.

No mide nada nuevo: lee los CSV que dejo benchmark.py.

    python3 python/plot_compare.py
    python3 python/plot_compare.py --csv data/bench_p4.csv --x N --out images/comparacion_vs_N.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from bench_common import aggregate, load

METHOD_STYLE = {
    "cim": ("#d62728", "o", "-", "vector por celda"),
    "cim-ll": ("#1f77b4", "s", "--", "listas enlazadas"),
}


def series(stats, method, field_index=0):
    """[(x, valor)] ordenado, para una estructura."""
    return sorted((k[1], stats[k][field_index]) for k in stats if k[0] == method)


def main():
    p = argparse.ArgumentParser(description="Comparacion de las dos estructuras de celdas")
    p.add_argument("--csv", default="data/bench_p3.csv")
    p.add_argument("--x", choices=("M", "N"), default="M",
                   help="que barre el eje horizontal (M para el punto 3, N para el 4)")
    p.add_argument("--tag", help="quedarse con una sola etiqueta del CSV "
                                 "(en el punto 4, un solo regimen de densidad)")
    p.add_argument("--N", type=int, help="quedarse con un solo N (util en el punto 3)")
    p.add_argument("--out", default="images/comparacion_estructuras.png")
    p.add_argument("--show", action="store_true")
    args = p.parse_args()

    if not args.show:
        matplotlib.use("Agg")

    try:
        rows = load(args.csv)
    except (OSError, ValueError) as err:
        sys.exit(f"error leyendo {args.csv}: {err}")

    if args.tag:
        rows = [r for r in rows if r["tag"] == args.tag]
    if args.N:
        rows = [r for r in rows if r["N"] == args.N]
    if not rows:
        sys.exit("el filtro no dejo ninguna fila")

    methods = [m for m in METHOD_STYLE if any(r["method"] == m for r in rows)]
    if len(methods) < 2:
        sys.exit(f"{args.csv}: hace falta que las dos estructuras esten medidas "
                 f"(encontre {methods}); corre benchmark.py con --methods cim cim-ll")

    if args.N is None and args.x == "M":
        # Con varios N mezclados las curvas se pisan; el punto 3 mide dos, y el
        # mas grande es el que tiene algo que decir sobre la memoria.
        biggest = max(r["N"] for r in rows)
        rows = [r for r in rows if r["N"] == biggest]
        print(f"me quedo con N={biggest} (el mayor del CSV); usa --N para elegir otro")

    key = (lambda r: (r["method"], r[args.x]))
    panels = [
        ("build_seconds", "armado de la grilla [s]", "1. armar la grilla", True),
        ("sweep_seconds", "barrido [s]", "2. barrer las celdas", True),
        ("grid_bytes", "memoria de la grilla [B]", "3. memoria de la estructura", True),
        ("grid_live_blocks", "bloques vivos", "4. bloques que la estructura tiene", True),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    ratios = {}

    for ax, (field, ylabel, title, logy) in zip(axes.flat, panels):
        stats = aggregate(rows, key)
        curves = {}
        for method in methods:
            # aggregate promedia 'seconds'; para las demas columnas se promedia
            # aca, que para bytes y allocations es constante entre corridas.
            points = {}
            for r in rows:
                if r["method"] == method:
                    points.setdefault(r[args.x], []).append(r[field])
            xs = sorted(points)
            ys = [sum(points[x]) / len(points[x]) for x in xs]
            curves[method] = dict(zip(xs, ys))

            color, marker, dash, label = METHOD_STYLE[method]
            ax.plot(xs, ys, marker=marker, color=color, linestyle=dash,
                    markersize=5, linewidth=1.4, label=label)

        a, b = methods
        common = sorted(set(curves[a]) & set(curves[b]))
        ratios[field] = [(x, curves[b][x] / curves[a][x]) for x in common
                         if curves[a][x] > 0]

        if logy:
            ax.set_yscale("log")
        ax.set_xlabel(args.x)
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=10)
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)

    sample = rows[0]
    boundary = "contorno periódico" if sample["periodic"] else "paredes"
    fig.suptitle(f"Vector por celda contra listas enlazadas\n"
                 f"N={sample['N']}, rc={sample['rc']:g}, {boundary}"
                 if args.x == "M" else
                 f"Vector por celda contra listas enlazadas\n"
                 f"rc={sample['rc']:g}, {boundary}, barrido en N")
    fig.tight_layout()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print(f"figura guardada en {args.out}")

    print(f"\nlistas enlazadas / vector por celda, en funcion de {args.x}:")
    print(f"  {'':>6} {'armado':>9} {'barrido':>9} {'memoria':>9} {'vivos':>9}")
    xs = [x for x, _ in ratios["build_seconds"]]
    for i, x in enumerate(xs):
        cells = []
        for field in ("build_seconds", "sweep_seconds", "grid_bytes", "grid_live_blocks"):
            match = [v for xx, v in ratios[field] if xx == x]
            cells.append(f"{match[0]:8.3f}x" if match else f"{'-':>9}")
        print(f"  {args.x}={x:<4}" + " ".join(cells))

    print("\nMenos de 1 es a favor de las listas enlazadas. El barrido deberia dar")
    print("cerca de 1, porque es el mismo trabajo; el resultado esta en el armado.")
    print("Memoria y bloques vivos no son mediciones sino propiedades de cada")
    print("estructura, y estan para explicar por que el armado da lo que da.")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
