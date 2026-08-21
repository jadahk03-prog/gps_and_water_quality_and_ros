# Water Quality Monitoring on Arduino UNO Q

Arduino UNO Q에서 수질 센서값을 읽고 ROS 2 토픽으로 발행하는 프로젝트입니다.

# 자동실행 설치 (최초 1회만)
실행
cd ~/ArduinoApps/sensor_gps
chmod +x run.sh start_water_quality.sh install_autostart.sh
./install_autostart.sh


ROS노드 확인
docker exec ros_jazzy_container bash -lc \
  'source /opt/ros/jazzy/setup.bash &&
   source /ros2_ws/install/setup.bash &&
   ros2 node list'

정상이면
/gps_node
/water_quality_node

## Architecture

- STM32 MCU가 수온, pH, 용존산소(DO), 탁도 센서를 측정합니다.
- `get_water_quality` RPC가 측정 결과를 JSON으로 반환합니다.
- Qualcomm MPU의 Docker 컨테이너에서 ROS 2 Jazzy 노드가 실행됩니다.
- ROS 노드는 Arduino Router를 통해 RPC를 호출하고 센서값을 ROS 2 토픽으로 발행합니다.

## Docker

Docker 이미지를 빌드합니다.

```bash
docker build -t ros_jazzy_ws python/
```

Arduino 앱을 시작합니다.

```bash
arduino-app-cli app start user:ros_arduino_uno_Q
```

Arduino Router 소켓이 생성된 후 컨테이너를 실행합니다.

```bash
docker run -it \
  --network host \
  --name ros_jazzy_container \
  -v /var/run/arduino-router.sock:/var/run/arduino-router.sock \
  ros_jazzy_ws
```

컨테이너 안에서 ROS 2 노드를 실행합니다.

```bash
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
ros2 run ros_led led
```

새 이름은 `water_quality`이며, 기존 `led` 명령도 호환성을 위해 유지됩니다.

```bash
ros2 run ros_led water_quality
ros2 run ros_led gps
```

백그라운드 자동 실행에는 루트 디렉터리의 스크립트를 사용할 수 있습니다.

```bash
./start_water_quality.sh
```

## 배터리 전원 자동 실행

UNO Q에 배터리 전원만 공급해도 부팅 후 자동 실행되도록 최초 한 번 서비스를
설치합니다.

```bash
chmod +x install_autostart.sh
./install_autostart.sh
```

설치 스크립트는 `sudo`를 직접 붙이지 말고 평소 UNO Q 사용자 계정에서
실행합니다. 필요한 systemd 설정 단계에서만 비밀번호를 요청합니다.

설치 후에는 로그인이나 터미널 실행 없이 Arduino 앱, RouterBridge, ROS 2
컨테이너와 수질/GPS 노드가 순서대로 시작됩니다. 상태와 로그는 다음 명령으로
확인합니다.

```bash
sudo systemctl status sensor-gps.service
docker logs ros_jazzy_container
```

## ROS 2 Topics

부팅되면 `water_quality_node`와 `gps_node`가 함께 실행됩니다. 수질 데이터의
기본 발행 주기는 5초이며, GPS 상태의 기본 발행 주기는 1초입니다.

### 수질 토픽

| 토픽 | 메시지 타입 | 값/단위 | 의미 |
|---|---|---|---|
| `/water_quality/data` | `std_msgs/msg/String` | JSON 문자열 | 한 번 측정한 수질 데이터 전체와 MCU 부팅 후 경과 시간을 함께 제공합니다. |
| `/water_quality/temperature_c` | `std_msgs/msg/Float32` | °C | DS18B20 센서로 측정한 수온입니다. |
| `/water_quality/ph` | `std_msgs/msg/Float32` | pH | 센서 보정값과 현재 수온을 반영해 계산한 산성·알칼리성 수치입니다. 7은 중성입니다. |
| `/water_quality/do_mg_l` | `std_msgs/msg/Float32` | mg/L | 물에 녹아 있는 산소의 농도입니다. 수온 보정이 적용됩니다. |
| `/water_quality/turbidity_voltage_v` | `std_msgs/msg/Float32` | V | 탁도 센서에서 측정하고 분압비를 보정한 전압입니다. 원시 상태 확인과 재보정에 사용합니다. |
| `/water_quality/clarity_pct` | `std_msgs/msg/Float32` | 0~100% | 탁도 전압을 맑기 비율로 변환한 값입니다. 값이 클수록 맑은 물입니다. |
| `/water_quality/clarity_level` | `std_msgs/msg/String` | 상태 문자열 | 맑기 비율을 사람이 읽기 쉬운 단계로 분류한 결과입니다. |

