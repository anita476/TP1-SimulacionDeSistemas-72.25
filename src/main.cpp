#include <algorithm>
#include <argparse/argparse.hpp>
#include <chrono>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "generator.hpp"
#include "io.hpp"
#include "neighbors.hpp"
#include "particle.hpp"

int main(int argc, char* argv[]) {
    argparse::ArgumentParser program("CIM-TP1");

    program.add_argument("-N").help("number of particles").default_value(1000).scan<'i', int>();
    program.add_argument("-L").help("side of the square domain").default_value(20.0).scan<'g', double>();
    program.add_argument("-M").help("cells per side; 0 uses the maximum allowed").default_value(0).scan<'i', int>();
    program.add_argument("--rmin").help("minimum particle radius").default_value(0.23).scan<'g', double>();
    program.add_argument("--rmax").help("maximum particle radius").default_value(0.26).scan<'g', double>();
    program.add_argument("--rc").help("interaction radius").default_value(1.0).scan<'g', double>();
    program.add_argument("--method").help("neighbour search: cim | cim-ll | brute | none").default_value(std::string("cim"));
    program.add_argument("--periodic").help("use periodic boundary conditions").flag();
    program.add_argument("--seed").help("RNG seed").default_value(std::string("42"));
    program.add_argument("--attempts").help("rejection budget per particle").default_value(20000).scan<'i', int>();
    program.add_argument("--verify").help("run the O(N^2) overlap check on the configuration").flag();
    program.add_argument("--input-static").help("read the configuration instead of generating it").default_value(std::string(""));
    program.add_argument("--input-dynamic").help("positions that go with --input-static").default_value(std::string(""));
    program.add_argument("--static-out").help("static output file").default_value(std::string("data/static.txt"));
    program.add_argument("--dynamic-out").help("dynamic output file").default_value(std::string("data/dynamic.txt"));
    program.add_argument("--neighbors-out").help("neighbour list output file").default_value(std::string("data/neighbors.txt"));
    program.add_argument("--repeat").help("time the search this many times").default_value(1).scan<'i', int>();
    program.add_argument("--csv").help("append one timing row per run to this file").default_value(std::string(""));
    program.add_argument("--tag").help("label written in the first CSV column").default_value(std::string(""));
    program.add_argument("--trace").help("write a CIM sweep trace here for python/animate_cim.py").default_value(std::string(""));

    try {
        program.parse_args(argc, argv);
    } catch (const std::exception& err) {
        std::cerr << err.what() << '\n' << program;
        return 1;
    }

    try {
        const bool periodic = program.get<bool>("--periodic");
        const double rc = program.get<double>("--rc");
        const std::string in_static = program.get<std::string>("--input-static");
        const std::string in_dynamic = program.get<std::string>("--input-dynamic");

        if (rc < 0.0) {
            std::cerr << "error: rc must be non-negative\n";
            return 1;
        }
        if (in_static.empty() != in_dynamic.empty()) {
            std::cerr << "error: --input-static and --input-dynamic go together\n";
            return 1;
        }

        std::vector<Particle> particles;
        double L = 0.0;

        if (!in_static.empty()) {
            if (program.is_used("-N") || program.is_used("-L")) {
                std::cerr << "warning: -N and -L are ignored when reading a configuration; "
                             "N and L come from the files\n";
            }
            Configuration config = read_configuration(in_static, in_dynamic);
            particles = std::move(config.particles);
            L = config.L;
            std::cerr << "read " << particles.size() << " particles from " << in_static
                      << " and " << in_dynamic << " | L=" << L << '\n';
        } else {
            GeneratorConfig cfg;
            cfg.N = program.get<int>("-N");
            cfg.L = program.get<double>("-L");
            cfg.r_min = program.get<double>("--rmin");
            cfg.r_max = program.get<double>("--rmax");
            cfg.max_attempts = program.get<int>("--attempts");
            cfg.periodic = periodic;

            const std::string seed_text = program.get<std::string>("--seed");
            try {
                cfg.seed = std::stoull(seed_text);
            } catch (const std::exception&) {
                std::cerr << "error: --seed '" << seed_text << "' is not a non-negative integer\n";
                return 1;
            }

            GeneratorStats stats;
            particles = generate_particles(cfg, &stats);
            L = cfg.L;

            write_static(program.get<std::string>("--static-out"), particles, L);
            write_dynamic(program.get<std::string>("--dynamic-out"), particles);

            std::cerr << "generated " << particles.size() << " particles in " << stats.seconds << " s"
                      << " | placement grid " << stats.grid_side << "x" << stats.grid_side
                      << " | attempts/particle " << static_cast<double>(stats.attempts) / std::max(cfg.N, 1)
                      << " | packing fraction " << stats.packing_fraction << '\n';
        }

        if (program.get<bool>("--verify")) {
            const int bad = find_overlap(particles, L, periodic);
            if (bad >= 0) {
                std::cerr << "verification failed: particle " << bad << " overlaps\n";
                return 2;
            }
            std::cerr << "verification passed\n";
        }

        // Cell size criteria
        const double r_max = max_radius(particles);
        const int m_max = cim_max_grid_side(L, rc, r_max);
        int M = program.get<int>("-M");

        if (m_max < 1) {
            std::cerr << "error: rc + 2*r_max = " << rc + 2.0 * r_max
                      << " does not fit in a box of side " << L << ": no valid M exists\n";
            return 1;
        }
        if (M == 0) {
            M = m_max;  // 0 means "use the finest grid the criterion allows"
        } else if (M < 1 || M > m_max) {
            std::cerr << "error: M=" << M << " is out of range 1.." << m_max
                      << " for L=" << L << ", rc=" << rc << ", r_max=" << r_max
                      << " (the cell side L/M must be at least rc + 2*r_max = "
                      << rc + 2.0 * r_max << ")\n";
            return 1;
        }

        std::cerr << "grid: M=" << M << " (max " << m_max << ") | cell " << L / M
                  << " >= rc + 2*r_max = " << rc + 2.0 * r_max << '\n';

        const std::string method = program.get<std::string>("--method");
        if (method == "none") return 0;
        if (method != "brute" && method != "cim" && method != "cim-ll") {
            std::cerr << "error: unknown --method '" << method << "' (cim | cim-ll | brute | none)\n";
            return 1;
        }
        // Both cell structures sweep the same grid, so both honour --trace and
        // both are bound by the same M criterion checked above.
        const bool is_cim = method == "cim" || method == "cim-ll";

        // Tracing writes one line per pair test, so it is only ever meant for the
        // small runs the animator replays. A timing run leaves --trace empty and
        // the sink null.
        const std::string trace_path = program.get<std::string>("--trace");
        std::ofstream trace_file;
        if (!trace_path.empty()) {
            if (!is_cim) {
                std::cerr << "error: --trace only applies to --method cim or cim-ll\n";
                return 1;
            }
            std::filesystem::path parent = std::filesystem::path(trace_path).parent_path();
            if (!parent.empty()) std::filesystem::create_directories(parent);
            trace_file.open(trace_path);
            if (!trace_file) {
                std::cerr << "error: cannot open " << trace_path << " for writing\n";
                return 1;
            }
        }
        std::ostream* trace = trace_file.is_open() ? &trace_file : nullptr;

        const int repeat = program.get<int>("--repeat");
        if (repeat < 1) {
            std::cerr << "error: --repeat must be >= 1\n";
            return 1;
        }
        // Every run would write the whole sweep again, appending one trace after
        // another into a file the animator reads as a single sweep, and the
        // writing would land inside the clock.
        if (trace && repeat > 1) {
            std::cerr << "error: --trace needs --repeat 1 (it would write the sweep "
                         "once per run, and time the writing)\n";
            return 1;
        }

        // Which search to call is resolved here and not inside the loop: leaving
        // the string comparison between t0 and the call would put it in the
        // measurement. Brute force ignores the grid arguments, so a captureless
        // lambda gives it the shared signature.
        using SearchFn = NeighborLists (*)(const std::vector<Particle>&, double, double, int, bool,
                                           std::ostream*, CimStats*);
        const SearchFn search =
            method == "cim"    ? &cim_neighbors :
            method == "cim-ll" ? &cim_linked_neighbors :
            +[](const std::vector<Particle>& p, double box, double cut, int, bool per,
                std::ostream*, CimStats*) { return brute_force_neighbors(p, box, cut, per); };

        // The search is run repeat times and every run is timed on its own, so
        // the CSV gets one row per search and the spread is visible instead of
        // averaged away here.
        NeighborLists neighbors;
        std::vector<double> times;
        std::vector<CimStats> stats;
        times.reserve(static_cast<std::size_t>(repeat));
        stats.reserve(static_cast<std::size_t>(repeat));

        for (int run = 0; run < repeat; ++run) {
            CimStats run_stats;

            const auto t0 = std::chrono::steady_clock::now();
            NeighborLists result = search(particles, L, rc, M, periodic, trace, &run_stats);
            const double elapsed =
                std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

            times.push_back(elapsed);
            // Brute force has no grid to build, so its whole run is the sweep.
            if (!is_cim) run_stats.sweep_seconds = elapsed;
            stats.push_back(run_stats);

            // Only now, with the clock stopped: this releases the PREVIOUS run's
            // lists, which is not part of a search. Inside the clock it would be
            // paid by every run except the first, making row 0 of every point
            // cheaper than the rest for no physical reason.
            neighbors = std::move(result);
        }

        // Outside the timed loop: for the CIM this is an extra run, so that the
        // counted columns are on every row without any timed run having paid for
        // them. Brute force builds no grid, so it only has a pair count.
        CimStats counted;
        if (is_cim) {
            counted = cim_untimed_stats(particles, L, rc, M, periodic, method == "cim-ll");
        } else {
            counted.pair_tests = brute_pair_tests(particles.size());
        }
        for (CimStats& s : stats) {
            s.pair_tests = counted.pair_tests;
            s.grid_bytes = counted.grid_bytes;
            s.grid_live_blocks = counted.grid_live_blocks;
        }
        const std::size_t pair_tests = counted.pair_tests;

        std::size_t pairs = 0;
        for (const std::vector<int>& list : neighbors) pairs += list.size();

        write_neighbors(program.get<std::string>("--neighbors-out"), neighbors);

        const std::string csv_path = program.get<std::string>("--csv");
        if (!csv_path.empty()) {
            append_timings(csv_path, program.get<std::string>("--tag"), method,
                           static_cast<int>(particles.size()), L, M, rc, periodic,
                           program.get<std::string>("--seed"), times, stats);
        }

        double mean = 0.0, mean_build = 0.0, mean_sweep = 0.0;
        for (double t : times) mean += t;
        for (const CimStats& s : stats) {
            mean_build += s.build_seconds;
            mean_sweep += s.sweep_seconds;
        }
        const double runs = static_cast<double>(times.size());
        mean /= runs;
        mean_build /= runs;
        mean_sweep /= runs;

        std::cerr << method << ": rc=" << rc << " | " << mean << " s"
                  << (repeat > 1 ? " (mean of " + std::to_string(repeat) + ")" : "") << " | "
                  << pairs / 2 << " pairs | "
                  << static_cast<double>(pairs) / std::max<std::size_t>(neighbors.size(), 1)
                  << " neighbours/particle\n";

        if (is_cim) {
            std::cerr << "  build " << mean_build << " s | sweep " << mean_sweep << " s | "
                      << stats.front().grid_bytes << " B in "
                      << stats.front().grid_live_blocks << " bloques vivos | "
                      << pair_tests << " distance tests\n";
        } else {
            std::cerr << "  " << pair_tests << " distance tests\n";
        }
    } catch (const std::exception& err) {
        std::cerr << "error: " << err.what() << '\n';
        return 1;
    }

    return 0;
}
