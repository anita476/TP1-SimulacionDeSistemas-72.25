#!/usr/bin/env python3
"""Runs the parametric sweeps of points 3 and 4 of the assignment.

Point 3 — L=20, rc=1, r=U[0.23,0.26]. Two values of N (one intermediate and the
highest the geometry admits); for each, M from 1 (brute force) up to the maximum
the method allows.

Point 4 — with the optimal M from point 3, at least 10 values of N from 10 up to
the maximum. 4.1 keeps L=20 so the density grows with N; 4.2 grows L along with
N to hold an intermediate density from 4.1 constant.

Every point in a sweep reuses the SAME configuration across all values of M, so
the comparison is paired and the differences are the algorithm, not the sample.

    python3 python/benchmark.py --part 3
    python3 python/benchmark.py --part 4 --M 13
"""

import argparse
import math
import os
import subprocess
import sys

EXE = "./build/CIM-TP1"
TMP = "data/bench_tmp"

L_DEFAULT = 20.0
RC_DEFAULT = 1.0
R_MIN, R_MAX = 0.23, 0.26


def run(args):
    return subprocess.run([EXE] + [str(a) for a in args], capture_output=True, text=True)


def cim_max_grid_side(L, rc, r_max=R_MAX):
    """Mirror of the C++ criterion, used only to know how far to sweep M."""
    return int(math.floor(L / (rc + 2.0 * r_max)))


def generate(N, L, seed, periodic, tag):
    """Writes one configuration and returns the two input paths, or None."""
    os.makedirs(TMP, exist_ok=True)
    static, dynamic = f"{TMP}/{tag}_s.txt", f"{TMP}/{tag}_d.txt"
    args = ["-N", N, "-L", L, "--seed", seed, "--rmin", R_MIN, "--rmax", R_MAX,
            "--method", "none", "--static-out", static, "--dynamic-out", dynamic]
    if periodic:
        args.append("--periodic")
    return (static, dynamic) if run(args).returncode == 0 else None


def max_generable_n(L, seed, periodic):
    """Highest N the geometry admits: the assignment's 'el mas alto posible'."""
    lo, hi = 1, 2
    while generate(hi, L, seed, periodic, "probe") is not None:
        lo, hi = hi, hi * 2
        if hi > 1 << 20:
            break
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if generate(mid, L, seed, periodic, "probe") is not None:
            lo = mid
        else:
            hi = mid
    return lo


def measure(inputs, M, rc, periodic, repeat, warmup, csv, seed, tag):
    static, dynamic = inputs
    args = ["--input-static", static, "--input-dynamic", dynamic, "--rc", rc,
            "--method", "cim", "-M", M, "--seed", seed, "--tag", tag,
            "--repeat", repeat, "--warmup", warmup, "--csv", csv,
            "--neighbors-out", f"{TMP}/n.txt"]
    if periodic:
        args.append("--periodic")
    result = run(args)
    if result.returncode != 0:
        print(f"    M={M}: FALLO -> {result.stderr.strip().splitlines()[-1]}")
        return False
    return True


def part3(args):
    """Point 3: time versus M, for two values of N."""
    L, rc = L_DEFAULT, args.rc
    n_max = max_generable_n(L, args.seed, args.periodic)
    n_mid = n_max // 2
    m_max = cim_max_grid_side(L, rc)

    print(f"L={L} rc={rc} | N maximo generable = {n_max} | M de 1 a {m_max}")
    if os.path.exists(args.csv):
        os.remove(args.csv)

    configs = {}
    for N in (n_mid, n_max):
        inputs = generate(N, L, args.seed, args.periodic, f"n{N}")
        if inputs is None:
            print(f"  N={N}: no se pudo generar")
            continue
        configs[N] = (inputs, "intermedio" if N == n_mid else "maximo")

    # The whole sweep is repeated instead of only the search inside each point.
    # Measuring every M in one contiguous burst confounds the machine's drift
    # (CPU frequency, cache state) with the value of M: between-sweep scatter
    # came out 3 to 7 times the standard error a single sweep reports.
    for round_index in range(args.rounds):
        print(f"  vuelta {round_index + 1}/{args.rounds}:", end="", flush=True)
        for N, (inputs, tag) in configs.items():
            for M in range(1, m_max + 1):
                measure(inputs, M, rc, args.periodic, args.repeat, args.warmup, args.csv,
                        args.seed, tag)
            print(f" N={N}", end="", flush=True)
        print()

    print(f"\n-> {args.csv}  ({args.rounds} vueltas x {args.repeat} busquedas por punto)")


