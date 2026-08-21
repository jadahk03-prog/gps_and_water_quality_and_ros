#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SENSOR_GPS_PROJECT_DIR:-$SCRIPT_DIR}"
CONTAINER_NAME="ros_jazzy_container"
IMAGE_NAME="ros_jazzy_ws"

cd "$PROJECT_DIR"

if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "[0] Docker image missing; building it..."
    docker build -t "$IMAGE_NAME" "$PROJECT_DIR/python"
fi

echo "[1] Starting Arduino App..."
arduino-app-cli app start user:ros_arduino_uno_Q

echo "[2] Waiting for Arduino Router..."

for i in $(seq 1 30); do
    if [ -S /var/run/arduino-router.sock ]; then
        echo "Arduino Router ready."
        break
    fi

    sleep 1
done

if [ ! -S /var/run/arduino-router.sock ]; then
    echo "ERROR: Arduino Router socket not ready."
    exit 1
fi

echo "[3] Removing old ROS container..."

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "[4] Starting ROS 2 container..."

docker run -d \
    --name "$CONTAINER_NAME" \
    --network host \
    --restart unless-stopped \
    -e ROS_DOMAIN_ID=0 \
    -v /var/run/arduino-router.sock:/var/run/arduino-router.sock \
    -v "$PROJECT_DIR/python/src:/ros2_ws/src" \
    "$IMAGE_NAME" \
    bash -c '
        source /opt/ros/jazzy/setup.bash
        cd /ros2_ws
        colcon build --symlink-install
        source /ros2_ws/install/setup.bash
        ros2 run ros_led water_quality &
        WATER_PID=$!
        ros2 run ros_led gps &
        GPS_PID=$!
        trap "kill $WATER_PID $GPS_PID" TERM INT
        wait -n $WATER_PID $GPS_PID
    '

echo "[5] Water quality and GPS ROS nodes started."
