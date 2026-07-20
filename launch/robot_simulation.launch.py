#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    
    pkg_share = get_package_share_directory("my_robot_simulation")
    
    controller_params = os.path.join(pkg_share, "config", "controller_params.yaml")
    rviz_config = os.path.join(pkg_share, "config", "robot.rviz")
    
    turtlebot3_model = "burger"
    os.environ["TURTLEBOT3_MODEL"] = turtlebot3_model
    
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    launch_rviz = LaunchConfiguration("launch_rviz", default="false")
    
    # 用 turtlebot3_gazebo 启动 Gazebo
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('turtlebot3_gazebo'),
                'launch',
                'turtlebot3_world.launch.py'
            )
        ])
    )
    
    # 读取URDF
    urdf_path = os.path.join(
        get_package_share_directory("turtlebot3_description"),
        "urdf",
        "turtlebot3_burger.urdf"
    )
    with open(urdf_path, 'r') as f:
        robot_description = f.read()
    
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "robot_description": robot_description
        }]
    )
    
    spawn_robot = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
            "-entity", "turtlebot3_" + turtlebot3_model,
            "-file", urdf_path,
            "-x", "0.0", "-y", "0.0", "-z", "0.01", "-Y", "0.0"
        ],
        output="screen"
    )
    
    hybrid_controller = Node(
        package="my_robot_simulation",
        executable="smart_controller",
        name="smart_hybrid_controller",
        output="screen",
        parameters=[
            controller_params,
            {"use_sim_time": use_sim_time}
        ],
        remappings=[
            ("/cmd_vel_keyboard", "/cmd_vel_keyboard"),
        ]
    )
    
    teleop_keyboard = Node(
        package="teleop_twist_keyboard",
        executable="teleop_twist_keyboard",
        name="teleop_keyboard",
        output="screen",
        prefix="xterm -e",
        remappings=[
            ("/cmd_vel", "/cmd_vel_keyboard"),
        ],
        parameters=[{
            "speed": 0.3,
            "turn": 0.5,
        }]
    )
    
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        condition=IfCondition(launch_rviz),
        parameters=[{"use_sim_time": use_sim_time}],
        arguments=["-d", rviz_config]
    )
    
    ld = LaunchDescription()
    
    ld.add_action(DeclareLaunchArgument("use_sim_time", default_value="true"))
    ld.add_action(DeclareLaunchArgument("launch_rviz", default_value="false"))
    
    ld.add_action(gazebo_launch)
    ld.add_action(robot_state_publisher)
    ld.add_action(spawn_robot)
    ld.add_action(hybrid_controller)
    ld.add_action(teleop_keyboard)
    ld.add_action(rviz_node)
    
    return ld