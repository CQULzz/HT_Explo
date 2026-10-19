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
  // A full primary timeout must not spend every cycle before reaching a
  // recovery candidate. Give one ordinary recovery the second slot, while
  // preserving the first primary (including a committed goal) and all tail
  // backtracking priorities. Callers skip recovery if a gain route exists.
  if (primary_end) order.push_back(0);
  if (primary_end<recovery_end) order.push_back(primary_end);
  for (std::size_t i=1;i<primary_end;++i) order.push_back(i);
  for (std::size_t i=primary_end+1;i<recovery_end;++i) order.push_back(i);
  for (std::size_t i=recovery_end;i<total;++i) order.push_back(i);
  return order;
}
}  // namespace ht_cost_ns
