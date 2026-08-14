#include "neighbors.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>

#include "cell_grid.hpp"
#include "geometry.hpp"
#include "linked_cell_grid.hpp"


int cim_max_grid_side(double L, double rc, double r_max)
{
    const double reach = rc + 2.0 * r_max;
    if (reach <= 0.0 || L <= 0.0)
        return 0;
    const int m = static_cast<int>(std::floor(L / reach));
    return m > 0 ? m : 0;
}

double max_radius(const std::vector<Particle> &particles)
{
    double r_max = 0.0;
    for (const Particle &p : particles)
        r_max = std::max(r_max, p.r);
    return r_max;
}

NeighborLists brute_force_neighbors(const std::vector<Particle> &particles,
                                    double L, double rc, bool periodic)
{
    const int n = static_cast<int>(particles.size());
    NeighborLists neighbors(n);

    // d_ij == d_ji, so each pair is tested once and recorded on both sides.
    for (int i = 0; i < n; ++i)
    {
        for (int j = i + 1; j < n; ++j)
        {
            if (within_cutoff(particles[i], particles[j], rc, L, periodic))
            {
                neighbors[i].push_back(j);
                neighbors[j].push_back(i);
            }
        }
    }
    return neighbors;
}

// Half-shell: for every offset d in this table -d is absent, so each pair of adjacent
// cells is visited exactly once, from one side only, and d_ij == d_ji is never counted
// twice.
//
// A&T p. 152 & Teorica 1 p.25. In A&T Fig. 5.5 show the half-shell to be: SE, E, NE and N. That is:
//    NW (no)   N (si)   NE (si)
//     W (no)   ·        E  (si)
//    SW (no)   S (no)   SE (si)

constexpr int kHalfShellCount = 4;
constexpr int kHalfShell[kHalfShellCount][2] = {{+1, -1}, {+1, 0}, {+1, +1}, {0, +1}};


template <class Grid, bool Trace, bool Count>
NeighborLists cim_sweep(const std::vector<Particle> &particles, double L, double rc, int M,
                        bool periodic, std::ostream *trace, CimStats *stats)
{
    using Clock = std::chrono::steady_clock;

    const int n = static_cast<int>(particles.size());
    NeighborLists neighbors(n);

    const auto t_build = Clock::now();
    Grid grid(L, M, n);
    // identify exact cell of particles
    for (int i = 0; i < n; ++i) {
        grid.insert(i, particles[i].x, particles[i].y);
    }
    const auto t_built = Clock::now();

    // for tracing
    if constexpr (Trace) {
        *trace << "L " << L << "\nM " << M << "\nRC " << rc
               << "\nPERIODIC " << (periodic ? 1 : 0) << '\n';
        for (int i = 0; i < n; ++i) {
            *trace << "P " << i << ' ' << particles[i].x << ' ' << particles[i].y
                   << ' ' << particles[i].r << '\n';
        }
        for (int cy = 0; cy < M; ++cy) {
            for (int cx = 0; cx < M; ++cx) {
                const auto &ids = grid.cell(grid.cell_index(cx, cy));
                if (ids.empty()) continue;
                *trace << "CELL " << cx << ' ' << cy;
                for (int id : ids) *trace << ' ' << id;
                *trace << '\n';
            }
        }
    }

    std::size_t pair_tests = 0;

    auto test_pair = [&](int a, int b, [[maybe_unused]] const char *tag) {
        if constexpr (Count) ++pair_tests;
        const bool hit = within_cutoff(particles[a], particles[b], rc, L, periodic);
        if (hit) {
            neighbors[a].push_back(b);
            neighbors[b].push_back(a);
        }
        if constexpr (Trace) *trace << tag << ' ' << a << ' ' << b << ' ' << (hit ? 1 : 0) << '\n';
    };

    // The trace preamble above dumps the whole grid to a stream, so the sweep
    // clock starts here, after it, and not when the build clock stopped.
    const auto t_sweep = Clock::now();

    for (int cy = 0; cy < M; ++cy) {
        for (int cx = 0; cx < M; ++cx) {
            const auto &ids = grid.cell(grid.cell_index(cx, cy));

            if (ids.empty()) continue;

            if constexpr (Trace) *trace << "FOCUS " << cx << ' ' << cy << '\n';

            // own cell: every unordered pair once. Starting from the successor
            // of `it` is the "i < j" of before, now that a cell may be a chain
            // with no indices to compare.
            for (auto it = ids.begin(); it != ids.end(); ++it) {
                auto jt = it;
                for (++jt; jt != ids.end(); ++jt) {
                    test_pair(*it, *jt, "SELF");
                }
            }

            // half-shell
            for (int k = 0; k < kHalfShellCount; ++k)
            {
                int nx = cx + kHalfShell[k][0];
                int ny = cy + kHalfShell[k][1];

                if (periodic) {
                    nx = (nx + M) % M;
                    ny = (ny + M) % M;
                }
                else if (nx < 0 || nx >= M || ny < 0 || ny >= M) {
                    continue; // a wall
                }
                // grab neighbor bucket
                const auto &nids = grid.cell(grid.cell_index(nx, ny));

                if constexpr (Trace) *trace << "SHELL " << nx << ' ' << ny << '\n';

                for (auto it = ids.begin(); it != ids.end(); ++it) {
                    for (auto jt = nids.begin(); jt != nids.end(); ++jt) {
                        test_pair(*it, *jt, "PAIR");
                    }
                }
            }
        }
    }

    if (stats) {
        stats->build_seconds = std::chrono::duration<double>(t_built - t_build).count();
        stats->sweep_seconds = std::chrono::duration<double>(Clock::now() - t_sweep).count();
        // memory_bytes() and live_blocks() walk the M*M cells, which is not work
        // the algorithm does: on CellGrid that is two passes over the whole cell
        // array, on LinkedCellGrid it is O(1), so leaving them in would tax one
        // structure and not the other. They ride along with the pair counter, on
        // the extra pass nobody times.
        if constexpr (Count) {
            stats->grid_bytes = grid.memory_bytes();
            stats->grid_live_blocks = grid.live_blocks();
            stats->pair_tests = pair_tests;
        }
    }

    return neighbors;
}

