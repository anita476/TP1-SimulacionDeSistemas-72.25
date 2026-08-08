#pragma once

#include <cstddef>
#include <vector>

// Uniform grid of M x M square cells over the [0,L) x [0,L) domain. Each cell
// holds the ids of the particles whose centre falls inside it.
//
// The same structure serves the generator (cell side >= 2*r_max, overlap
// queries) and the Cell Index Method (cell side > rc + 2*r_max, neighbour
// queries); only the chosen M differs.
class CellGrid {
public:
    CellGrid(double L, int M)
        : L_(L), M_(M), cells_(static_cast<std::size_t>(M) * static_cast<std::size_t>(M)) {}

    int side() const { return M_; }
    int cell_count() const { return M_ * M_; }
    double cell_size() const { return L_ / M_; }

    // Cell coordinate of a single axis value. Clamped so that a coordinate
    // landing exactly on L still maps to a valid cell.
    int cell_coord(double v) const {
        const int c = static_cast<int>(v * M_ / L_);
        if (c < 0) return 0;
        if (c >= M_) return M_ - 1;
        return c;
    }

    int cell_index(int cx, int cy) const { return cy * M_ + cx; }

    void insert(int id, double x, double y) {
        cells_[cell_index(cell_coord(x), cell_coord(y))].push_back(id);
    }

    // Iterate a cell with:  for (int j : grid.cell(index)) { ... }
    const std::vector<int>& cell(int index) const { return cells_[index]; }

    void clear() {
        for (std::vector<int>& c : cells_) c.clear();
    }

private:
    double L_;
    int M_;
    std::vector<std::vector<int>> cells_;
};
