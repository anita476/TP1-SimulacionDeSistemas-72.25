#include "neighbors.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>

#include "cell_grid.hpp"
#include "geometry.hpp"


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

NeighborLists cim_neighbors(const std::vector<Particle> &particles, double L, double rc, int M, bool periodic,
                            std::ostream *trace)
{
    // if periodic && M < 3, the half-shell wraps onto cells it has already visited
    // with M = 2: dx=-1 and dx=+1 land on the same column
    // with M = 1: every offset lands on the focus cell
    if (periodic && M < 3) return brute_force_neighbors(particles, L, rc, periodic);

    const int n = static_cast<int>(particles.size());
    NeighborLists neighbors(n);
    CellGrid grid(L, M);
    // identify exact cell of particles
    for (int i = 0; i < n; ++i) {
        grid.insert(i, particles[i].x, particles[i].y);
    }

    // for tracing
    if (trace) {
        *trace << "L " << L << "\nM " << M << "\nRC " << rc
               << "\nPERIODIC " << (periodic ? 1 : 0) << '\n';
        for (int i = 0; i < n; ++i) {
            *trace << "P " << i << ' ' << particles[i].x << ' ' << particles[i].y
                   << ' ' << particles[i].r << '\n';
        }
        for (int cy = 0; cy < M; ++cy) {
            for (int cx = 0; cx < M; ++cx) {
                const std::vector<int> &ids = grid.cell(grid.cell_index(cx, cy));
                if (ids.empty()) continue;
                *trace << "CELL " << cx << ' ' << cy;
                for (int id : ids) *trace << ' ' << id;
                *trace << '\n';
            }
        }
    }

    auto test_pair = [&](int a, int b, const char *tag) {
        const bool hit = within_cutoff(particles[a], particles[b], rc, L, periodic);
        if (hit) {
            neighbors[a].push_back(b);
            neighbors[b].push_back(a);
        }
        if (trace) *trace << tag << ' ' << a << ' ' << b << ' ' << (hit ? 1 : 0) << '\n';
    };

    for (int cy = 0; cy < M; ++cy) {
        for (int cx = 0; cx < M; ++cx) {
            const std::vector<int> &ids = grid.cell(grid.cell_index(cx, cy));
            const int n_cell = static_cast<int>(ids.size());

            if (n_cell ==0) continue;

            if (trace) *trace << "FOCUS " << cx << ' ' << cy << '\n';

            // own cell
            for (int i = 0; i < n_cell; ++i) {
                for (int j = i + 1; j < n_cell; ++j) {
                    test_pair(ids[i], ids[j], "SELF");
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
                const std::vector<int> &nids = grid.cell(grid.cell_index(nx, ny));
                const int nn_cell = static_cast<int>(nids.size());

                if (trace) *trace << "SHELL " << nx << ' ' << ny << '\n';

                for (int i = 0; i < n_cell; ++i) {
                    for (int j = 0; j < nn_cell; ++j) {
                        test_pair(ids[i], nids[j], "PAIR");
                    }
                }
            }
        }
    }

    return neighbors;
}