def part4(args):
    """Point 4: time versus N, at fixed L (4.1) and at fixed density (4.2)."""
    L, rc = L_DEFAULT, args.rc
    n_max = max_generable_n(L, args.seed, args.periodic)

    # At least 10 values from N=10 to the maximum, spread logarithmically so the
    # small end is not crushed by the large one.
    count = max(args.points, 10)
    values = sorted({int(round(10 * (n_max / 10) ** (i / (count - 1)))) for i in range(count)})

    # 4.2 holds constant the density of an intermediate point of 4.1.
    n_ref = values[len(values) // 2]
    density = n_ref / (L * L)

    print(f"L={L} rc={rc} | N maximo = {n_max} | M optimo = {args.M}")
    print(f"4.1 densidad libre (L={L} fijo)")
    print(f"4.2 densidad fija = {density:.4f} part/area (referencia N={n_ref})")
    if os.path.exists(args.csv):
        os.remove(args.csv)

    m_max_fixed_L = cim_max_grid_side(L, rc)
    if args.M > m_max_fixed_L:
        sys.exit(f"M={args.M} supera el maximo {m_max_fixed_L} para L={L}")

    # Both curves are generated once and then swept repeatedly, for the same
    # reason as in point 3: a point measured in its own contiguous burst carries
    # whatever the machine was doing at that moment.
    plan = []
    for N in values:
        inputs = generate(N, L, args.seed, args.periodic, f"a{N}")
        if inputs is not None:
            plan.append((inputs, args.M, "densidad libre", N))

        L_n = math.sqrt(N / density)
        # Keeping the cell size fixed is what "the same M" means once L moves;
        # the criterion still caps it.
        M_n = min(cim_max_grid_side(L_n, rc), max(1, round(args.M * L_n / L)))
        inputs = generate(N, round(L_n, 6), args.seed, args.periodic, f"b{N}")
        if inputs is not None:
            plan.append((inputs, M_n, "densidad fija", N))

    for round_index in range(args.rounds):
        print(f"  vuelta {round_index + 1}/{args.rounds}:", end="", flush=True)
        for inputs, M, tag, N in plan:
            measure(inputs, M, rc, args.periodic, args.repeat, args.warmup, args.csv,
                    args.seed, tag)
        print(" ok")

    print(f"\n-> {args.csv}  ({args.rounds} vueltas x {args.repeat} busquedas por punto)")


def main():
    p = argparse.ArgumentParser(description="Barridos parametricos del TP1")
    p.add_argument("--part", type=int, choices=(3, 4), required=True)
    p.add_argument("--M", type=int, help="M optimo hallado en el punto 3 (requerido para --part 4)")
    p.add_argument("--rc", type=float, default=RC_DEFAULT)
    p.add_argument("--repeat", type=int, default=100, help="busquedas cronometradas por punto y vuelta")
    p.add_argument("--rounds", type=int, default=5,
                   help="veces que se repite el barrido completo, para que la deriva "
                        "de la maquina no quede pegada a un valor de M")
    p.add_argument("--warmup", type=int, default=3, help="busquedas descartadas antes de medir")
    p.add_argument("--points", type=int, default=12, help="valores de N en el punto 4")
    p.add_argument("--periodic", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--csv", help="CSV de salida")
    args = p.parse_args()

    if not os.path.exists(EXE):
        sys.exit(f"no encuentro {EXE}: compila primero con cmake --build build")
    if args.csv is None:
        args.csv = f"data/bench_p{args.part}.csv"
    if args.part == 4 and args.M is None:
        sys.exit("--part 4 necesita --M (el optimo que sale del punto 3)")

    (part3 if args.part == 3 else part4)(args)


if __name__ == "__main__":
    main()
