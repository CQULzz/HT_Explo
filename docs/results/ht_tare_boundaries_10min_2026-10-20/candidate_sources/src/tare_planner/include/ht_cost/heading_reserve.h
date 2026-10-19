#pragma once
#include "ht_cost/xytheta_planner.h"

namespace ht_cost_ns {
// Extra planning clearance from a discontinuous eight-channel boundary.
// The caller still checks every nominal swept pose using the hard HT gate.
// Do not require the *measured root* to already have the extra reserve: a
// nominally valid root near a boundary must be able to turn inward again.
template<class Allowed>
bool successorHeadingReserve(Pose2 root,Pose2 previous,Pose2 next,double margin,Allowed allowed) {
  if (margin<=0) return true;
  if (std::hypot(previous.x-root.x,previous.y-root.y)<1e-9 &&
      std::hypot(next.x-root.x,next.y-root.y)<1e-9 &&
      std::abs(wrapYaw(previous.yaw-root.yaw))<1e-9 &&
      std::abs(wrapYaw(next.yaw-root.yaw))<1e-9) return true;
  Pose2 low=next,high=next;
  low.yaw=wrapYaw(low.yaw-margin);high.yaw=wrapYaw(high.yaw+margin);
  return allowed(low) && allowed(high);
}
}
