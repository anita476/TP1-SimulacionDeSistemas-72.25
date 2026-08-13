#!/usr/bin/env python3
"""Draws the particle configuration produced by the simulator.

Covers the figure required by point 1 of the assignment: every particle at its
real radius, one of them highlighted, and its neighbours in a different colour.

    python python/visualize.py --particle 0 --neighbors data/neighbors.txt

An interactive mode is also available: instead of rendering one static PNG for
one particle, it opens a window where you click any particle to select it (or
step through ids with n/p) and its neighbours update live.

    python python/visualize.py --neighbors data/neighbors.txt --interactive
    python python/visualize.py --rc 1.5 --periodic --interactive   # no file: neighbours computed on the fly

The simulator writes the input files; this script only reads them. Keeping the
two apart is the pipeline the course asks for: SIMULATION -> files -> ANALYSIS.
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
from matplotlib.widgets import Slider

OTHER_FACE = "#d9d9d9"
OTHER_EDGE = "#9e9e9e"
NEIGHBOUR = "#1f77b4"
TARGET = "#d62728"
GHOST = "#8c564b"


def read_static(path):
    """Returns (L, [radius per particle]) from the static file: N, L, then 'r prop'."""
    with open(path) as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if len(lines) < 2:
        raise ValueError(f"{path}: expected at least the N and L headers")
    n = int(lines[0])
    box = float(lines[1])
    radii = [float(ln.split()[0]) for ln in lines[2:2 + n]]
    if len(radii) != n:
        raise ValueError(f"{path}: header says {n} particles but found {len(radii)}")
    return box, radii


def read_dynamic(path, n):
    """Returns [(x, y)] for the first time frame of the dynamic file."""
    with open(path) as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if not lines:
        raise ValueError(f"{path}: file is empty")
    rows = lines[1:1 + n]  # lines[0] is the time heading
    if len(rows) != n:
        raise ValueError(f"{path}: expected {n} particles, found {len(rows)}")
    return [(float(p[0]), float(p[1])) for p in (ln.split() for ln in rows)]


def read_neighbors(path, index_base):
    """Parses 'id_i: id_j id_k ...' (the colon is optional) into {id: [ids]}."""
    table = {}
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            head, _, tail = ln.partition(":")
            if not _:  # no colon: first token is the particle, rest are neighbours
                tokens = ln.split()
                head, tail = tokens[0], " ".join(tokens[1:])
            table[int(head) - index_base] = [int(t) - index_base for t in tail.split()]
    return table


def minimum_image(d, box, periodic):
    """Shortest signed separation along one axis; mirrors axis_separation() in C++."""
    if not periodic:
        return d
    if d > 0.5 * box:
        return d - box
    if d < -0.5 * box:
        return d + box
    return d


def neighbours_by_distance(target, positions, radii, box, periodic, rc):
    """Neighbour ids whose border-to-border distance to the target is below rc.

    Mirrors within_cutoff() in C++, radii of both discs included and the
    comparison strict, so a click reproduces exactly what the simulator writes.
    Used in interactive mode when no --neighbors file was given.
    """
    tx, ty = positions[target]
    found = []
    for j, (px, py) in enumerate(positions):
        if j == target:
            continue
        dx = minimum_image(px - tx, box, periodic)
        dy = minimum_image(py - ty, box, periodic)
        limit = radii[target] + radii[j] + rc
        if dx * dx + dy * dy < limit * limit:
            found.append(j)
    return found


def render(ax, box, radii, positions, target, neighbours, rc, periodic, title):
    """Draws one frame on `ax`, clearing whatever was there before.

    Shared by the static (one PNG) and interactive (redrawn on click) paths so
    the two never drift apart visually.
    """
    ax.clear()

    highlighted = set(neighbours) | ({target} if target is not None else set())
    ghosts = []  # periodic images drawn outside the box; widen the view for them

    # Everything not highlighted goes into one collection, which stays fast even
    # when N is large.
    background = [Circle(positions[i], radii[i])
                  for i in range(len(radii)) if i not in highlighted]
    ax.add_collection(PatchCollection(background, facecolor=OTHER_FACE,
                                      edgecolor=OTHER_EDGE, linewidths=0.5))

    for i in neighbours:
        ax.add_patch(Circle(positions[i], radii[i], facecolor=NEIGHBOUR,
                            edgecolor="black", linewidth=0.6, zorder=3))

    if target is not None:
        tx, ty = positions[target]
        ax.add_patch(Circle((tx, ty), radii[target], facecolor=TARGET,
                            edgecolor="black", linewidth=0.9, zorder=5))

        # Everything whose border falls inside this dashed ring is a neighbour:
        # the ring sits exactly rc away from the target's surface.
        if rc is not None:
            ax.add_patch(Circle((tx, ty), radii[target] + rc, fill=False,
                                edgecolor=TARGET, linestyle="--", linewidth=1.2,
                                alpha=0.8, zorder=4))

        # A segment to each neighbour. Under periodic boundaries the segment is
        # drawn towards the minimum image, so pairs that interact through a wall
        # visibly leave the box, and a faded ghost shows where that image is.
        for j in neighbours:
            raw_x, raw_y = positions[j][0] - tx, positions[j][1] - ty
            dx, dy = minimum_image(raw_x, box, periodic), minimum_image(raw_y, box, periodic)
            gx, gy = tx + dx, ty + dy
            ax.plot([tx, gx], [ty, gy], color=TARGET, linewidth=0.8,
                    alpha=0.5, zorder=2)
            # Only a pair that actually wrapped gets a ghost. Comparing the
            # separations, not the reconstructed positions, keeps this exact:
            # tx + (px - tx) does not always round back to px.
            if dx != raw_x or dy != raw_y:
                ghosts.append((gx, gy, radii[j]))
                ax.add_patch(Circle((gx, gy), radii[j], facecolor=GHOST,
                                    edgecolor="black", linewidth=0.5,
                                    alpha=0.35, zorder=2))

    ax.add_patch(plt.Rectangle((0, 0), box, box, fill=False,
                               edgecolor="black", linewidth=1.2))

    margin = 0.04 * box
    lo_x, hi_x, lo_y, hi_y = -margin, box + margin, -margin, box + margin
    for gx, gy, gr in ghosts:  # keep periodic images fully inside the view
        lo_x, hi_x = min(lo_x, gx - gr - margin), max(hi_x, gx + gr + margin)
        lo_y, hi_y = min(lo_y, gy - gr - margin), max(hi_y, gy + gr + margin)
    ax.set_xlim(lo_x, hi_x)
    ax.set_ylim(lo_y, hi_y)
    ax.set_aspect("equal")  # circles must look like circles
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title)

    handles = [Line2D([], [], marker="o", linestyle="", markerfacecolor=OTHER_FACE,
                      markeredgecolor=OTHER_EDGE, label="resto")]
    if target is not None:
        handles.append(Line2D([], [], marker="o", linestyle="", markerfacecolor=TARGET,
                              markeredgecolor="black", label=f"partícula {target}"))
        handles.append(Line2D([], [], marker="o", linestyle="", markerfacecolor=NEIGHBOUR,
                              markeredgecolor="black",
                              label=f"vecinas ({len(neighbours)})"))
        if rc is not None:
            handles.append(Line2D([], [], color=TARGET, linestyle="--",
                                  label=f"borde + rc = {rc:g}"))
    if ghosts:
        handles.append(Line2D([], [], marker="o", linestyle="", alpha=0.35,
                              markerfacecolor=GHOST, markeredgecolor="black",
                              label="imagen periódica"))
    # Outside the axes: inside it would hide particles.
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=3, frameon=False)


def plot(box, radii, positions, target, neighbours, rc, periodic, title, out_path, show):
    fig, ax = plt.subplots(figsize=(8, 8))
    render(ax, box, radii, positions, target, neighbours, rc, periodic, title)
    fig.tight_layout()
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150)
        print(f"figura guardada en {out_path}")
    if show:
        plt.show()
    plt.close(fig)


def closest_particle(positions, radii, x, y):
    """Id of the particle whose circle contains (x, y), or None if none does.

    Ties (overlapping circles) go to whichever centre is nearest the click.
    """
    best, best_d2 = None, None
    for i, (px, py) in enumerate(positions):
        d2 = (px - x) ** 2 + (py - y) ** 2
        if d2 <= radii[i] ** 2 and (best_d2 is None or d2 < best_d2):
            best, best_d2 = i, d2
    return best


def run_interactive(box, radii, positions, table, rc, periodic, start, index_base):
    """Opens a window: click a particle to select it, n/p to step, q to quit.

    Neighbours come from `table` (the --neighbors file) when it's not None;
    otherwise, if --rc was given, they're computed on the fly from distance.
    """
    n = len(radii)
    ids = sorted(table.keys()) if table is not None else list(range(n))
    if not ids:
        sys.exit("no hay partículas para mostrar en modo interactivo")

    state = {"target": start if start in ids else ids[0]}

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.subplots_adjust(bottom=0.17)
    slider_ax = fig.add_axes((0.2, 0.04, 0.6, 0.03))
    slider = Slider(slider_ax, "id", ids[0], ids[-1],
                    valinit=state["target"], valstep=ids if len(ids) > 1 else None)

    def neighbours_of(target):
        if table is not None:
            return [j for j in table.get(target, []) if j != target]
        if rc is not None:
            return neighbours_by_distance(target, positions, radii, box, periodic, rc)
        return []

    def redraw():
        target = state["target"]
        neighbours = neighbours_of(target)
        boundary = "contorno periódico" if periodic else "paredes"
        title = (f"N={n}  L={box:g}  ({boundary})\n"
                 f"partícula {target}: {len(neighbours)} vecinas   "
                 f"[click = seleccionar, n/p = siguiente/anterior, q = salir]")
        render(ax, box, radii, positions, target, neighbours, rc, periodic, title)
        slider.eventson = False
        slider.set_val(target)
        slider.eventson = True
        fig.canvas.draw_idle()

    def select(new_target):
        if new_target in ids and new_target != state["target"]:
            state["target"] = new_target
            redraw()

    def on_click(event):
        if event.inaxes != ax or event.xdata is None:
            return
        picked = closest_particle(positions, radii, event.xdata, event.ydata)
        if picked is not None:
            select(picked)

    def on_key(event):
        if event.key == "q":
            plt.close(fig)
            return
        if event.key not in ("n", "p"):
            return
        pos = ids.index(state["target"])
        pos = (pos + 1) % len(ids) if event.key == "n" else (pos - 1) % len(ids)
        select(ids[pos])

    def on_slider(val):
        # valstep already snaps to a valid id when the table restricts the set.
        select(min(ids, key=lambda i: abs(i - val)))

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)
    slider.on_changed(on_slider)

    redraw()
    plt.show()

def main():
    p = argparse.ArgumentParser(description="Visualizador de partículas y vecinas (TP1)")
    p.add_argument("--static", default="data/static.txt", help="archivo estático")
    p.add_argument("--dynamic", default="data/dynamic.txt", help="archivo dinámico")
    p.add_argument("--neighbors", help="archivo de vecinas 'id: id id ...'")
    p.add_argument("--particle", type=int, help="id de la partícula a resaltar")
    p.add_argument("--rc", type=float, help="radio de interacción, para dibujar el anillo")
    p.add_argument("--periodic", action="store_true",
                   help="contorno periódico: dibuja las imágenes mínimas")
    p.add_argument("--index-base", type=int, default=0, choices=(0, 1),
                   help="base de los ids en el archivo de vecinas (default 0)")
    p.add_argument("--out", default="figures/neighbors.png", help="PNG de salida")
    p.add_argument("--show", action="store_true", help="abrir la figura en una ventana")
    p.add_argument("--interactive", action="store_true",
                   help="ventana interactiva: click en una partícula para "
                        "seleccionarla (o --rc sin --neighbors para calcular "
                        "las vecinas en el momento)")
    args = p.parse_args()

    if not args.show and not args.interactive:
        matplotlib.use("Agg")  # no display needed when only saving

    try:
        box, radii = read_static(args.static)
        positions = read_dynamic(args.dynamic, len(radii))
    except (OSError, ValueError) as err:
        sys.exit(f"error leyendo los archivos de entrada: {err}")

    target = args.particle
    if target is not None and not (0 <= target < len(radii)):
        sys.exit(f"--particle {target} fuera de rango: hay {len(radii)} partículas (0..{len(radii) - 1})")

    table = None
    if args.neighbors:
        try:
            table = read_neighbors(args.neighbors, args.index_base)
        except (OSError, ValueError) as err:
            sys.exit(f"error leyendo {args.neighbors}: {err}")

    if args.interactive:
        if table is None and args.rc is None:
            sys.exit("--interactive necesita --neighbors o --rc para saber "
                      "quiénes son vecinas")
        run_interactive(box, radii, positions, table, args.rc, args.periodic,
                        target if target is not None else 0, args.index_base)
        return

    neighbours = []
    if args.neighbors:
        if target is None:
            sys.exit("--neighbors requiere --particle para saber a quién resaltar")
        neighbours = [j for j in table.get(target, []) if j != target]

    boundary = "contorno periódico" if args.periodic else "paredes"
    title = f"N={len(radii)}  L={box:g}  ({boundary})"
    if target is not None:
        title += f"\npartícula {target}: {len(neighbours)} vecinas"

    plot(box, radii, positions, target, neighbours, args.rc, args.periodic,
         title, args.out, args.show)


if __name__ == "__main__":
    main()