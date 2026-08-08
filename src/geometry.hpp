#pragma once

#include "particle.hpp"

// Shortest signed separation along one axis. Under periodic boundary conditions
// this is the minimum image convention; against walls it is just the raw
// difference. Valid as long as the interaction range stays below L/2, which the
// cell-size criteria in this project already guarantee.
inline double axis_separation(double d, double L, bool periodic) {
    if (!periodic) return d;
    const double half_L = 0.5 * L;
    if (d > half_L) return d - L;
    if (d < -half_L) return d + L;
    return d;
}

// True when the border-to-border distance between the two discs is below cutoff.
//
// This is the single geometric primitive of the project:
//   cutoff = 0   -> the two discs overlap        (used by the generator)
//   cutoff = rc  -> the two discs are neighbours (used by the Cell Index Method)
inline bool within_cutoff(const Particle& a, const Particle& b, double cutoff,
                          double L, bool periodic) {
    const double dx = axis_separation(a.x - b.x, L, periodic);
    const double dy = axis_separation(a.y - b.y, L, periodic);
    const double reach = cutoff + a.r + b.r;
    return dx * dx + dy * dy < reach * reach;
}
