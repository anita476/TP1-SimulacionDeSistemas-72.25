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
    // The particle count is accepted but unused: it is there so this class and
    // LinkedCellGrid, which does need it to size its LIST array, can be built
    // from the same expression by the templated sweep in neighbors.cpp.
    CellGrid(double L, int M, int /*n*/ = 0)
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

    // M*M vector headers (24 B each on libc++) plus what each cell reserved.
    // capacity() and not size(), because the doubling leaves reserved slack.
    std::size_t memory_bytes() const {
        std::size_t bytes = cells_.capacity() * sizeof(std::vector<int>);
        for (const std::vector<int>& c : cells_) bytes += c.capacity() * sizeof(int);
        return bytes;
    }

    // Blocks the structure is HOLDING once it is built: one for the outer array
    // and one per non-empty cell. Not the number of requests the allocator saw
    // while building it, which is higher: each cell grows by doubling, so a cell
    // that ends with 6 particles asked four times (1, 2, 4, 8) and freed three.
    // Counted this way to pair with memory_bytes(), which is also what is held.
    std::size_t live_blocks() const {
        std::size_t count = cells_.capacity() > 0 ? 1 : 0;
        for (const std::vector<int>& c : cells_) {
            if (c.capacity() > 0) ++count;
        }
        return count;
    }

private:
    double L_;
    int M_;
    std::vector<std::vector<int>> cells_;
};
