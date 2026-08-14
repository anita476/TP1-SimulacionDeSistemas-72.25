#pragma once

#include <cstddef>
#include <iosfwd>
#include <vector>

#include "particle.hpp"

// neighbours[i] holds the ids of the particles whose border-to-border distance
// to particle i is below rc. The relation is symmetric, so j appears in
// neighbours[i] exactly when i appears in neighbours[j].
using NeighborLists = std::vector<std::vector<int>>;

// What one run of the CIM cost, split in two phases: building the grid is where
// the two cell structures differ, sweeping it is where they do the same work.
// build + sweep falls a little short of the total the caller measures; the rest
// is allocating the output lists and tearing the grid down.
//
// The two timings come from a timed run. The three counters do not: measuring
// them costs an M*M walk, so they come from cim_untimed_stats() instead.
struct CimStats {
    double build_seconds = 0.0;        // allocating the grid and filing the N particles
    double sweep_seconds = 0.0;        // the focus cell + half-shell loops
    std::size_t grid_bytes = 0;        // bytes the cell structure itself holds
    std::size_t grid_live_blocks = 0;  // heap blocks it is holding, once built
    std::size_t pair_tests = 0;        // distance tests
};

// Largest number of cells per side the Cell Index Method may use.
int cim_max_grid_side(double L, double rc, double r_max);

// Largest radius in the configuration.
double max_radius(const std::vector<Particle>& particles);

// Measures every pair: N*(N-1)/2 distance tests.
NeighborLists brute_force_neighbors(const std::vector<Particle>& particles, double L, double rc, bool periodic);

// Cell Index Method: MxM grid, own cell + half-shell (L-shape for symmetry) of neighbors
//
// When `trace` is non-null every decision the sweep makes is written to it in the
// grammar python/animate_cim.py replays. Leave it null for timing runs.
//
// The two differ only in how a cell stores its particles: cim_neighbors gives
// each cell its own std::vector, cim_linked_neighbors uses A&T's HEAD/LIST. Same
// sweep, same pairs found; only the order inside each list changes.
NeighborLists cim_neighbors(const std::vector<Particle>& particles, double L, double rc, int M, bool periodic,
                            std::ostream* trace = nullptr, CimStats* stats = nullptr);

NeighborLists cim_linked_neighbors(const std::vector<Particle>& particles, double L, double rc, int M,
                                   bool periodic, std::ostream* trace = nullptr, CimStats* stats = nullptr);


CimStats cim_untimed_stats(const std::vector<Particle>& particles, double L, double rc, int M,
                           bool periodic, bool linked);

// Brute force always tests every unordered pair, so it needs no run to count.
inline std::size_t brute_pair_tests(std::size_t n) { return n * (n - 1) / 2; }