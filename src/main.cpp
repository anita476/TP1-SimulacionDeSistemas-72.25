#include <algorithm>
#include <argparse/argparse.hpp>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "generator.hpp"
#include "particle.hpp"

namespace {

// Creates the output folder if the caller asked for one that does not exist yet.
void ensure_parent_dir(const std::string& path) {
    const std::filesystem::path parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) std::filesystem::create_directories(parent);
}

// Static file: N, L and then one "radius property" line per particle.
void write_static(const std::string& path, const std::vector<Particle>& particles, double L) {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write " + path);
    out << particles.size() << '\n' << std::setprecision(12) << L << '\n';
    for (const Particle& p : particles) {
        out << p.r << " 1\n";
    }
}

// Dynamic file: a single time t0 followed by "x y vx vy" per particle.
void write_dynamic(const std::string& path, const std::vector<Particle>& particles) {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write " + path);
    out << "0\n" << std::setprecision(12);
    for (const Particle& p : particles) {
        out << p.x << ' ' << p.y << " 0 0\n";
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    argparse::ArgumentParser program("CIM-TP1");

    program.add_argument("-N").help("number of particles").default_value(1000).scan<'i', int>();
    program.add_argument("-L").help("side of the square domain").default_value(20.0).scan<'g', double>();
    program.add_argument("--rmin").help("minimum particle radius").default_value(0.23).scan<'g', double>();
    program.add_argument("--rmax").help("maximum particle radius").default_value(0.26).scan<'g', double>();
    program.add_argument("--seed").help("RNG seed").default_value(std::string("42"));
    program.add_argument("--attempts").help("rejection budget per particle").default_value(20000).scan<'i', int>();
    program.add_argument("--periodic").help("use periodic boundary conditions").flag();
    program.add_argument("--static-out").help("static output file").default_value(std::string("data/static.txt"));
    program.add_argument("--dynamic-out").help("dynamic output file").default_value(std::string("data/dynamic.txt"));
    program.add_argument("--verify").help("run the O(N^2) overlap check on the result").flag();

    try {
        program.parse_args(argc, argv);
    } catch (const std::exception& err) {
        std::cerr << err.what() << '\n' << program;
        return 1;
    }

    GeneratorConfig cfg;
    cfg.N = program.get<int>("-N");
    cfg.L = program.get<double>("-L");
    cfg.r_min = program.get<double>("--rmin");
    cfg.r_max = program.get<double>("--rmax");
    cfg.max_attempts = program.get<int>("--attempts");
    cfg.periodic = program.get<bool>("--periodic");

    try {
        cfg.seed = std::stoull(program.get<std::string>("--seed"));

        GeneratorStats stats;
        const std::vector<Particle> particles = generate_particles(cfg, &stats);

        if (program.get<bool>("--verify")) {
            const int bad = find_overlap(particles, cfg.L, cfg.periodic);
            if (bad >= 0) {
                std::cerr << "verification failed: particle " << bad << " overlaps\n";
                return 2;
            }
            std::cerr << "verification passed\n";
        }

        write_static(program.get<std::string>("--static-out"), particles, cfg.L);
        write_dynamic(program.get<std::string>("--dynamic-out"), particles);

        std::cerr << "generated " << particles.size() << " particles in " << stats.seconds << " s"
                  << " | grid " << stats.grid_side << "x" << stats.grid_side
                  << " | attempts/particle " << static_cast<double>(stats.attempts) / std::max(cfg.N, 1)
                  << " | packing fraction " << stats.packing_fraction << '\n';
    } catch (const std::exception& err) {
        std::cerr << "error: " << err.what() << '\n';
        return 1;
    }

    return 0;
}
