#!/usr/bin/env python3
"""Compares two neighbour lists, ignoring the order within each line.

Brute force emits each list already sorted; the Cell Index Method emits it in
sweep order, so the files are not byte-identical even when they agree. This also
checks the invariants a neighbour list must satisfy.

    python3 python/compare_neighbors.py data/nb_brute.txt data/nb_cim.txt

Exit code 0 when they agree, 1 when they do not.
"""

import argparse
import sys


def load(path):
    lists = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            head, _, rest = line.partition(":")
            lists[int(head)] = [int(x) for x in rest.split()]
    if not lists:
        raise ValueError("no lines")
    return lists


def main():
    p = argparse.ArgumentParser(description="Compara dos listas de vecinas")
    p.add_argument("reference", help="lista de referencia (fuerza bruta)")
    p.add_argument("candidate", help="lista a validar (CIM)")
    p.add_argument("--max-report", type=int, default=5)
    args = p.parse_args()

    try:
        ref, got = load(args.reference), load(args.candidate)
    except (OSError, ValueError) as err:
        sys.exit(f"error: {err}")

    problems = []
    if ref.keys() != got.keys():
        problems.append(f"distinta cantidad de particulas: {len(ref)} vs {len(got)}")

    for i in sorted(ref.keys() & got.keys()):
        mine = got[i]
        if len(mine) != len(set(mine)):
            dups = sorted({x for x in mine if mine.count(x) > 1})
            problems.append(f"particula {i}: vecinas duplicadas {dups}")
        if i in mine:
            problems.append(f"particula {i}: figura como vecina de si misma")
        missing = sorted(set(ref[i]) - set(mine))
        extra = sorted(set(mine) - set(ref[i]))
        if missing or extra:
            problems.append(f"particula {i}: faltan {missing} sobran {extra}")

    asymmetric = [(i, j) for i in got for j in got[i] if i not in got.get(j, [])]
    if asymmetric:
        problems.append(f"pares asimetricos: {asymmetric[:3]}")

    if problems:
        print(f"DIFIEREN ({len(problems)} problemas)")
        for line in problems[:args.max_report]:
            print("  -", line)
        if len(problems) > args.max_report:
            print(f"  ... y {len(problems) - args.max_report} mas")
        sys.exit(1)

    pairs = sum(len(v) for v in ref.values()) // 2
    print(f"IDENTICAS: {len(ref)} particulas, {pairs} pares, "
          f"simetricas, sin duplicados ni auto-vecindad")


if __name__ == "__main__":
    main()
