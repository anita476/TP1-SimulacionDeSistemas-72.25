#pragma once

#include <string>
#include <vector>

#include "neighbors.hpp"
#include "particle.hpp"

// A configuration read from disk
struct Configuration {
    std::vector<Particle> particles;
    double L = 0.0;
};

// Reads a configuration produced by this program
Configuration read_configuration(const std::string& static_path, const std::string& dynamic_path);

void write_static(const std::string& path, const std::vector<Particle>& particles, double L);
void write_dynamic(const std::string& path, const std::vector<Particle>& particles);
void write_neighbors(const std::string& path, const NeighborLists& neighbors);
