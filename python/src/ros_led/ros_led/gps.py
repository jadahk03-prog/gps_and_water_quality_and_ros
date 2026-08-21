import json
from ros_led.app_utils import Bridge
from ros_led.telemetry import bounded_integer
from ros_led.telemetry import valid_coordinates

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import NavSatFix
from sensor_msgs.msg import NavSatStatus
from std_msgs.msg import Bool
from std_msgs.msg import String
from std_msgs.msg import UInt8


class GpsNode(Node):

    def __init__(self):
        super().__init__('gps_node')

        self.fix_pub = self.create_publisher(
            NavSatFix, '/gps/fix', 10
        )
        self.satellites_pub = self.create_publisher(
            UInt8, '/gps/satellites', 10
        )
        self.has_fix_pub = self.create_publisher(
            Bool, '/gps/has_fix', 10
        )
        self.status_pub = self.create_publisher(
            String, '/gps/status', 10
        )

        self.timer = self.create_timer(1.0, self.read_gps)
        self.get_logger().info('GPS node started')

    def read_gps(self):
        try:
            raw = Bridge.call('get_gps')
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            data = json.loads(str(raw))
        except Exception as error:
            self.get_logger().warning(f'GPS Bridge error: {error}')
            return

        has_fix = data.get('fix') is True

        fix_state = Bool()
        fix_state.data = has_fix
        self.has_fix_pub.publish(fix_state)

        satellites = UInt8()
        satellites.data = bounded_integer(data.get('satellites'), 0, 255)
        self.satellites_pub.publish(satellites)

        status = String()
        status.data = json.dumps(
            data, ensure_ascii=False, separators=(',', ':')
        )
        self.status_pub.publish(status)

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        coordinates_valid = valid_coordinates(latitude, longitude)

        if has_fix and coordinates_valid:
            message = NavSatFix()
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = 'gps_link'
            message.status.status = NavSatStatus.STATUS_FIX
            message.status.service = NavSatStatus.SERVICE_GPS
            message.latitude = float(latitude)
            message.longitude = float(longitude)
            message.altitude = float('nan')
            message.position_covariance_type = (
                NavSatFix.COVARIANCE_TYPE_UNKNOWN
            )
            self.fix_pub.publish(message)

        self.get_logger().info(
            f"parser={data.get('parser_ok')} "
            f"fix={has_fix} satellites={satellites.data} "
            f"bytes={data.get('bytes')} "
            f"sentences={data.get('sentences')}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = GpsNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
