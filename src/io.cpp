#include "io.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace {

constexpr int kDigits = 17;

// Creates the output folder if the caller asked for one that does not exist yet.
void ensure_parent_dir(const std::string& path) {
    const std::filesystem::path parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) std::filesystem::create_directories(parent);
}

[[noreturn]] void fail(const std::string& path, const std::string& what) {
    throw std::runtime_error(path + ": " + what);
}

}

Configuration read_configuration(const std::string& static_path,
                                 const std::string& dynamic_path) {
    std::ifstream sf(static_path);
    if (!sf) fail(static_path, "cannot open for reading");

    std::size_t n = 0;
    double L = 0.0;
    if (!(sf >> n >> L)) fail(static_path, "expected the N and L headings on the first two lines");
    if (n == 0) fail(static_path, "declares 0 particles (is this really a static file?)");
    if (L <= 0.0) fail(static_path, "L must be positive");

    Configuration config;
    config.L = L;

    for (std::size_t i = 0; i < n; ++i) {
        Particle p{};
        if (!(sf >> p.r)) {
            fail(static_path, "expected " + std::to_string(n) + " radii, file ends at " +
                                  std::to_string(i));
        }
        if (p.r <= 0.0) {
            fail(static_path, "radius " + std::to_string(i) + " must be positive");
        }
        config.particles.push_back(p);
        std::string rest;
        std::getline(sf, rest);
    }

    std::ifstream df(dynamic_path);
    if (!df) fail(dynamic_path, "cannot open for reading");

    double time = 0.0;
    if (!(df >> time)) fail(dynamic_path, "expected the time heading on the first line");

    for (std::size_t i = 0; i < n; ++i) {
        Particle& p = config.particles[i];
        if (!(df >> p.x >> p.y)) {
            fail(dynamic_path, "expected " + std::to_string(n) + " positions, file ends at " +
                                   std::to_string(i));
        }
        if (p.x < 0.0 || p.x > L || p.y < 0.0 || p.y > L) {
            std::ostringstream msg;
            msg << "particle " << i << " at (" << p.x << ", " << p.y
                << ") lies outside the box of side " << L
                << " (do the static and dynamic files belong together?)";
            fail(dynamic_path, msg.str());
        }
        std::string rest;
        std::getline(df, rest);  // velocities, if present
    }

    return config;
}

void write_static(const std::string& path, const std::vector<Particle>& particles, double L) {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) fail(path, "cannot open for writing");
    out << particles.size() << '\n' << std::setprecision(kDigits) << L << '\n';
    for (const Particle& p : particles) {
        out << p.r << " 1\n";  // property column: unit mass placeholder
    }
    if (!out) fail(path, "write failed (disk full?)");
}

void write_dynamic(const std::string& path, const std::vector<Particle>& particles) {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) fail(path, "cannot open for writing");
    out << "0\n" << std::setprecision(kDigits);
    for (const Particle& p : particles) {
        out << p.x << ' ' << p.y << " 0 0\n";
    }
    if (!out) fail(path, "write failed (disk full?)");
}

void append_timings(const std::string& path, const std::string& tag, const std::string& method,
                    int N, double L, int M, double rc, bool periodic, const std::string& seed,
                    const std::vector<double>& seconds, std::size_t checks) {
    ensure_parent_dir(path);
    const bool fresh = !std::filesystem::exists(path) || std::filesystem::file_size(path) == 0;

    std::ofstream out(path, std::ios::app);
    if (!out) fail(path, "cannot open for appending");
    if (fresh) out << "tag,method,N,L,M,rc,periodic,seed,run,seconds,checks\n";

    out << std::setprecision(12);
    for (std::size_t run = 0; run < seconds.size(); ++run) {
        out << tag << ',' << method << ',' << N << ',' << L << ',' << M << ',' << rc << ','
            << (periodic ? 1 : 0) << ',' << seed << ',' << run << ',' << seconds[run] << ','
            << checks << '\n';
    }
    if (!out) fail(path, "write failed (disk full?)");
}

void write_neighbors(const std::string& path, const NeighborLists& neighbors) {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) fail(path, "cannot open for writing");
    for (std::size_t i = 0; i < neighbors.size(); ++i) {
        out << i << ':';
        for (int j : neighbors[i]) out << ' ' << j;
        out << '\n';
    }
    if (!out) fail(path, "write failed (disk full?)");
}
