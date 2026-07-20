
此文档由ai生成，我仅提供了生成说明的要求

# my_robot_simulation

ROS2/Gazebo 移动机器人仿真系统

## 功能特性

- 键盘控制优先于自动避障
- 智能避障：根据空间充裕度自动选择左转/右转
- 所有参数外置到 config/ 目录，无需编译即可调参
- 支持RViz可视化
  
## 目录结构

```
my_robot_simulation/
├── my_robot_simulation/
│   ├── __init__.py
│   └── smart_hybrid_controller.py    # 智能混合控制器节点
├── launch/
│   └── robot_simulation.launch.py    # 主启动文件
├── worlds/
│   └── hexagon_world.world            # 六边形障碍物场景
├── config/
│   ├── controller_params.yaml         # 控制器参数（避障/速度/超时等）
│   ├── mapper_params_online_async.yaml # SLAM建图参数
│   └── robot.rviz                    # RViz预设配置
├── resource/
│   └── my_robot_simulation           # ament索引标记文件
├── maps/
├── package.xml
├── setup.py
└── setup.cfg
```

## 安装步骤

```bash
# 1. 安装依赖
sudo apt update
sudo apt install ros-humble-turtlebot3 ros-humble-turtlebot3-gazebo ros-humble-turtlebot3-simulations ros-humble-turtlebot3-description
sudo apt install ros-humble-teleop-twist-keyboard ros-humble-slam-toolbox
sudo apt install xterm

# 2. 创建工作空间
cd ~
mkdir -p ros2_ws/src
cd ros2_ws/src

# 3. 复制本功能包到 src/ 目录
cp -r /path/to/my_robot_simulation ./

# 4. 编译
cd ~/ros2_ws
colcon build --packages-select my_robot_simulation

# 5. 配置环境变量
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
source install/setup.bash
```

## 运行

```bash
# 一键启动完整仿真
ros2 launch my_robot_simulation robot_simulation.launch.py

# 带RViz可视化
ros2 launch my_robot_simulation robot_simulation.launch.py launch_rviz:=true

# 或者在仿真已经运行的情况下，新开终端：
ros2 run rviz2 rviz2 -d ~/ros2_ws/install/my_robot_simulation/share/my_robot_simulation/config/robot.rviz
```

如果 RViz 报错 Fixed Frame [map] does not exist，将 Fixed Frame 从 map 改为 odom。

## 键盘控制

启动后会弹出XTerm终端，按以下键控制：

| 按键 | 动作 |
|------|------|
| i | 前进 |
| , | 后退 |
| j | 左转 |
| l | 右转 |
| k | 停止 |
| q/z | 加速/减速 |
| Ctrl+C | 退出 |

控制逻辑：

    键盘输入活跃时，完全由键盘控制
    停止按键 3秒 后，自动切换为智能避障模式
    键盘前进时遇障，自动阻止前进但保留转向控制

## 参数调参

编辑 `config/controller_params.yaml`，修改后重启launch即可：

```yaml
smart_hybrid_controller:
  ros__parameters:
    min_distance: 0.5                # 障碍物检测距离
    linear_speed: 0.15               # 自动模式速度
    angular_speed: 0.8                # 自动转向速度
    keyboard_timeout: 3.0            # 键盘超时时间
    turn_threshold: 0.2              # 转向切换阈值
    default_turn_direction: "right"    # 默认转向方向
```

## SLAM 建图（可选）
```bash
# 1. 启动仿真
ros2 launch my_robot_simulation robot_simulation.launch.py launch_rviz:=true

# 2. 新终端启动 SLAM
ros2 launch slam_toolbox online_async_launch.py \
    slam_params_file:=./src/my_robot_simulation/config/mapper_params_online_async.yaml \
    use_sim_time:=true

# 3. 键盘控制机器人遍历环境后，保存地图
ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/my_robot_simulation/maps/my_map
```

## 代码修改后重新编译
```bash
cd ~/ros2_ws
colcon build --packages-select my_robot_simulation --symlink-install
source install/setup.bash
```

## 环境说明
- 项目版本：v1.0
- 运行系统：Ubuntu 22.04 LTS
- ROS版本：ROS 2 Humble Hawksbill
- 仿真环境：Gazebo Classic 11
- 机器人模型：TurtleBot3 Burger

## 克隆我的仓库
```bash
# 1. 进入工作空间src
cd ~/ros2_ws/src

# 2. 克隆你的包
git clone https://github.com/fadai12306/my_robot_simulation.git

# 3. 返回工作空间根目录编译
cd ..
colcon build

# 4. 刷新环境
source install/setup.bash
```