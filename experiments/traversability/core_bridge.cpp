// Batch adapter using the production HT integration and cost implementation.
#include "ht_cost/ht_cost_core.h"
#include <iomanip>
#include <iostream>

int main() {
  using namespace ht_cost_ns;
  std::cout << std::setprecision(17);
  int route_count;
  if (!(std::cin >> route_count) || route_count < 1) return 1;
  for (int route = 0; route < route_count; ++route) {
    int count;
    std::cin >> count;
    Cost total;
    for (int section = 0; section < count; ++section) {
      double length, heading, grade;
      int valid;
      std::cin >> length >> heading >> grade >> valid;
      Map map;
      map.rows = map.cols = 1;
      map.resolution = 1000;  // Each fixture section is spatially uniform.
      map.valid = {static_cast<unsigned char>(valid)};
      for (auto& channel : map.probabilities) {
        double p;
        std::cin >> p;
        if (p < 0 || p > 1 || !std::isfinite(p)) return 2;
        channel = {static_cast<float>(p)};
      }
      if (!std::cin || !map.wellFormed() || length <= 0 || length > 100) return 3;
      const double angle = heading*kPi/180;
      const Point end{length*std::cos(angle), length*std::sin(angle), length*std::tan(grade*kPi/180)};
      const auto cost = segment(&map, {}, end, 0.02);
      total.length += cost.length;
      total.risk += cost.risk;
      total.unknown_length += cost.unknown_length;
      total.fully_known = total.fully_known && cost.fully_known;
    }
    std::cout << total.length << ' ' << total.risk << ' ' << total.unknown_length
              << ' ' << total.fully_known;
    for (double weight : {0., .5, 1., 2., 5.})
      std::cout << ' ' << total.total(weight, 2.);
    std::cout << '\n';
  }
}
