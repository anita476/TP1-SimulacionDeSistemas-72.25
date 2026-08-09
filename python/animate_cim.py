"""Replays a Cell Index Method trace as an animation.

    ./build/CIM-TP1 -N 40 -L 20 --rc 2.0 -M 5 --method cim --trace data/trace.txt
    python python/animate_cim.py --trace data/trace.txt --out figures/cim.gif

Trace grammar (one event per line):

    L <L> | M <M> | RC <rc> | PERIODIC <0|1>
    P     <id> <x> <y> <r>          one per particle
    CELL  <cx> <cy> <id>...         occupancy after insertion
    FOCUS <cx> <cy>                 a cell becomes the focus
    SHELL <nx> <ny>                 a half-shell cell is opened
    SELF  <a> <b> <0|1>             self-cell pair tested
    PAIR  <a> <b> <0|1>             cross-cell pair tested
"""

import argparse
import sys
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle, Rectangle

FOCUS_COLOR = "#ffd54f"
SHELL_COLOR = "#b3e5fc"
DONE_COLOR = "#e8e8e8"
HIT_COLOR = "#2e7d32"
MISS_COLOR = "#c62828"
PARTICLE_COLOR = "#cfcfcf"


@dataclass
class Trace:
    L: float = 0.0
    M: int = 0
    rc: float = 0.0
    periodic: bool = False
    particles: dict = field(default_factory=dict)   # id -> (x, y, r)
    cells: dict = field(default_factory=dict)       # (cx, cy) -> [ids]
    events: list = field(default_factory=list)      # (kind, payload)


def read_trace(path):
    t = Trace()
    with open(path) as fh:
        for raw in fh:
            parts = raw.split()
            if not parts:
                continue
            tag, rest = parts[0], parts[1:]
            if tag == "L":
                t.L = float(rest[0])
            elif tag == "M":
                t.M = int(rest[0])
            elif tag == "RC":
                t.rc = float(rest[0])
            elif tag == "PERIODIC":
                t.periodic = rest[0] == "1"
            elif tag == "P":
                t.particles[int(rest[0])] = tuple(float(v) for v in rest[1:4])
            elif tag == "CELL":
                t.cells[(int(rest[0]), int(rest[1]))] = [int(v) for v in rest[2:]]
            elif tag == "FOCUS":
                t.events.append(("FOCUS", (int(rest[0]), int(rest[1]))))
            elif tag == "SHELL":
                t.events.append(("SHELL", (int(rest[0]), int(rest[1]))))
            elif tag in ("SELF", "PAIR"):
                t.events.append((tag, (int(rest[0]), int(rest[1]), rest[2] == "1")))
    if not t.events:
        sys.exit(f"{path}: no events (did you pass --trace to the simulator?)")
    return t


def build_frames(trace, stride, max_frames):
    """Turn the flat event list into drawable states.

    Each frame carries what has been *settled* so far as well as what is happening
    now, so the picture answers "how much is left?" and not only "where am I?":

        done    cells already retired as focus -- their pairs will never be
                revisited, which is the half-shell guarantee made visible
        missed  pairs tested and rejected, kept faint
        found   pairs tested and accepted

    Every FOCUS and SHELL gets its own frame so the cell sweep stays legible;
    pair tests are subsampled by `stride`, since a dense run has thousands.
    """
    frames, focus, shell = [], None, None
    done, found, missed = [], [], []
    n_focus = sum(1 for kind, _ in trace.events if kind == "FOCUS")
    for i, (kind, payload) in enumerate(trace.events):
        if kind == "FOCUS":
            # The previous focus is finished the moment a new one opens.
            if focus is not None:
                done.append(focus)
            focus, shell = payload, None
        elif kind == "SHELL":
            shell = payload
        else:
            a, b, hit = payload
            (found if hit else missed).append((a, b))
            if i % stride:
                continue
            frames.append((focus, shell, (a, b, hit), list(done), list(found), list(missed)))
            continue
        frames.append((focus, shell, None, list(done), list(found), list(missed)))
    frames.append((None, None, None, done + ([focus] if focus else []), found, missed))
    if len(frames) > max_frames:
        keep = len(frames) / max_frames
        frames = [frames[int(k * keep)] for k in range(max_frames)]
        print(f"note: subsampled to {max_frames} frames; raise --max-frames for more")
    return frames, n_focus


def segments(pairs, particles):
    """Flatten pairs into one NaN-separated polyline -- far cheaper than a Line2D each."""
    xs, ys = [], []
    for a, b in pairs:
        xa, ya, _ = particles[a]
        xb, yb, _ = particles[b]
        xs += [xa, xb, float("nan")]
        ys += [ya, yb, float("nan")]
    return xs, ys


