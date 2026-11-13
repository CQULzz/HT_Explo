from pathlib import Path
import shutil,json
old=Path('/home/lzz/ht_execution_300s_20261113');r=Path('/home/lzz/ht_repeat_20261114');r.mkdir(exist_ok=True);(r/'setup').mkdir(exist_ok=True)
p=Path('/home/lzz/tare_native_20261110/src/tare_planner/src')
for name in ['sensor_coverage_planner/sensor_coverage_planner_ground.cpp','grid_world/grid_world.cpp','local_coverage_planner/local_coverage_planner.cpp']:
    src=p/name;backup=r/'original_tare_source'/name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(src,backup)
    s=backup.read_text()
    if name.startswith('sensor_'):
        anchor='    near_home_ = GetRobotToHomeDistance() < kRushHomeDist;'
        s=s.replace(anchor,'''    RCLCPP_INFO(this->get_logger(), "EXPLORATION_DIAG candidates=%d uncovered=%d frontier=%d global_return=%d local_complete=%d global_nodes=%zu local_nodes=%zu x=%.3f y=%.3f",
      viewpoint_candidate_count, uncovered_point_num, uncovered_frontier_point_num,
      grid_world_->IsReturningHome(), local_coverage_planner_->IsLocalCoverageComplete(), global_path.nodes_.size(), local_path.nodes_.size(), robot_position_.x, robot_position_.y);
'''+anchor)
    elif name.startswith('grid_'):
        s=s.replace('  for (int i = 0; i < subspaces_->GetCellNumber(); i++)\n  {\n    if (subspaces_->GetCell(i).GetStatus() == CellStatus::EXPLORING)', '  int diag_exploring=0;\n  for (int i = 0; i < subspaces_->GetCellNumber(); i++)\n  {\n    if (subspaces_->GetCell(i).GetStatus() == CellStatus::EXPLORING)')
        s=s.replace('    if (subspaces_->GetCell(i).GetStatus() == CellStatus::EXPLORING)\n    {\n      if (std::find', '    if (subspaces_->GetCell(i).GetStatus() == CellStatus::EXPLORING)\n    {\n      ++diag_exploring;\n      if (std::find')
        s=s.replace('  /****** Return home ******/','  RCLCPP_INFO(rclcpp::get_logger("grid_diag"), "GLOBAL_DIAG exploring=%d routable=%zu", diag_exploring, exploring_cell_indices.size());\n  /****** Return home ******/')
    else:
        anchor='  viewpoint_sampling_timer.Stop(false, kRuntimeUnit);'
        s=s.replace(anchor,'''  RCLCPP_INFO(rclcpp::get_logger("local_diag"), "LOCAL_DIAG uncovered=%d frontier=%d queue=%zu best_surface=%d frontier_queue=%zu best_frontier=%d reused=%zu",
    uncovered_point_num, uncovered_frontier_point_num, queue.size(), queue.empty()?0:queue[0].first, frontier_queue.size(), frontier_queue.empty()?0:frontier_queue[0].first, reused_viewpoint_indices.size());
'''+anchor)
    src.write_text(s)
for name in ['runtime','config','common_sensor','mapper_source','install_mapper','install_gate','install_cmu','venv']:
    if not (r/name).exists():(r/name).symlink_to(old/name,target_is_directory=True)
for name in ['mapper_setup_4hz.yaml','mcap.yaml']:shutil.copy2(old/name,r/name)
s=(old/'run.py').read_text().replace(str(old),str(r))
s=s.replace("'/ht_repeat_20261114/install_mapper/'", "'/ht_execution_300s_20261113/install_mapper/'")
s=s.replace("PROJECT/'tools/ht_height_quality'", "PROJECT/'tools/ht_height_quality'")
s=s.replace("'core_param_file:=/home/lzz/ht_repeat_20261114/config/trial_core.yaml'", "'core_param_file:=/home/lzz/ht_execution_300s_20261113/config/trial_core.yaml'")
s=s.replace("ROOT/'BUDGET.json'", "ROOT/'REPEAT_BUDGET.json'")
s=s.replace("'/ht_minimal/recovery_path']", "'/ht_minimal/recovery_path','/frontier_cloud','/filtered_frontier_cloud','/candidate_viewpoints','/selected_viewpoints','/coverage_cloud','/uncovered_cloud','/exploring_cell_vis_cloud']")
(r/'run.py').write_text(s)
(r/'simulation.launch.py').write_text((old/'simulation.launch.py').read_text().replace(str(old),str(r)))
(r/'env.sh').write_text((old/'env.sh').read_text().replace(str(old/'install_native'),str(r/'install_native')).replace('ROS_DOMAIN_ID=214','ROS_DOMAIN_ID=215'))
budget=r/'REPEAT_BUDGET.json'
if not budget.exists():budget.write_text(json.dumps({'maximum_formal_launch_attempts':4,'planned_baseline_repeats':2,'planned_fix_verification':1,'duration_s':300,'attempts':[]},indent=2))
print('Diagnostic-only source and independent repeat ledger prepared')
