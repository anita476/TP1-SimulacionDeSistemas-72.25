#pragma once

#include <vector>

#include "particle.hpp"

// neighbours[i] holds the ids of the particles whose border-to-border distance
// to particle i is below rc. The relation is symmetric, so j appears in
// neighbours[i] exactly when i appears in neighbours[j].
using NeighborLists = std::vector<std::vector<int>>;

// Measures every pair: N*(N-1)/2 distance tests.
NeighborLists brute_force_neighbors(const std::vector<Particle>& particles, double L, double rc, bool periodic);
