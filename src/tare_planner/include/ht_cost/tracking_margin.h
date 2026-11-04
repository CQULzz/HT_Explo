#pragma once
#include <cmath>
namespace ht_cost_ns {
// The physical collision boundary is never relaxed. A vehicle already inside
// the extra tracking buffer may leave it only while increasing its minimum
// distance to measured obstacles. Once outside, the full buffer applies again.
inline bool trackingMarginAllows(double previous_clearance,double next_clearance,double margin) {
  if (!std::isfinite(margin) || margin<0 || std::isnan(previous_clearance) ||
      std::isnan(next_clearance) || previous_clearance<=0 || next_clearance<=0) return false;
  if (next_clearance>margin) return true;
  return previous_clearance<margin && next_clearance>previous_clearance+1e-7;
}
}