def render(trace, frames, n_focus, out, fps):
    L, M = trace.L, trace.M
    cell = L / M

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-0.02 * L, 1.02 * L)
    ax.set_ylim(-0.02 * L, 1.02 * L)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])

    # Static layers, drawn once: grid lines, then every particle at true scale.
    for k in range(M + 1):
        ax.axhline(k * cell, color="#dddddd", lw=0.8, zorder=0)
        ax.axvline(k * cell, color="#dddddd", lw=0.8, zorder=0)
    ax.add_patch(Rectangle((0, 0), L, L, fill=False, ec="black", lw=1.5, zorder=5))
    for x, y, r in trace.particles.values():
        ax.add_patch(Circle((x, y), r, fc=PARTICLE_COLOR, ec="#909090", lw=0.5, zorder=3))

    # One reusable patch per cell for the "already retired as focus" layer. Cheaper
    # than rebuilding patches each frame, and it is the layer that answers
    # "what is left to do?".
    done_patches = {}
    for cy in range(M):
        for cx in range(M):
            patch = Rectangle((cx * cell, cy * cell), cell, cell,
                              fc=DONE_COLOR, alpha=0.9, zorder=0.5)
            patch.set_visible(False)
            ax.add_patch(patch)
            done_patches[(cx, cy)] = patch

    # Dynamic layers, replaced every frame.
    focus_patch = Rectangle((0, 0), cell, cell, fc=FOCUS_COLOR, alpha=0.55, zorder=1)
    shell_patch = Rectangle((0, 0), cell, cell, fc=SHELL_COLOR, alpha=0.55, zorder=1)
    focus_patch.set_visible(False)
    shell_patch.set_visible(False)
    ax.add_patch(focus_patch)
    ax.add_patch(shell_patch)

    missed_lines = ax.plot([], [], color=MISS_COLOR, lw=0.6, alpha=0.14, zorder=3.5)[0]
    found_lines = ax.plot([], [], color=HIT_COLOR, lw=1.0, alpha=0.5, zorder=4)[0]
    test_line = ax.plot([], [], lw=2.2, zorder=6)[0]
    title = ax.set_title("", fontsize=11, family="monospace")

    legend = [
        Rectangle((0, 0), 1, 1, fc=DONE_COLOR, label="cell done"),
        Rectangle((0, 0), 1, 1, fc=FOCUS_COLOR, alpha=0.55, label="focus"),
        Rectangle((0, 0), 1, 1, fc=SHELL_COLOR, alpha=0.55, label="half-shell"),
    ]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=3, frameon=False, fontsize=9)

    def draw(idx):
        focus, shell, test, done, found, missed = frames[idx]

        done_set = set(done)
        for cellpos, patch in done_patches.items():
            patch.set_visible(cellpos in done_set)

        for patch, cellpos in ((focus_patch, focus), (shell_patch, shell)):
            patch.set_visible(cellpos is not None)
            if cellpos is not None:
                patch.set_xy((cellpos[0] * cell, cellpos[1] * cell))

        missed_lines.set_data(*segments(missed, trace.particles))
        found_lines.set_data(*segments(found, trace.particles))

        if test is None:
            test_line.set_data([], [])
            label = "done" if focus is None else \
                f"focus {focus}" + (f"  ->  shell {shell}" if shell else "")
        else:
            a, b, hit = test
            xa, ya, _ = trace.particles[a]
            xb, yb, _ = trace.particles[b]
            test_line.set_data([xa, xb], [ya, yb])
            test_line.set_color(HIT_COLOR if hit else MISS_COLOR)
            kind = "self " if shell is None else "shell"
            label = f"{kind}  {a:>3} - {b:<3}  {'NEIGHBOUR' if hit else 'too far'}"

        cells_done = len(done_set) + (1 if focus is not None else 0)
        title.set_text(
            f"M={M}  rc={trace.rc}   {label}\n"
            f"cells {cells_done}/{n_focus}    "
            f"tested {len(found) + len(missed)}    found {len(found)}")
        return focus_patch, shell_patch, found_lines, missed_lines, test_line, title

    anim = FuncAnimation(fig, draw, frames=len(frames), blit=False, interval=1000 / fps)
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)
    print(f"{len(frames)} frames -> {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--trace", default="data/trace.txt", help="trace written by the simulator")
    p.add_argument("--out", default="figures/cim.gif", help="output GIF")
    p.add_argument("--stride", type=int, default=1, help="draw every Nth pair test")
    p.add_argument("--max-frames", type=int, default=600, help="cap on total frames")
    p.add_argument("--fps", type=int, default=8)
    args = p.parse_args()

    trace = read_trace(args.trace)
    frames, n_focus = build_frames(trace, max(args.stride, 1), args.max_frames)
    render(trace, frames, n_focus, args.out, args.fps)


if __name__ == "__main__":
    main()
