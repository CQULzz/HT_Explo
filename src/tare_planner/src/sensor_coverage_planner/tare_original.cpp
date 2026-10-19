// Upstream TARE ROS2 baseline b6760adb4280b379567c76f4e684ce628e28ef71.
// Function bodies preserved; only method names differ. See docs/plans/2026-10-20_tare_ht_waypoint_plan.md.
#include "sensor_coverage_planner/sensor_coverage_planner_ground.h"
namespace sensor_coverage_planner_3d_ns {
exploration_path_ns::ExplorationPath
SensorCoveragePlanner3D::ConcatenateTarePath(
    const exploration_path_ns::ExplorationPath &global_path,
    const exploration_path_ns::ExplorationPath &local_path) {
  exploration_path_ns::ExplorationPath full_path;
  if (exploration_finished_ && near_home_ && kRushHome) {
    exploration_path_ns::Node node;
    node.position_.x() = robot_position_.x;
    node.position_.y() = robot_position_.y;
    node.position_.z() = robot_position_.z;
    node.type_ = exploration_path_ns::NodeType::ROBOT;
    full_path.nodes_.push_back(node);
    node.position_ = initial_position_;
    node.type_ = exploration_path_ns::NodeType::HOME;
    full_path.nodes_.push_back(node);
    return full_path;
  }

  double global_path_length = global_path.GetLength();
  double local_path_length = local_path.GetLength();
  if (global_path_length < 3 && local_path_length < 5) {
    return full_path;
  } else {
    full_path = local_path;
    if (local_path.nodes_.front().type_ ==
            exploration_path_ns::NodeType::LOCAL_PATH_END &&
        local_path.nodes_.back().type_ ==
            exploration_path_ns::NodeType::LOCAL_PATH_START) {
      full_path.Reverse();
    } else if (local_path.nodes_.front().type_ ==
                   exploration_path_ns::NodeType::LOCAL_PATH_START &&
               local_path.nodes_.back() == local_path.nodes_.front()) {
      full_path.nodes_.back().type_ =
          exploration_path_ns::NodeType::LOCAL_PATH_END;
    } else if (local_path.nodes_.front().type_ ==
                   exploration_path_ns::NodeType::LOCAL_PATH_END &&
               local_path.nodes_.back() == local_path.nodes_.front()) {
      full_path.nodes_.front().type_ =
          exploration_path_ns::NodeType::LOCAL_PATH_START;
    }
  }

  return full_path;
}

bool SensorCoveragePlanner3D::GetTareLookAheadPoint(
    const exploration_path_ns::ExplorationPath &local_path,
    const exploration_path_ns::ExplorationPath &global_path,
    Eigen::Vector3d &lookahead_point) {
  Eigen::Vector3d robot_position(robot_position_.x, robot_position_.y,
                                 robot_position_.z);

  // Determine which direction to follow on the global path
  double dist_from_start = 0.0;
  for (int i = 1; i < global_path.nodes_.size(); i++) {
    dist_from_start +=
        (global_path.nodes_[i - 1].position_ - global_path.nodes_[i].position_)
            .norm();
    if (global_path.nodes_[i].type_ ==
        exploration_path_ns::NodeType::GLOBAL_VIEWPOINT) {
      break;
    }
  }

  double dist_from_end = 0.0;
  for (int i = global_path.nodes_.size() - 2; i > 0; i--) {
    dist_from_end +=
        (global_path.nodes_[i + 1].position_ - global_path.nodes_[i].position_)
            .norm();
    if (global_path.nodes_[i].type_ ==
        exploration_path_ns::NodeType::GLOBAL_VIEWPOINT) {
      break;
    }
  }

  bool local_path_too_short = true;
  for (int i = 0; i < local_path.nodes_.size(); i++) {
    double dist_to_robot =
        (robot_position - local_path.nodes_[i].position_).norm();
    if (dist_to_robot > kLookAheadDistance / 5) {
      local_path_too_short = false;
      break;
    }
  }
  if (local_path.GetNodeNum() < 1 || local_path_too_short) {
    if (dist_from_start < dist_from_end) {
      double dist_from_robot = 0.0;
      for (int i = 1; i < global_path.nodes_.size(); i++) {
        dist_from_robot += (global_path.nodes_[i - 1].position_ -
                            global_path.nodes_[i].position_)
                               .norm();
        if (dist_from_robot > kLookAheadDistance / 2) {
          lookahead_point = global_path.nodes_[i].position_;
          break;
        }
      }
    } else {
      double dist_from_robot = 0.0;
      for (int i = global_path.nodes_.size() - 2; i > 0; i--) {
        dist_from_robot += (global_path.nodes_[i + 1].position_ -
                            global_path.nodes_[i].position_)
                               .norm();
        if (dist_from_robot > kLookAheadDistance / 2) {
          lookahead_point = global_path.nodes_[i].position_;
          break;
        }
      }
    }
    return false;
  }

  bool has_lookahead = false;
  bool dir = true;
  int robot_i = 0;
  int lookahead_i = 0;
  for (int i = 0; i < local_path.nodes_.size(); i++) {
    if (local_path.nodes_[i].type_ == exploration_path_ns::NodeType::ROBOT) {
      robot_i = i;
    }
    if (local_path.nodes_[i].type_ ==
        exploration_path_ns::NodeType::LOOKAHEAD_POINT) {
      has_lookahead = true;
      lookahead_i = i;
    }
  }

  if (reset_waypoint_) {
    has_lookahead = false;
  }

  int forward_viewpoint_count = 0;
  int backward_viewpoint_count = 0;

  bool local_loop = false;
  if (local_path.nodes_.front() == local_path.nodes_.back() &&
      local_path.nodes_.front().type_ == exploration_path_ns::NodeType::ROBOT) {
    local_loop = true;
  }

  if (local_loop) {
    robot_i = 0;
  }
  for (int i = robot_i + 1; i < local_path.GetNodeNum(); i++) {
    if (local_path.nodes_[i].type_ ==
        exploration_path_ns::NodeType::LOCAL_VIEWPOINT) {
      forward_viewpoint_count++;
    }
  }
  if (local_loop) {
    robot_i = local_path.nodes_.size() - 1;
  }
  for (int i = robot_i - 1; i >= 0; i--) {
    if (local_path.nodes_[i].type_ ==
        exploration_path_ns::NodeType::LOCAL_VIEWPOINT) {
      backward_viewpoint_count++;
    }
  }

  Eigen::Vector3d forward_lookahead_point = robot_position;
  Eigen::Vector3d backward_lookahead_point = robot_position;

  bool has_forward = false;
  bool has_backward = false;

  if (local_loop) {
    robot_i = 0;
  }
  bool forward_lookahead_point_in_los = true;
  bool backward_lookahead_point_in_los = true;
  double length_from_robot = 0.0;
  for (int i = robot_i + 1; i < local_path.GetNodeNum(); i++) {
    length_from_robot +=
        (local_path.nodes_[i].position_ - local_path.nodes_[i - 1].position_)
            .norm();
    double dist_to_robot =
        (local_path.nodes_[i].position_ - robot_position).norm();
    bool in_line_of_sight = true;
    if (i < local_path.GetNodeNum() - 1) {
      in_line_of_sight = viewpoint_manager_->InCurrentFrameLineOfSight(
          local_path.nodes_[i + 1].position_);
    }
    if ((length_from_robot > kLookAheadDistance ||
         (kUseLineOfSightLookAheadPoint && !in_line_of_sight) ||
         local_path.nodes_[i].type_ ==
             exploration_path_ns::NodeType::LOCAL_VIEWPOINT ||
         local_path.nodes_[i].type_ ==
             exploration_path_ns::NodeType::LOCAL_PATH_START ||
         local_path.nodes_[i].type_ ==
             exploration_path_ns::NodeType::LOCAL_PATH_END ||
         i == local_path.GetNodeNum() - 1))

    {
      if (kUseLineOfSightLookAheadPoint && !in_line_of_sight) {
        forward_lookahead_point_in_los = false;
      }
      forward_lookahead_point = local_path.nodes_[i].position_;
      has_forward = true;
      break;
    }
  }
  if (local_loop) {
    robot_i = local_path.nodes_.size() - 1;
  }
  length_from_robot = 0.0;
  for (int i = robot_i - 1; i >= 0; i--) {
    length_from_robot +=
        (local_path.nodes_[i].position_ - local_path.nodes_[i + 1].position_)
            .norm();
    double dist_to_robot =
        (local_path.nodes_[i].position_ - robot_position).norm();
    bool in_line_of_sight = true;
    if (i > 0) {
      in_line_of_sight = viewpoint_manager_->InCurrentFrameLineOfSight(
          local_path.nodes_[i - 1].position_);
    }
    if ((length_from_robot > kLookAheadDistance ||
         (kUseLineOfSightLookAheadPoint && !in_line_of_sight) ||
         local_path.nodes_[i].type_ ==
             exploration_path_ns::NodeType::LOCAL_VIEWPOINT ||
         local_path.nodes_[i].type_ ==
             exploration_path_ns::NodeType::LOCAL_PATH_START ||
         local_path.nodes_[i].type_ ==
             exploration_path_ns::NodeType::LOCAL_PATH_END ||
         i == 0))

    {
      if (kUseLineOfSightLookAheadPoint && !in_line_of_sight) {
        backward_lookahead_point_in_los = false;
      }
      backward_lookahead_point = local_path.nodes_[i].position_;
      has_backward = true;
      break;
    }
  }

  if (forward_viewpoint_count > 0 && !has_forward) {
    std::cout << "forward viewpoint count > 0 but does not have forward "
                 "lookahead point"
              << std::endl;
    exit(1);
  }
  if (backward_viewpoint_count > 0 && !has_backward) {
    std::cout << "backward viewpoint count > 0 but does not have backward "
                 "lookahead point"
              << std::endl;
    exit(1);
  }

  double dx = lookahead_point_direction_.x();
  double dy = lookahead_point_direction_.y();

  if (reset_waypoint_) {
    reset_waypoint_ = false;
    double lx = 1.0;
    double ly = 0.0;

    dx = cos(robot_yaw_) * lx - sin(robot_yaw_) * ly;
    dy = sin(robot_yaw_) * lx + cos(robot_yaw_) * ly;
  }

  double forward_angle_score = -2;
  double backward_angle_score = -2;
  double lookahead_angle_score = -2;

  double dist_robot_to_lookahead = 0.0;
  if (has_forward) {
    Eigen::Vector3d forward_diff = forward_lookahead_point - robot_position;
    forward_diff.z() = 0.0;
    forward_diff = forward_diff.normalized();
    forward_angle_score = dx * forward_diff.x() + dy * forward_diff.y();
  }
  if (has_backward) {
    Eigen::Vector3d backward_diff = backward_lookahead_point - robot_position;
    backward_diff.z() = 0.0;
    backward_diff = backward_diff.normalized();
    backward_angle_score = dx * backward_diff.x() + dy * backward_diff.y();
  }
  if (has_lookahead) {
    Eigen::Vector3d prev_lookahead_point =
        local_path.nodes_[lookahead_i].position_;
    dist_robot_to_lookahead = (robot_position - prev_lookahead_point).norm();
    Eigen::Vector3d diff = prev_lookahead_point - robot_position;
    diff.z() = 0.0;
    diff = diff.normalized();
    lookahead_angle_score = dx * diff.x() + dy * diff.y();
  }

  lookahead_point_cloud_->cloud_->clear();

  if (forward_viewpoint_count == 0 && backward_viewpoint_count == 0) {
    relocation_ = true;
  } else {
    relocation_ = false;
  }
  if (relocation_) {
    if (use_momentum_ && kUseMomentum) {
      if (forward_angle_score > backward_angle_score) {
        lookahead_point = forward_lookahead_point;
      } else {
        lookahead_point = backward_lookahead_point;
      }
    } else {
      // follow the shorter distance one
      if (dist_from_start < dist_from_end &&
          local_path.nodes_.front().type_ !=
              exploration_path_ns::NodeType::ROBOT) {
        lookahead_point = backward_lookahead_point;
      } else if (dist_from_end < dist_from_start &&
                 local_path.nodes_.back().type_ !=
                     exploration_path_ns::NodeType::ROBOT) {
        lookahead_point = forward_lookahead_point;
      } else {
        lookahead_point = forward_angle_score > backward_angle_score
                              ? forward_lookahead_point
                              : backward_lookahead_point;
      }
    }
  } else if (has_lookahead && lookahead_angle_score > 0 &&
             dist_robot_to_lookahead > kLookAheadDistance / 2 &&
             viewpoint_manager_->InLocalPlanningHorizon(
                 local_path.nodes_[lookahead_i].position_))

  {
    lookahead_point = local_path.nodes_[lookahead_i].position_;
  } else {
    if (forward_angle_score > backward_angle_score) {
      if (forward_viewpoint_count > 0) {
        lookahead_point = forward_lookahead_point;
      } else {
        lookahead_point = backward_lookahead_point;
      }
    } else {
      if (backward_viewpoint_count > 0) {
        lookahead_point = backward_lookahead_point;
      } else {
        lookahead_point = forward_lookahead_point;
      }
    }
  }

  if ((lookahead_point == forward_lookahead_point &&
       !forward_lookahead_point_in_los) ||
      (lookahead_point == backward_lookahead_point &&
       !backward_lookahead_point_in_los)) {
    lookahead_point_in_line_of_sight_ = false;
  } else {
    lookahead_point_in_line_of_sight_ = true;
  }

  lookahead_point_direction_ = lookahead_point - robot_position;
  lookahead_point_direction_.z() = 0.0;
  lookahead_point_direction_.normalize();

  pcl::PointXYZI point;
  point.x = lookahead_point.x();
  point.y = lookahead_point.y();
  point.z = lookahead_point.z();
  point.intensity = 1.0;
  lookahead_point_cloud_->cloud_->points.push_back(point);

  if (has_lookahead) {
    point.x = local_path.nodes_[lookahead_i].position_.x();
    point.y = local_path.nodes_[lookahead_i].position_.y();
    point.z = local_path.nodes_[lookahead_i].position_.z();
    point.intensity = 0;
    lookahead_point_cloud_->cloud_->points.push_back(point);
  }
  return true;
}
}
