#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace ht_cost_ns {
constexpr double kPi = 3.14159265358979323846;
struct Point { double x = 0, y = 0, z = 0; };
// The CMU ground controller uses planar goal distance (stopDisThre=0.2 m).
// Consume nearby route vertices before that controller stops at them.
inline bool waypointReached(const Point& robot, const Point& target, double tolerance) {
  return std::hypot(target.x-robot.x,target.y-robot.y)<=tolerance;
}
struct Cost {
  double length = 0, risk = 0, unknown_length = 0;
  bool fully_known = true;
  double total(double weight, double unknown_penalty) const {
    return length + weight * risk + unknown_penalty * unknown_length;
  }
};

// Canonical storage: row increases along -map X, column along -map Y.
// The ROS decoder removes the GridMap circular buffer before constructing this.
struct Map {
  int rows = 0, cols = 0;
  double resolution = 0, center_x = 0, center_y = 0, yaw = 0, stamp = 0;
  double heading_offset = 0;
  std::array<int, 8> channel_order{{0,1,2,3,4,5,6,7}};
  std::array<std::vector<float>, 8> probabilities;
  std::vector<unsigned char> valid;

  bool wellFormed() const {
    if (rows <= 0 || cols <= 0 || !std::isfinite(resolution) || resolution <= 0 ||
        !std::isfinite(center_x) || !std::isfinite(center_y) ||
        !std::isfinite(yaw) || !std::isfinite(stamp) || !std::isfinite(heading_offset))
      return false;
    const auto size = static_cast<size_t>(rows) * cols;
    if (valid.size() != size) return false;
    auto order = channel_order;
    std::sort(order.begin(), order.end());
    for (int k = 0; k < 8; ++k)
      if (order[k] != k || probabilities[k].size() != size) return false;
    return true;
  }
  bool fresh(double now, double timeout) const {
    return std::isfinite(now) && now >= stamp && now - stamp <= timeout;
  }
  double sample(double x, double y, double heading) const {
    if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(heading))
      return std::numeric_limits<double>::quiet_NaN();
    const double dx = x-center_x, dy = y-center_y;
    const double mx = std::cos(yaw)*dx + std::sin(yaw)*dy;
    const double my = -std::sin(yaw)*dx + std::cos(yaw)*dy;
    const double rx = rows*0.5-mx/resolution, cy = cols*0.5-my/resolution;
    if (rx < 0 || cy < 0 || rx >= rows || cy >= cols)
      return std::numeric_limits<double>::quiet_NaN();
    const auto index = static_cast<size_t>(std::floor(rx))*cols +
                       static_cast<size_t>(std::floor(cy));
    if (!valid[index]) return std::numeric_limits<double>::quiet_NaN();
    double angle = std::fmod(heading-yaw-heading_offset, 2*kPi);
    if (angle < 0) angle += 2*kPi;
    const int channel = channel_order[static_cast<int>(std::floor(angle/(kPi/4)+0.5))%8];
    const double p = probabilities[channel][index];
    return std::isfinite(p) && p >= 0 && p <= 1 ? p :
           std::numeric_limits<double>::quiet_NaN();
  }
};

inline Cost segment(const Map* map, const Point& a, const Point& b, double step) {
  if (!std::isfinite(step) || step <= 0) throw std::invalid_argument("Invalid HT sample step");
  Cost result;
  const double dx=b.x-a.x, dy=b.y-a.y, dz=b.z-a.z;
  result.length=std::hypot(std::hypot(dx,dy),dz);
  if (!std::isfinite(result.length)) throw std::invalid_argument("Non-finite path");
  if (result.length == 0) return result;
  if (map == nullptr) {
    result.unknown_length=result.length;
    result.fully_known=false;
    return result;
  }
  const double actual_step=std::min(step, map->resolution/2);
  const double count=std::ceil(result.length/actual_step);
  if (count > 1000000) throw std::invalid_argument("HT segment sampling budget exceeded");
  const int n=std::max(1, static_cast<int>(count));
  const double ds=result.length/n, heading=std::atan2(dy,dx);
  // Midpoint quadrature makes constant-terrain cost independent of sample count.
  for (int i=0;i<n;++i) {
    const double t=(i+0.5)/n;
    const double p=map->sample(a.x+t*dx,a.y+t*dy,heading);
    if (!std::isfinite(p)) {
      result.unknown_length+=ds;
      result.fully_known=false;
    } else result.risk+=ds*(-std::log(std::max(p,0.001)));
  }
  return result;
}
}  // namespace ht_cost_ns
