# 八方向来源核对

2026-10-11 检查用户指定的 `Unmanned-Systems-Lab/ZTH`：main
`3b5763c619a2037dd8a43772d248f341601f2609` 和 feature/city-multiseq-alignment-pipeline
`f0d867fdb3e88b5c7669c9bb7826aa1d7307aeef` 均未找到 HT 训练标签或八方向定义；项目是雷达/激光雷达目标检测。

本机 `/home/agx/ht_trans` 有 Scout HT 训练实现。其 mapping/model/student_best_epoch_weights.pth
与运行包 models/student_best_epoch_weights.pth 的 SHA256 相同：
`0a79b865d012aa633fbb9913fc4031908dfe188ec9e161ef5a3fbb34a3f8c4d4`。
这证明权重文件一致；仓库未提供该权重训练运行的完整溯源记录。

## 从代码推导的顺序

- ht_tra_classification_scout/utils/dataloader.py 的 Scout 数据类第1158行：yaw列表按0、45、90、135、180、225、270、315度排列。
- 第1253行附近：teacher yaw = student yaw + 列表角度，按列表顺序加入 teacher patch。
- 同文件 hm_extract_patch_fast_nofastpara：先以 alpha 旋转图片坐标，再 np.rot90。
  原图航向向量 `(cos(alpha), -sin(alpha))` 因此对应模型输入的负行方向。
- mapping/utils/utils_fit.py 第398行起：teacher第k个patch与student输出第2k、2k+1项蒸馏匹配，无通道重排。
- mapping/student_model.py 第98行：输出 reshape 为8×2；ROS node.py 第260行取类别1可通过概率。
- 当前 GridMap 解码不旋转图片；GridMap矩阵负行方向是地图+X，负列方向是地图+Y。

由此推导当前接口应使用下面的顺序（相对高程图坐标系，非车头坐标系）：

|通道|航向|方向|
|---|---|---|
|0|0°|+X|
|1|45°|+X,+Y|
|2|90°|+Y|
|3|135°|-X,+Y|
|4|180°|-X|
|5|225°|-X,-Y|
|6|270°|-Y|
|7|315°|+X,-Y|

`ht_channel_order: [0,1,2,3,4,5,6,7]`，`ht_heading_offset: 0.0`。
上游推理节点的 direction_order 也必须保持身份顺序，避免重复重排。

## 实车状态

训练代码推导不是实车单向坡面验证。用户明确要求启动低速实车测试后，已将 `ht_directions_calibrated: true`，仅表示采用已核对的坐标映射；运动效果尚未验证。速度上限0.2 m/s，角速度上限0.15 rad/s。
需要用已知方向的坡面核对模型八通道输出，再确认标定状态。有效支持不足仍禁止运动。
接口、方向轨迹检查、停止逻辑已完成；此处没有宣称完成实车运动验证。

## 2026-10-11 补充：模型参考点

四个方向的静态墙复算曾表现为障碍影响相反通道。继续检查训练标签后确认，这是学生模型参考点在车头前缘造成的，不能据此将通道旋转 180°。

实际 Scout 标签生成代码位于 `/home/agx/ht_trans/ht_tra_classification_scout_mapping/txt_annotation_frontcar_repeatdata_teacher_elefilesave_multiprocess_plane_onelabel_returntime.py`：学生参考点为 Frontpoint + goal_distance/2，教师参考点为 Frontpoint + car_bais_sum_teacher。Scout 长度 0.925 m，动作标签距离 0.04 m，因此学生参考点相对车身中心前移 0.4825 m。

桥接后的 `/ht_traversability/global_local` 将每个方向的概率从车头前缘参考点转换到车身中心参考点：方向 k 的车身中心概率查询原图沿该方向前移 0.4825 m 的单元。通道顺序保持不变；边缘缺失不填概率。原始模型图仍为前缘参考点，不能直接用于车身中心规划。

模型已包含车身覆盖：规划和控制的概率额外裕量采用 0.1 m。局部控制对完整 0.6 m 实体范围保留有效支持检查，并以 0.6 m 半径检查实际点云障碍；概率阈值仍 0.5。实车方向坡面标定仍未完成。
