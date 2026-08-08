#pragma once

#include <cstdint>
#include <vector>

#include "particle.hpp"

struct GeneratorConfig {
    int N = 1000;                       // number of particles
    double L = 20.0;                    // side of the square
    double r_min = 0.23;
    double r_max = 0.26;
    bool periodic = false;
    std::uint64_t seed = 0;
    int max_attempts = 20000;
};

struct GeneratorStats {
    long long attempts = 0;
    int grid_side = 0;                  // M used by the acceptance grid
    double packing_fraction = 0.0;
    double seconds = 0.0;
};

// Generates N non-overlapping discs.
std::vector<Particle> generate_particles(const GeneratorConfig& cfg, GeneratorStats* stats = nullptr);

// Check that no pair of particles overlaps.
int find_overlap(const std::vector<Particle>& particles, double L, bool periodic);
