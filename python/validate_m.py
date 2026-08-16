#!/usr/bin/env python3
"""Validates that the Cell Index Method agrees with brute force for every M.

What the cátedra asks for: on ONE configuration, the neighbour list produced with
M > 1 must name exactly the same neighbours as the M = 1 (brute force) list, for
every particle. The order inside each line is irrelevant, so the comparison is
between sets.

Sweeps M from 1 to the maximum the criterion allows, and also checks that M+1
past the maximum is rejected with an error.

    python3 python/validate_m.py
    python3 python/validate_m.py --periodic
    python3 python/validate_m.py -N 500 --rc 2.0 --seeds 1 2 3

Exit code 0 when every M agrees, 1 when any of them does not.
"""

import argparse
import os
import subprocess
import sys
import tempfile

EXE = "./build/CIM-TP1"


def run(args):
    return subprocess.run([EXE] + [str(a) for a in args], capture_output=True, text=True)


def grid_max(stderr):
    """Reads m_max out of the 'grid: M=.. (max ..)' line the simulator prints."""
    for line in stderr.splitlines():
        if line.startswith("grid:"):
            return int(line.split("(max ")[1].split(")")[0])
    return None


def load(path):
    """Parses 'i: j k ...' into {i: set(j, k, ...)}."""
    lists = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            head, _, rest = line.partition(":")
            lists[int(head)] = [int(x) for x in rest.split()]
    if not lists:
        raise ValueError(f"{path}: no hay lineas")
    return lists


def check(reference, candidate, M):
    """Every invariant a neighbour list must satisfy, plus equality with the reference."""
    problems = []
    if reference.keys() != candidate.keys():
        problems.append(f"distinta cantidad de particulas: "
                        f"{len(reference)} vs {len(candidate)}")

    for i in sorted(reference.keys() & candidate.keys()):
        mine = candidate[i]
        if len(mine) != len(set(mine)):
            dups = sorted({x for x in mine if mine.count(x) > 1})
            problems.append(f"particula {i}: vecinas duplicadas {dups}")
        if i in mine:
            problems.append(f"particula {i}: figura como vecina de si misma")
        missing = sorted(set(reference[i]) - set(mine))
        extra = sorted(set(mine) - set(reference[i]))
        if missing or extra:
            problems.append(f"particula {i}: faltan {missing[:6]} sobran {extra[:6]}")

    asymmetric = [(i, j) for i in candidate for j in candidate[i]
                  if i not in candidate.get(j, [])]
    if asymmetric:
        problems.append(f"pares asimetricos: {asymmetric[:3]}")
    return problems


def validate(args, seed, tmp):
    """Sweeps M for one configuration. Returns True when every M agrees."""
    label = (f"N={args.N} L={args.L:g} rc={args.rc:g} seed={seed} "
             f"{'periodico' if args.periodic else 'paredes'}")
    static = os.path.join(tmp, "static.txt")
    dynamic = os.path.join(tmp, "dynamic.txt")

    gen = ["-N", args.N, "-L", args.L, "--rc", args.rc, "--seed", seed,
           "--rmin", args.rmin, "--rmax", args.rmax, "--method", "none",
           "--static-out", static, "--dynamic-out", dynamic]
    if args.periodic:
        gen.append("--periodic")
    result = run(gen)
    if result.returncode != 0:
        print(f"  {label}: NO SE PUDO GENERAR -> "
              f"{result.stderr.strip().splitlines()[-1]}")
        return False

    # Every M reads the same configuration off disk, so the only thing that
    # changes between runs is the grid.
    cfg = ["--input-static", static, "--input-dynamic", dynamic, "--rc", args.rc]
    if args.periodic:
        cfg.append("--periodic")

    ref_path = os.path.join(tmp, "brute.txt")
    result = run(cfg + ["--method", "brute", "--neighbors-out", ref_path])
    if result.returncode != 0:
        print(f"  {label}: fuerza bruta fallo -> {result.stderr.strip()}")
        return False
    m_max = grid_max(result.stderr)
    reference = load(ref_path)
    pairs = sum(len(v) for v in reference.values()) // 2

    print(f"  {label} | M de 1 a {m_max} | {pairs} pares de referencia")

    ok = True
    for M in range(1, m_max + 1):
        got_path = os.path.join(tmp, f"cim_{M}.txt")
        result = run(cfg + ["--method", "cim", "-M", M, "--neighbors-out", got_path])
        if result.returncode != 0:
            print(f"    M={M:<3} ERROR (exit {result.returncode}): "
                  f"{result.stderr.strip().splitlines()[-1]}")
            ok = False
            continue

        problems = check(reference, load(got_path), M)
        if problems:
            ok = False
            print(f"    M={M:<3} DIFIERE ({len(problems)} problemas)")
            for line in problems[:args.max_report]:
                print("          -", line)
            if len(problems) > args.max_report:
                print(f"          ... y {len(problems) - args.max_report} mas")
        elif args.verbose:
            print(f"    M={M:<3} identica a fuerza bruta")

    # The assignment asks for an error past the maximum, not a silently wrong list.
    result = run(cfg + ["--method", "cim", "-M", m_max + 1,
                        "--neighbors-out", os.path.join(tmp, "over.txt")])
    if result.returncode == 0:
        print(f"    M={m_max + 1:<3} DEBIO FALLAR: supera el maximo y fue aceptado")
        ok = False
    elif args.verbose:
        print(f"    M={m_max + 1:<3} rechazado, como corresponde")

    print(f"    -> {'TODOS LOS M COINCIDEN' if ok else 'HAY DIFERENCIAS'}")
    return ok


def main():
    p = argparse.ArgumentParser(
        description="Valida el CIM contra fuerza bruta para todo M de 1 al maximo")
    p.add_argument("-N", type=int, default=1000, help="cantidad de particulas")
    p.add_argument("-L", type=float, default=20.0, help="lado del area")
    p.add_argument("--rc", type=float, default=1.0, help="radio de interaccion")
    p.add_argument("--rmin", type=float, default=0.23)
    p.add_argument("--rmax", type=float, default=0.26)
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3],
                   help="una configuracion distinta por semilla")
    p.add_argument("--periodic", action="store_true",
                   help="solo contorno periodico (por defecto corre los dos)")
    p.add_argument("--walls", action="store_true",
                   help="solo paredes (por defecto corre los dos)")
    p.add_argument("--max-report", type=int, default=5)
    p.add_argument("--verbose", action="store_true", help="una linea por cada M")
    args = p.parse_args()

    if not os.path.exists(EXE):
        sys.exit(f"no encuentro {EXE}: compila primero con cmake --build build")

    modes = []
    if not args.periodic:
        modes.append(False)
    if not args.walls:
        modes.append(True)
    if not modes:
        sys.exit("--periodic y --walls son excluyentes")

    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        for periodic in modes:
            args.periodic = periodic
            print(f"\n{'Contorno periodico' if periodic else 'Paredes'}:")
            for seed in args.seeds:
                ok &= validate(args, seed, tmp)

    print("\nVALIDACION OK: el CIM da las mismas vecinas que la fuerza bruta para todo M"
          if ok else "\nVALIDACION FALLIDA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