`/water_quality/clarity_level` 값은 다음과 같습니다.

| 값 | 맑기 비율 | 의미 |
|---|---:|---|
| `very_clear` | 80% 이상 | 매우 맑음 |
| `clear` | 60% 이상 80% 미만 | 맑음 |
| `normal` | 40% 이상 60% 미만 | 보통 |
| `turbid` | 20% 이상 40% 미만 | 탁함 |
| `very_turbid` | 20% 미만 | 매우 탁함 |

센서가 연결되지 않았거나 값을 계산할 수 없으면 전체 JSON의 해당 값은
`null`이 됩니다. 이 경우 해당 개별 `Float32` 토픽은 잘못된 숫자를 대신
발행하지 않습니다.

### GPS 토픽

| 토픽 | 메시지 타입 | 값/단위 | 의미 |
|---|---|---|---|
| `/gps/fix` | `sensor_msgs/msg/NavSatFix` | 위도·경도(도) | 유효한 GPS Fix가 있을 때만 발행되는 표준 ROS 위치 메시지입니다. 고도와 위치 공분산은 현재 제공하지 않습니다. |
| `/gps/has_fix` | `std_msgs/msg/Bool` | `true`/`false` | 현재 GPS가 유효한 위치를 확보했는지 나타냅니다. 마지막 정상 NMEA 문장 이후 5초가 지나면 `false`가 됩니다. |
| `/gps/satellites` | `std_msgs/msg/UInt8` | 위성 개수 | GGA 문장에서 확인한 현재 사용 위성 수입니다. |
| `/gps/status` | `std_msgs/msg/String` | JSON 문자열 | GPS 연결, 파서, checksum, Fix 및 UART 수신 상태를 모두 포함하는 진단 정보입니다. |

`/gps/status` JSON의 주요 필드는 다음과 같습니다.

| 필드 | 의미 |
|---|---|
| `ms` | MCU가 부팅된 후 흐른 시간(ms) |
| `parser_ok` | 부팅 시 내장 NMEA 샘플로 수행한 파서 자체 시험 결과 |
| `fix` | 현재 유효한 위치 Fix 보유 여부 |
| `satellites` | 현재 사용하는 위성 수 |
| `latitude`, `longitude` | 유효한 Fix가 있을 때의 십진수 좌표, 없으면 `null` |
| `bytes` | GPS UART에서 받은 누적 바이트 수 |
| `sentences` | `$`로 시작하는 누적 NMEA 문장 수 |
| `checksum_errors` | checksum이 없거나 일치하지 않아 폐기한 문장 수 |
| `last_sentence_age_ms` | 마지막 정상 NMEA 문장을 받은 후 흐른 시간, 수신 전에는 `null` |

GPS가 아직 위치를 잡지 못해도 `/gps/has_fix`, `/gps/satellites`,
`/gps/status`는 계속 발행됩니다. `/gps/fix`만 유효한 좌표가 있을 때 발행됩니다.

### 토픽 확인

```bash
ros2 topic echo /water_quality/data
ros2 topic echo /water_quality/temperature_c
ros2 topic echo /gps/status
ros2 topic echo /gps/fix
```

실행 중인 노드를 확인하려면 다음 명령을 사용합니다.

```bash
docker exec ros_jazzy_container bash -lc \
  'source /opt/ros/jazzy/setup.bash && \
   source /ros2_ws/install/setup.bash && \
   ros2 node list'
```

## License

BSD-3-Clause. 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.
