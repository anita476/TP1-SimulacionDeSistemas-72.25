#include "neighbors.hpp"

#include <algorithm>
#include <cmath>

#include "geometry.hpp"

int cim_max_grid_side(double L, double rc, double r_max) {
    const double reach = rc + 2.0 * r_max;
    if (reach <= 0.0 || L <= 0.0) return 0;
    const int m = static_cast<int>(std::floor(L / reach));
    return m > 0 ? m : 0;
}

double max_radius(const std::vector<Particle>& particles) {
    double r_max = 0.0;
    for (const Particle& p : particles) r_max = std::max(r_max, p.r);
    return r_max;
}

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