// Shared by the two entry points, which differ only in the Grid argument.
template <class Grid>
NeighborLists cim_dispatch(const std::vector<Particle> &particles, double L, double rc, int M,
                           bool periodic, std::ostream *trace, CimStats *stats)
{
    if (periodic && M < 3) {
        if (trace) {
            std::cerr << "warning: periodic with M=" << M
                      << " degenerates to all pairs, so no sweep trace is written\n";
        }
        return brute_force_neighbors(particles, L, rc, periodic);
    }
    return trace ? cim_sweep<Grid, true, false>(particles, L, rc, M, periodic, trace, stats)
                 : cim_sweep<Grid, false, false>(particles, L, rc, M, periodic, nullptr, stats);
}

NeighborLists cim_neighbors(const std::vector<Particle> &particles, double L, double rc, int M, bool periodic,
                            std::ostream *trace, CimStats *stats)
{
    return cim_dispatch<CellGrid>(particles, L, rc, M, periodic, trace, stats);
}

NeighborLists cim_linked_neighbors(const std::vector<Particle> &particles, double L, double rc, int M,
                                   bool periodic, std::ostream *trace, CimStats *stats)
{
    return cim_dispatch<LinkedCellGrid>(particles, L, rc, M, periodic, trace, stats);
}

CimStats cim_untimed_stats(const std::vector<Particle> &particles, double L, double rc, int M,
                           bool periodic, bool linked)
{
    CimStats stats;

    // With this grid cim_dispatch falls back to brute force, which measures
    // every pair and builds no grid.
    if (periodic && M < 3) {
        stats.pair_tests = brute_pair_tests(particles.size());
        return stats;
    }

    if (linked) {
        cim_sweep<LinkedCellGrid, false, true>(particles, L, rc, M, periodic, nullptr, &stats);
    } else {
        cim_sweep<CellGrid, false, true>(particles, L, rc, M, periodic, nullptr, &stats);
    }
    // This pass was not timed, so its clock readings mean nothing; the caller
    // takes the times from the runs that were.
    stats.build_seconds = 0.0;
    stats.sweep_seconds = 0.0;
    return stats;
}
