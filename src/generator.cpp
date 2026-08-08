#include "generator.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>
#include <sstream>
#include <stdexcept>

#include "cell_grid.hpp"
#include "geometry.hpp"

namespace {

constexpr double kPi = 3.14159265358979323846;

// Side of the acceptance grid.
//
// Correctness bound: two particles overlap only if their centres are closer
// than r_i + r_j <= 2*r_max, so a cell side of at least 2*r_max guarantees that
// every overlapping partner lives in the 3x3 block around the candidate cell.
int choose_grid_side(const GeneratorConfig& cfg) {
    const int m_geometry = static_cast<int>(std::floor(cfg.L / (2.0 * cfg.r_max)));
    const int m_density = static_cast<int>(std::ceil(std::sqrt(static_cast<double>(std::max(cfg.N, 1)))));
    return std::max(1, std::min(m_geometry, m_density));
}

void validate(const GeneratorConfig& cfg) {
    if (cfg.N < 0) throw std::invalid_argument("N must be non-negative");
    if (cfg.L <= 0.0) throw std::invalid_argument("L must be positive");
    if (cfg.r_min <= 0.0) throw std::invalid_argument("r_min must be positive");
    if (cfg.r_max < cfg.r_min) throw std::invalid_argument("r_max must be >= r_min");
    if (cfg.max_attempts < 1) throw std::invalid_argument("max_attempts must be >= 1");
    if (cfg.L <= 2.0 * cfg.r_max) {
        throw std::invalid_argument("L must be larger than the diameter of the largest particle");
    }
}

// Does the candidate overlap any of the particles already inserted into the grid?
// Only the 3x3 block of cells around the candidate is scanned, which is enough
// because the cell side is at least 2*r_max.
bool overlaps_placed(const Particle& candidate, const std::vector<Particle>& placed,
                     const CellGrid& grid, double L, bool periodic) {
    const int M = grid.side();
    const int cx = grid.cell_coord(candidate.x);
    const int cy = grid.cell_coord(candidate.y);

    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            int nx = cx + dx;
            int ny = cy + dy;
            if (periodic) {
                nx = (nx + M) % M;
                ny = (ny + M) % M;
            } else if (nx < 0 || nx >= M || ny < 0 || ny >= M) {
                continue;
            }
            for (int j : grid.cell(grid.cell_index(nx, ny))) {
                if (within_cutoff(candidate, placed[j], 0.0, L, periodic)) return true;
            }
        }
    }
    return false;
}

}

std::vector<Particle> generate_particles(const GeneratorConfig& cfg, GeneratorStats* stats) {
    validate(cfg);

    const auto t0 = std::chrono::steady_clock::now();

    const double L = cfg.L;
    const int M = choose_grid_side(cfg);

    std::vector<Particle> particles;
    particles.reserve(static_cast<std::size_t>(cfg.N));

    CellGrid grid(L, M);

    std::mt19937_64 rng(cfg.seed);
    std::uniform_real_distribution<double> unit(0.0, 1.0);

    long long attempts = 0;
    double sum_area = 0.0;

    for (int i = 0; i < cfg.N; ++i) {
        const double r = cfg.r_min + unit(rng) * (cfg.r_max - cfg.r_min);

        // If periodic, the particle can be placed anywhere in [0,L)
        const double lo = cfg.periodic ? 0.0 : r;
        const double span = cfg.periodic ? L : L - 2.0 * r;

        bool placed = false;
        for (int attempt = 0; attempt < cfg.max_attempts && !placed; ++attempt) {
            ++attempts;

            const Particle candidate{lo + unit(rng) * span, lo + unit(rng) * span, r};

            if (!overlaps_placed(candidate, particles, grid, L, cfg.periodic)) {
                grid.insert(i, candidate.x, candidate.y);
                particles.push_back(candidate);
                sum_area += kPi * r * r;
                placed = true;
            }
        }

        if (!placed) {
            std::ostringstream msg;
            msg << "could not place particle " << i + 1 << "/" << cfg.N << " after "
                << cfg.max_attempts << " attempts (packing fraction reached "
                << sum_area / (L * L)
                << "; random sequential addition jams around 0.547): lower N or raise L";
            throw std::runtime_error(msg.str());
        }
    }

    if (stats != nullptr) {
        const auto t1 = std::chrono::steady_clock::now();
        stats->attempts = attempts;
        stats->grid_side = M;
        stats->packing_fraction = sum_area / (L * L);
        stats->seconds = std::chrono::duration<double>(t1 - t0).count();
    }

    return particles;
}

int find_overlap(const std::vector<Particle>& particles, double L, bool periodic) {
    const int n = static_cast<int>(particles.size());
    for (int i = 0; i < n; ++i) {
        const Particle& a = particles[i];
        if (!periodic && (a.x < a.r || a.x > L - a.r || a.y < a.r || a.y > L - a.r)) {
            return i;  // sticking out of a wall
        }
        for (int j = i + 1; j < n; ++j) {
            if (within_cutoff(a, particles[j], 0.0, L, periodic)) return i;
        }
    }
    return -1;
}
