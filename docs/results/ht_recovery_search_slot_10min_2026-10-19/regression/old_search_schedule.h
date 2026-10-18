#pragma once

#include <cstddef>
#include <stdexcept>
#include <vector>

namespace ht_cost_ns {
// Queue partitions: primary goals, ordinary recovery, then backtracking.
inline std::vector<std::size_t> targetSearchOrder(std::size_t total,
                                                std::size_t primary_end,
                                                std::size_t recovery_end) {
  if (primary_end>recovery_end || recovery_end>total)
    throw std::invalid_argument("Invalid HT target partitions");
  std::vector<std::size_t> order;
  order.reserve(total);
  for (std::size_t i=0;i<total;++i) order.push_back(i);
  return order;
}
}  // namespace ht_cost_ns
