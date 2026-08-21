import json
import math

from ros_led.app_utils import *

import rclpy
from rclpy.node import Node

from std_msgs.msg import Float32
from std_msgs.msg import String


class WaterQualityNode(Node):

    def __init__(self):

        super().__init__(
            'water_quality_node'
        )

        self.data_pub = (
            self.create_publisher(
                String,
                '/water_quality/data',
                10
            )
        )

        self.temp_pub = (
            self.create_publisher(
                Float32,
                '/water_quality/temperature_c',
                10
            )
        )

        self.ph_pub = (
            self.create_publisher(
                Float32,
                '/water_quality/ph',
                10
            )
        )

        self.do_pub = (
            self.create_publisher(
                Float32,
                '/water_quality/do_mg_l',
                10
            )
        )

        self.turbidity_pub = (
            self.create_publisher(
                Float32,
                '/water_quality/turbidity_voltage_v',
                10
            )
        )

        self.clarity_pub = (
            self.create_publisher(
                Float32,
                '/water_quality/clarity_pct',
                10
            )
        )

        self.level_pub = (
            self.create_publisher(
                String,
                '/water_quality/clarity_level',
                10
            )
        )

        self.timer = self.create_timer(
            5.0,
            self.read_water_quality
        )

        self.get_logger().info(
            'Water quality node started'
        )


    def publish_float(
        self,
        publisher,
        value
    ):

        if not isinstance(
            value,
            (int, float)
        ):
            return

        value = float(value)

        if not math.isfinite(value):
            return

        msg = Float32()

        msg.data = value

        publisher.publish(msg)


    def read_water_quality(self):

        try:

            raw = Bridge.call(
                "get_water_quality"
            )

            if isinstance(
                raw,
                bytes
            ):
                raw = raw.decode(
                    'utf-8'
                )

            data = json.loads(
                str(raw)
            )

        except Exception as error:

            self.get_logger().warning(
                f'Bridge error: {error}'
            )

            return


        # ------------------------
        # 전체 JSON
        # ------------------------

        json_msg = String()

        json_msg.data = json.dumps(
            data,
            ensure_ascii=False,
            separators=(',', ':')
        )

        self.data_pub.publish(
            json_msg
        )


        # ------------------------
        # 개별 값
        # ------------------------

        self.publish_float(
            self.temp_pub,
            data.get('temp_c')
        )

        self.publish_float(
            self.ph_pub,
            data.get('ph')
        )

        self.publish_float(
            self.do_pub,
            data.get('do_mg_l')
        )

        self.publish_float(
            self.turbidity_pub,
            data.get(
                'turbidity_voltage_v'
            )
        )

        self.publish_float(
            self.clarity_pub,
            data.get(
                'clarity_pct'
            )
        )


        level = data.get(
            'clarity_level'
        )

        if isinstance(
            level,
            str
        ):

            msg = String()

            msg.data = level

            self.level_pub.publish(
                msg
            )


        self.get_logger().info(
            f"T={data.get('temp_c')} "
            f"pH={data.get('ph')} "
            f"DO={data.get('do_mg_l')} "
            f"clarity={data.get('clarity_pct')}"
        )


def main(args=None):

    rclpy.init(args=args)

    node = WaterQualityNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':
    main()
