#pragma once
#include <array>
#include <cstdlib>

namespace ht_cost_ns {
// Neighboring grid centers alone do not establish a traversable diagonal.
// Every cell touching the crossed corner/edge must support the connection.
// This also covers an off-center robot's segment to the next route vertex.
template <typename CellSupported>
bool gridEdgeSupported(const std::array<int, 3>& from,
                       const std::array<int, 3>& to,
                       CellSupported supported) {
  unsigned changed = 0;
  for (unsigned axis = 0; axis < 3; ++axis) {
    if (std::abs(to[axis] - from[axis]) > 1) return false;
    if (from[axis] != to[axis]) changed |= 1u << axis;
  }
  for (unsigned mask = 0; mask < 8; ++mask) {
    if (mask & ~changed) continue;
    auto cell = from;
    for (unsigned axis = 0; axis < 3; ++axis)
      if (mask & (1u << axis)) cell[axis] = to[axis];
    if (!supported(cell)) return false;
  }
  return true;
}
}  // namespace ht_cost_ns
