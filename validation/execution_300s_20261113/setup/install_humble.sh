set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
mkdir -p /home/lzz/ht_execution_300s_20261113/setup
exec > >(tee -a /mnt/d/HT-Execution-300s/setup/install_humble.log) 2>&1
sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list
apt-get -o Acquire::ForceIPv4=true update
apt-get -y install ca-certificates curl gnupg locales software-properties-common
cp /mnt/d/HT-Execution-300s/setup/ros.key /usr/share/keyrings/ros-archive-keyring.gpg
printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.ustc.edu.cn/ros2/ubuntu jammy main\n' > /etc/apt/sources.list.d/ros2.list
apt-get -o Acquire::ForceIPv4=true update
apt-get -y install ros-humble-ros-base ros-humble-gazebo-ros-pkgs ros-humble-pcl-ros ros-humble-grid-map-ros ros-humble-rosbag2-storage-mcap ros-humble-rviz2 ros-humble-joy ros-humble-robot-state-publisher ros-humble-xacro python3-colcon-common-extensions python3-venv python3-pip python3-scipy python3-matplotlib python3-pytest libgoogle-glog-dev libgflags-dev libomp-dev libtbb-dev libeigen3-dev libopencv-dev libboost-all-dev xvfb mesa-utils ffmpeg git build-essential
printf 'HUMBLE_SETUP_COMPLETE\n'
