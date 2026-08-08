#pragma once

#include <vector>

#include "particle.hpp"

// neighbours[i] holds the ids of the particles whose border-to-border distance
// to particle i is below rc. The relation is symmetric, so j appears in
// neighbours[i] exactly when i appears in neighbours[j].
using NeighborLists = std::vector<std::vector<int>>;

// Largest number of cells per side the Cell Index Method may use.
int cim_max_grid_side(double L, double rc, double r_max);

// Largest radius in the configuration.
double max_radius(const std::vector<Particle>& particles);

// Measures every pair: N*(N-1)/2 distance tests.
NeighborLists brute_force_neighbors(const std::vector<Particle>& particles, double L, double rc, bool periodic);

