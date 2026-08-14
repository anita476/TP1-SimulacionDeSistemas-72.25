#pragma once

#include <algorithm>
#include <cstddef>
#include <iterator>
#include <vector>

// Using A&T linked-list implementation with two integer arrays instead of one heap-allocated container per cell
//  head_[c] = id of the first particle in cell c, or -1 when the cell is empty
//  next_[i] = id of the next particle in i's cell, or -1 at the end of a chain (called LIST in A&T)

class LinkedCellGrid {
public:
    // n is total number of particles: NEXT has one slot per particle so unlike CellGrid this structure has to be sized up front
    LinkedCellGrid(double L, int M, int n)
        : L_(L),
          M_(M),
          head_(static_cast<std::size_t>(M) * static_cast<std::size_t>(M), kNone),
          next_(static_cast<std::size_t>(n > 0 ? n : 0), kNone) {}

    int side() const { return M_; }
    int cell_count() const { return M_ * M_; }
    double cell_size() const { return L_ / M_; }

    int cell_coord(double v) const {
        const int c = static_cast<int>(v * M_ / L_);
        if (c < 0) return 0;
        if (c >= M_) return M_ - 1;
        return c;
    }

    int cell_index(int cx, int cy) const { return cy * M_ + cx; }

    void insert(int id, double x, double y) {
        const int c = cell_index(cell_coord(x), cell_coord(y));
        next_[static_cast<std::size_t>(id)] = head_[static_cast<std::size_t>(c)];
        head_[static_cast<std::size_t>(c)] = id;
    }

    class Iterator {
    public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = int;
        using difference_type = std::ptrdiff_t;
        using pointer = const int*;
        using reference = int;

        Iterator() = default;
        Iterator(int id, const std::vector<int>* next) : id_(id), next_(next) {}

        int operator*() const { return id_; }

        Iterator& operator++() {
            id_ = (*next_)[static_cast<std::size_t>(id_)];
            return *this;
        }
        Iterator operator++(int) {
            Iterator copy = *this;
            ++*this;
            return copy;
        }

        bool operator==(const Iterator& other) const { return id_ == other.id_; }
        bool operator!=(const Iterator& other) const { return id_ != other.id_; }

    private:
        int id_ = kNone;
        const std::vector<int>* next_ = nullptr;
    };

    // Range over one cell, so the sweep can say `for (int j : grid.cell(c))` exactly as it does over CellGrid's vector.
    class Chain {
    public:
        Chain(int first, const std::vector<int>& next) : first_(first), next_(&next) {}

        Iterator begin() const { return Iterator(first_, next_); }
        Iterator end() const { return Iterator(kNone, next_); }
        bool empty() const { return first_ == kNone; }

    private:
        int first_;
        const std::vector<int>* next_;
    };

    Chain cell(int index) const { return Chain(head_[static_cast<std::size_t>(index)], next_); }

    void clear() { std::fill(head_.begin(), head_.end(), kNone); }

    // (M*M + N) ints. Counted like CellGrid::memory_bytes() so the two are comparable
        std::size_t memory_bytes() const {
        return (head_.capacity() + next_.capacity()) * sizeof(int);
    }

    // HEAD and NEXT: always 2. Here held and requested are the same number,
    // because neither array is ever resized.
    std::size_t live_blocks() const {
        return (head_.capacity() > 0 ? 1u : 0u) + (next_.capacity() > 0 ? 1u : 0u);
    }

private:
    static constexpr int kNone = -1;

    double L_;
    int M_;
    std::vector<int> head_;
    std::vector<int> next_;
};
