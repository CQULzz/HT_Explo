#pragma once
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <cmath>
#include <vector>

namespace ht_cost_ns {
// Measured obstacles only. Unknown terrain is still checked independently by HT.
// Same cylindrical envelope as ViewPointManager::InCollisionAtPose; no exemption
// for the current pose, no conversion of low neural scores into point obstacles.
class MeasuredCollisionField {
 public:
  using Cloud=pcl::PointCloud<pcl::PointXYZ>;
  void update(Cloud::Ptr cloud) {
    cloud_=std::move(cloud);
    if (!cloud_->empty()) tree_.setInputCloud(cloud_);
  }
  double clearance(double x,double y,double z,double radius,double extra,double z_plus,double z_minus) {
    if (!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||!cloud_) return -INFINITY;
    if (cloud_->empty()) return INFINITY;
    pcl::PointXYZ query;query.x=x;query.y=y;query.z=z;
    std::vector<int> ids;std::vector<float> squared;
    const double rounding=std::hypot(double(query.x)-x,double(query.y)-y)+std::abs(double(query.z)-z);
    tree_.radiusSearch(query,std::hypot(radius+extra,std::max(z_plus,z_minus))+rounding+1e-5,ids,squared);
    double distance=INFINITY;
    for (int id:ids) {
      const auto& p=cloud_->points[id];const double dz=p.z-z;
      if (dz<=z_plus && dz>=-z_minus) distance=std::min(distance,std::hypot(double(p.x)-x,double(p.y)-y));
    }
    return distance-radius;
  }
  bool blocked(double x,double y,double z,double radius,double z_plus,double z_minus) {
    if (!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||!cloud_) return true;
    if (cloud_->empty()) return false;
    pcl::PointXYZ query;query.x=x;query.y=y;query.z=z;
    std::vector<int> ids;std::vector<float> squared;
    tree_.radiusSearch(query,std::hypot(radius,std::max(z_plus,z_minus))+1e-5,ids,squared);
    for (int id:ids) {
      const auto& p=cloud_->points[id];const double dz=p.z-z;
      if (dz<=z_plus && dz>=-z_minus && std::hypot(p.x-x,p.y-y)<=radius+1e-7) return true;
    }
    return false;
  }
 private:
  Cloud::Ptr cloud_;
  pcl::KdTreeFLANN<pcl::PointXYZ> tree_{false};
};
}
