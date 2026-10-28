# URDF自过滤只读核验（2026-10-28）

事实：用户要求查看URDF。GitHub默认main最新提交与已采用固定提交相同，均为`cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36`，提交日期2026-09-03T09:37:45Z。未发现后来更新的电脑/电源箱定义。

源文件：`CQULzz/eletranskit_scout/src/ele_scout_kit/urdf/scout_sensor_rack.urdf.xacro`，blob `ec5bda24ffb53d8ecb9a97b2155dee0d1993a9c3`。

展开宏后16个link、15个fixed joint。明细：

| link | 几何 | 当前self_filter |
|---|---|---|
| base_footprint | 空参考框架 | 无需过滤 |
| base_link | visual=base_link.dae；collision=0.925×0.380×0.210 box | 使用collision+2cm；视觉侧凸部分未完全覆盖 |
| 4×wheel link | visual=wheel_type1/2.dae；collision radius0.16459、length0.11653圆柱 | 已按4圆柱+2cm覆盖 |
| sensor_kit_base_link | 空安装框架 | 无需过滤 |
| sensor_frame_link | frame.STL | 已按完整mesh AABB+2cm覆盖 |
| rs_helios_link | rs_helios.STL | 已覆盖 |
| fixposition_link | fixposition_link.STL | 已覆盖 |
| gnss_right_link、gnss_left_link | gnss_antenna.STL | 两处均覆盖 |
| imu_tm431_link | imu_tm431.STL | 已覆盖 |
| rs_m1_link | rs_m1.STL | 已覆盖 |
| zed2i_link | zed2i.stl | 已覆盖 |
| rslidar | 空别名框架 | 无需过滤 |

各sensor_mesh均仅有visual，无collision（源Xacro72–92行）。现有self_filter使用其mesh边界，未漏掉这些visual。frame.STL是整体网格，不含电脑/电源箱分件名。不能凭外观确定其是否完整表达真实附件；如果附件位于现有包围盒内，本过滤已同时覆盖该区域。

## 可验证的低位底盘视觉缺口

base_link.dae含五个几何部件，整体范围`[-0.4649301,-0.273025,-0.1162019]`至`[0.4649308,0.2730249,0.1162017]`。当前collision加padding后的Y范围仅±0.210m。将其87098个视觉顶点代入当前完整9box+4cylinder过滤，仍6522顶点落在过滤体外；不是只与chassis box比较。缺口顶点范围`X[-0.4385901,0.438591],Y[-0.2518383,0.251839],Z[-0.1016751,0.07970116]`。

只读反事实检查：415帧原始点云中，用五个base_link视觉部件的AABB+同样2cm检查现有after过滤残留点，共1032点，分布260帧，最多15点/帧，末帧6点。范围`X[-0.484907,-0.137557],Y[-0.229318,0.288876],Z[0.021994,0.132632]`。这些是视觉包围盒候选残留，未有逐点车体真值，不能视为已经证明车体噪声，也不能认定为低HT概率的主因。

## 建议与边界

可将完整底盘视觉几何作为下一独立候选补充过滤，再冻结新版本并重建高程图/HT做同条件对比。不要仅凭用户说附件在车身就扩大整片车周围过滤框，不改外参、不猜附件尺寸，不把当前冻结版本208帧实验挪作新过滤候选验收。

本审计未修改任何生产代码、参数、TF、阈值；未启动设备或仿真。
