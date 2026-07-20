#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能混合控制器节点
功能：整合键盘控制与自动避障，键盘控制优先级高于自动避障
避障策略：智能选择左右转向（根据空间充裕度）
参数来源：config/controller_params.yaml
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool
import math
import time


class SmartHybridController(Node):
    def __init__(self):
        super().__init__("smart_hybrid_controller")

        # ==================== 声明参数（从YAML加载）====================
        self.declare_parameter("min_distance", 0.5)
        self.declare_parameter("side_min_distance", 0.3)
        self.declare_parameter("front_angle_range_deg", 30)
        self.declare_parameter("linear_speed", 0.15)
        self.declare_parameter("angular_speed", 0.8)
        self.declare_parameter("keyboard_timeout", 3.0)
        self.declare_parameter("turn_threshold", 0.2)
        self.declare_parameter("default_turn_direction", "right")

        # ==================== 读取参数 ====================
        self.min_distance = self.get_parameter("min_distance").value
        self.side_min_distance = self.get_parameter("side_min_distance").value
        self.front_angle_range_deg = self.get_parameter("front_angle_range_deg").value
        self.linear_speed = self.get_parameter("linear_speed").value
        self.angular_speed = self.get_parameter("angular_speed").value
        self.keyboard_timeout = self.get_parameter("keyboard_timeout").value
        self.turn_threshold = self.get_parameter("turn_threshold").value
        self.default_turn_direction = self.get_parameter("default_turn_direction").value

        # 角度转弧度
        self.front_angle_range_rad = math.radians(self.front_angle_range_deg)
        # 默认转向映射：1.0=左转, -1.0=右转
        self.default_turn_sign = 1.0 if self.default_turn_direction == "left" else -1.0

        # 打印加载的参数
        self.get_logger().info("========== 参数加载完成 ==========")
        self.get_logger().info(f"前方检测阈值: {self.min_distance}m")
        self.get_logger().info(f"前方检测角度: ±{self.front_angle_range_deg}°")
        self.get_logger().info(f"自动线速度: {self.linear_speed}m/s")
        self.get_logger().info(f"自动角速度: {self.angular_speed}rad/s")
        self.get_logger().info(f"键盘超时: {self.keyboard_timeout}s")
        self.get_logger().info(f"转向阈值: {self.turn_threshold}m")
        self.get_logger().info(f"默认转向: {self.default_turn_direction}")
        self.get_logger().info("===================================")

        # ==================== 状态变量 ====================
        self.last_keyboard_time = 0.0
        self.is_keyboard_active = False
        self.keyboard_cmd = Twist()

        self.front_distance = float("inf")
        self.left_distance = float("inf")
        self.right_distance = float("inf")

        # ==================== 通信接口 ====================
        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        self.keyboard_sub = self.create_subscription(
            Twist, "/cmd_vel_keyboard", self.keyboard_callback, 10)

        self.lidar_sub = self.create_subscription(
            LaserScan, "/scan", self.lidar_callback, 10)

        self.mode_pub = self.create_publisher(Bool, "/keyboard_active", 10)

        # 控制循环 10Hz
        self.timer = self.create_timer(0.1, self.control_loop)

        self.get_logger().info("智能混合控制器已启动")
        self.get_logger().info("策略：键盘优先，自动避障时智能选择左右转向")

    def keyboard_callback(self, msg: Twist):
        """键盘输入回调"""
        self.last_keyboard_time = time.time()
        self.is_keyboard_active = True
        self.keyboard_cmd = msg

        status = Bool()
        status.data = True
        self.mode_pub.publish(status)

    def lidar_callback(self, msg: LaserScan):
        """激光雷达回调：分析前、左、右三个扇区的障碍物距离"""
        ranges = msg.ranges
        angle_min = msg.angle_min
        angle_increment = msg.angle_increment

        f_min = l_min = r_min = float("inf")

        for i, dist in enumerate(ranges):
            if dist <= 0.05 or math.isinf(dist) or math.isnan(dist):
                continue

            angle = angle_min + i * angle_increment
            angle = (angle + math.pi) % (2 * math.pi) - math.pi

            # 前方扇区
            if abs(angle) <= self.front_angle_range_rad:
                f_min = min(f_min, dist)
            # 左侧扇区：+30° ~ +90°
            elif 0 < angle <= math.radians(90):
                l_min = min(l_min, dist)
            # 右侧扇区：-90° ~ -30°
            elif -math.radians(90) <= angle < 0:
                r_min = min(r_min, dist)

        self.front_distance = f_min
        self.left_distance = l_min
        self.right_distance = r_min

    def control_loop(self):
        """主控制循环"""
        cmd = Twist()
        current_time = time.time()

        # 检查键盘超时
        if current_time - self.last_keyboard_time > self.keyboard_timeout:
            self.is_keyboard_active = False

        # ==================== 模式1：键盘控制（高优先级）====================
        if self.is_keyboard_active:
            # 键盘前进时遇障安全处理
            if self.front_distance < self.min_distance and self.keyboard_cmd.linear.x > 0:
                self.get_logger().warning(
                    f"键盘前进被阻止！前方障碍物 {self.front_distance:.2f}m")
                cmd.linear.x = 0.0
                cmd.angular.z = self.keyboard_cmd.angular.z  # 保留转向
            else:
                cmd = self.keyboard_cmd

            self.publish_status(True)

        # ==================== 模式2：智能自动避障 ====================
        else:
            if self.front_distance < self.min_distance:
                cmd.linear.x = 0.0

                # 左侧明显更宽敞
                if self.left_distance > self.right_distance + self.turn_threshold:
                    cmd.angular.z = self.angular_speed
                    self.get_logger().info(
                        f"自动避障：前方{self.front_distance:.2f}m有障碍，"
                        f"左侧({self.left_distance:.2f}m)>右侧({self.right_distance:.2f}m) → 左转")

                # 右侧明显更宽敞
                elif self.right_distance > self.left_distance + self.turn_threshold:
                    cmd.angular.z = -self.angular_speed
                    self.get_logger().info(
                        f"自动避障：前方{self.front_distance:.2f}m有障碍，"
                        f"右侧({self.right_distance:.2f}m)>左侧({self.left_distance:.2f}m) → 右转")

                # 两边差不多，默认转向（防振荡）
                else:
                    cmd.angular.z = self.default_turn_sign * self.angular_speed
                    self.get_logger().info(
                        f"自动避障：前方{self.front_distance:.2f}m有障碍，"
                        f"左右空间相近 → 默认{self.default_turn_direction}转")

            else:
                # 路径畅通，直行
                cmd.linear.x = self.linear_speed
                cmd.angular.z = 0.0

            self.publish_status(False)

        self.cmd_vel_pub.publish(cmd)

    def publish_status(self, is_keyboard: bool):
        """发布当前控制模式"""
        status = Bool()
        status.data = is_keyboard
        self.mode_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    controller = SmartHybridController()
    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        controller.get_logger().info("关闭中...")
    finally:
        controller.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
