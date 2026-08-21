#!/bin/bash

PROJECT_DIR="/home/arduino/ArduinoApps/ros_arduino_uno_Q"
CONTAINER_NAME="ros_jazzy_container"
IMAGE_NAME="ros_jazzy_ws"

cd "$PROJECT_DIR" || exit 1

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
    "$IMAGE_NAME" \
    bash -c '
        source /opt/ros/jazzy/setup.bash
        source /ros2_ws/install/setup.bash
        exec ros2 run ros_led led
    '

echo "[5] Water quality ROS started."
