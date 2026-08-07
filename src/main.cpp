#include <stdlib.h>
#include <iostream>
#include <random>
#include <argparse/argparse.hpp>

#define M 10

typedef struct {
    double x, y, r;
} Particle;

// Collection of particles
std::vector<Particle> particles;

// Collection of cells, each with a collection of particles (ids)
std::vector<std::vector<int>> grid(M*M);


int main(int argc, char* argv[]){
  argparse::ArgumentParser program("CIM-TP1");

  program.add_argument("N")
    .help("")
    .default_value(10)
    .required();

  program.add_argument("M")
    
  try {
    program.parse_args(argc, argv);
  }
  catch (const std::exception& err) {
    std::cerr << err.what() << std::endl;
    std::cerr << program;
    return 1;
  }

  auto input = program.get<int>("square");
  std::cout << (input * input) << std::endl;

  return 0;
}

void generate_particles(int N, double L) {
    // Declare map of particles   
    for (int i = 0; i < N; i++) {
        double x = (double)rand() / RAND_MAX * L;
        double y = (double)rand() / RAND_MAX * L;
        // Check superposition
        // Add to map

    }
}

void generate_cells(int m, double l) {
    // Divide the box into M cells
}


double distance(Particle a, Particle b, bool periodic) {
    double dx = b.x - a.x;
    double dy = b.y - a.y;
    if (periodic) {
        // subtract L 
    }

    return sqrt(dx * dx + dy * dy) - a.r - b.r;
}

void check_neighbors() {
    // Continuity condition
    int 
}