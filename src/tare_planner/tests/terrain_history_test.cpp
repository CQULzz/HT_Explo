#include "ht_cost/terrain_history.h"
#include <gtest/gtest.h>
#include <random>
#include <array>
using ht_cost_ns::TerrainCell;
using ht_cost_ns::TerrainHistory;
using Key=TerrainHistory::Key;
using Flat=std::map<Key,TerrainCell>;
namespace {
std::vector<TerrainCell> reference(const Flat& flat,double x,double y,double radius) {
  std::vector<TerrainCell> out;
  for(const auto& item:flat) {
    const auto& c=item.second;
    if(std::abs(c.x-x)<=radius && std::abs(c.y-y)<=radius && std::isfinite(c.height)) out.push_back(c);
  }
  return out;
}
void same(const std::vector<TerrainCell>& a,const std::vector<TerrainCell>& b) {
  ASSERT_EQ(a.size(),b.size());
  for(size_t i=0;i<a.size();++i) {
    EXPECT_EQ(a[i].x,b[i].x);EXPECT_EQ(a[i].y,b[i].y);
    EXPECT_EQ(a[i].height,b[i].height);EXPECT_EQ(a[i].stamp,b[i].stamp);
    EXPECT_EQ(a[i].feasible,b[i].feasible);
  }
}
void put(TerrainHistory& indexed,Flat& flat,const TerrainCell& c) {
  const Key key{static_cast<int>(std::floor(c.x/.2)),static_cast<int>(std::floor(c.y/.2))};
  indexed[key]=c;flat[key]=c;
}
}
TEST(TerrainHistory, RandomRollingUpdatesAndWindowOrderMatchOriginal) {
  TerrainHistory index;Flat flat;std::mt19937 gen(20261030);
  std::uniform_real_distribution<double> pos(-100,100),radius(0,40);
  for(int i=0;i<20000;++i)put(index,flat,{pos(gen),pos(gen),i%11 ? .001*i : NAN,double(i),i%3==0});
  EXPECT_EQ(index.size(),flat.size());
  for(int i=0;i<200;++i) {
    const double x=pos(gen),y=pos(gen),r=radius(gen);
    same(index.window(x,y,r),reference(flat,x,y,r));
  }
  for(const auto& item:flat) {
    const auto* c=index.find(item.first);ASSERT_NE(c,nullptr);
    EXPECT_EQ(c->stamp,item.second.stamp);EXPECT_EQ(c->feasible,item.second.feasible);
  }
  EXPECT_EQ(index.find({10000,10000}),nullptr);
}
TEST(TerrainHistory, BoundariesNegativeCoordinatesAndInvalidQueriesMatchOriginal) {
  TerrainHistory index;Flat flat;
  for(double p:{-1.,-.6,-.2,0.,.2,.6,1.})
    for(double x:{std::nextafter(p,-INFINITY),p,std::nextafter(p,INFINITY)})
      for(double y:{-.2,0.,.2})put(index,flat,{x,y,.1,2,true});
  for(double x:{-.2,0.,.2})for(double r:{0.,.2,.6,1.})same(index.window(x,0,r),reference(flat,x,0,r));
  for(const auto& q:std::vector<std::array<double,3>>{{NAN,0,1},{0,NAN,1},{0,0,NAN},
      {0,0,-1},{0,0,INFINITY},{INFINITY,0,1},{INFINITY,0,INFINITY},{1e300,0,1e300}})
    same(index.window(q[0],q[1],q[2]),reference(flat,q[0],q[1],q[2]));
}
TEST(TerrainHistory, LocalQueryDoesNotVisitDistantRowsOrColumns) {
  TerrainHistory index;Flat flat;put(index,flat,{.1,.1,.2,1,true});
  for(int i=100;i<100100;++i) {
    put(index,flat,{double(i),.1,.3,1,true});put(index,flat,{.1,double(i),.3,1,true});
  }
  TerrainHistory::QueryStats stats;same(index.window(0,0,1,&stats),reference(flat,0,0,1));
  EXPECT_EQ(stats.columns,1u);EXPECT_EQ(stats.candidates,1u);
  put(index,flat,{.12,.13,.4,2,false});
  ASSERT_NE(index.find({0,0}),nullptr);EXPECT_FALSE(index.find({0,0})->feasible);
  same(index.window(0,0,1),reference(flat,0,0,1));
}
