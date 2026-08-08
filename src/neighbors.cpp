#include "neighbors.hpp"

#include "geometry.hpp"

NeighborLists brute_force_neighbors(const std::vector<Particle>& particles,
                                    double L, double rc, bool periodic) {
    const int n = static_cast<int>(particles.size());
    NeighborLists neighbors(n);

    // d_ij == d_ji, so each pair is tested once and recorded on both sides.
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (within_cutoff(particles[i], particles[j], rc, L, periodic)) {
                neighbors[i].push_back(j);
                neighbors[j].push_back(i);
            }
        }
    }
    return neighbors;
}
