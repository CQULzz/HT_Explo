#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <map>
#include <utility>
#include <vector>

namespace ht_cost_ns {
struct TerrainCell {
  double x=0,y=0,height=std::numeric_limits<double>::quiet_NaN(),stamp=0;
  bool feasible=false;
};

// Same 0.2m guidance cells and lexicographic order as the original flat map.
// Two ordered axes avoid scanning distant history for a local window. This
// index does not expire, evict, aggregate or otherwise change observations.
class TerrainHistory {
 public:
  using Key=std::pair<int,int>;
  struct QueryStats {size_t columns=0,candidates=0;};
  TerrainCell& operator[](Key key) {
    auto& column=columns_[key.first];
    auto inserted=column.emplace(key.second,TerrainCell{});
    if(inserted.second) ++size_;
    return inserted.first->second;
  }
  const TerrainCell* find(Key key) const {
    const auto column=columns_.find(key.first);
    if(column==columns_.end()) return nullptr;
    const auto cell=column->second.find(key.second);
    return cell==column->second.end() ? nullptr : &cell->second;
  }
  size_t size() const {return size_;}
  std::vector<TerrainCell> window(double x,double y,double radius,
                                  QueryStats* stats=nullptr) const {
    if(stats) *stats=QueryStats{};
    std::vector<TerrainCell> result;
    if(std::isnan(x) || std::isnan(y) || std::isnan(radius) || radius<0) return result;
    // Preserve the old predicate even for non-finite query arguments. Normal
    // finite queries use bounded ranges; only this compatibility case scans.
    const bool finite=std::isfinite(x) && std::isfinite(y) && std::isfinite(radius);
    // At huge magnitudes abs(c.x-x)<=radius may accept points outside the
    // rounded interval [x-radius,x+radius] (catastrophic cancellation). Keep
    // the reference scan when query roundoff is no longer small vs a bin.
    const bool bounded=finite && std::max({std::abs(x),std::abs(y),radius})*
      std::numeric_limits<double>::epsilon()<.2/16;
    const auto xb=bounded ? bounds(x,radius) : fullBounds();
    const auto yb=bounded ? bounds(y,radius) : fullBounds();
    auto column=columns_.lower_bound(xb.first);
    for(;column!=columns_.end() && column->first<=xb.second;++column) {
      if(stats) ++stats->columns;
      auto cell=column->second.lower_bound(yb.first);
      for(;cell!=column->second.end() && cell->first<=yb.second;++cell) {
        if(stats) ++stats->candidates;
        const auto& c=cell->second;
        // Exact original inclusive predicate, using observed coordinates
        // rather than the coarse-cell center. Also filters NaN wall heights.
        if(std::abs(c.x-x)<=radius && std::abs(c.y-y)<=radius && std::isfinite(c.height))
          result.push_back(c);
      }
    }
    return result;
  }
 private:
  static Key fullBounds() {return {std::numeric_limits<int>::min(),std::numeric_limits<int>::max()};}
  static int clipped(double index) {
    const auto all=fullBounds();
    if(index<=all.first) return all.first;
    if(index>=all.second) return all.second;
    return static_cast<int>(index);
  }
  static Key bounds(double center,double radius) {
    // Include one extra bin on both sides so rounding at negative/positive
    // cell and window boundaries cannot hide an originally accepted point.
    return {clipped(std::floor((center-radius)/.2)-1),
            clipped(std::floor((center+radius)/.2)+1)};
  }
  std::map<int,std::map<int,TerrainCell>> columns_;
  size_t size_=0;
};
}
