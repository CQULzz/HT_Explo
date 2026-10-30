// Offline scaling benchmark. Synthetic history only, not vehicle/HT frequency.
// g++ -std=c++17 -O3 -I src/tare_planner/include tools/benchmark_terrain_history.cpp -o /new/path/benchmark
#include "ht_cost/terrain_history.h"
#include <chrono>
#include <iostream>
#include <iomanip>
#include <stdexcept>
using ht_cost_ns::TerrainCell;
using ht_cost_ns::TerrainHistory;
using Flat=std::map<TerrainHistory::Key,TerrainCell>;
using Clock=std::chrono::steady_clock;
volatile size_t consumed=0;
std::vector<TerrainCell> reference(const Flat& history,double r) {
  std::vector<TerrainCell> out;
  for(const auto& item:history) {
    const auto& c=item.second;
    if(std::abs(c.x)<=r && std::abs(c.y)<=r && std::isfinite(c.height)) out.push_back(c);
  }
  return out;
}
void equal(const std::vector<TerrainCell>& a,const std::vector<TerrainCell>& b) {
  if(a.size()!=b.size())throw std::runtime_error("window size mismatch");
  for(size_t i=0;i<a.size();++i)
    if(a[i].x!=b[i].x || a[i].y!=b[i].y || a[i].height!=b[i].height ||
       a[i].stamp!=b[i].stamp || a[i].feasible!=b[i].feasible)
      throw std::runtime_error("cell content/order mismatch");
}
template<class F> double elapsed(F f) {
  auto start=Clock::now();f();return std::chrono::duration<double,std::micro>(Clock::now()-start).count();
}
int main() {
  std::cout<<std::setprecision(12);
  std::cout<<"cells,radius,repeat,baseline_us,indexed_us,returned,candidate_cells,columns,flat_build_us,indexed_build_us\n";
  for(int distant:{0,100000,400000,1000000}) {
    std::vector<std::pair<TerrainHistory::Key,TerrainCell>> input;
    for(int x=-100;x<=100;++x)for(int y=-100;y<=100;++y)
      input.push_back({{x,y},{x*.2+.05,y*.2+.05,.1,1,(x+y)%3!=0}});
    for(int i=0;i<distant;++i) {
      const int x=10000+i/1000,y=10000+i%1000;
      input.push_back({{x,y},{x*.2+.05,y*.2+.05,i%11 ? .2 : NAN,2,true}});
    }
    Flat flat;TerrainHistory indexed;
    const double fb=elapsed([&]{for(const auto& c:input)flat[c.first]=c.second;});
    const double ib=elapsed([&]{for(const auto& c:input)indexed[c.first]=c.second;});
    // Include a full-history negative control; an index need not win when all
    // cells are requested. Two unreported warmups retain all later slow calls.
    for(double radius:{1.,10.,40.,1e9}) {
      TerrainHistory::QueryStats stats;
      auto a=reference(flat,radius),b=indexed.window(0,0,radius,&stats);equal(a,b);
      for(int w=0;w<2;++w){consumed=reference(flat,radius).size();consumed=indexed.window(0,0,radius).size();}
      for(int rep=0;rep<12;++rep) {
        double before,after;
        auto run_before=[&]{before=elapsed([&]{a=reference(flat,radius);});};
        auto run_after=[&]{after=elapsed([&]{b=indexed.window(0,0,radius);});};
        if(rep%2){run_after();run_before();}else{run_before();run_after();}
        equal(a,b);consumed=a.size()+b.size();
        std::cout<<flat.size()<<','<<radius<<','<<rep<<','<<before<<','<<after<<','
                 <<a.size()<<','<<stats.candidates<<','<<stats.columns<<','<<fb<<','<<ib<<'\n';
      }
    }
  }
}
