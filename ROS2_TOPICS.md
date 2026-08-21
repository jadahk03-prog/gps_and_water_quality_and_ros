# UNO Q 수질 센서 + GPS 통합 및 ROS 2 토픽

## 1. 구성 개요

이 프로젝트는 Arduino UNO Q 한 대에서 수질 센서와 NEO-M8N GPS를 함께
운영한다.

- UNO Q의 MCU(STM32)는 센서와 GPS 데이터를 읽는다.
- 수질 센서는 D4, A0, A1, A5 핀을 사용한다.
- GPS는 `Serial1`을 통해 9600 baud로 NMEA-0183 문장을 수신한다.
- MCU와 Linux 사이의 데이터 전달에는 `Arduino_RouterBridge`를 사용한다.
- UNO Q의 Linux에서 실행되는 ROS 2 Jazzy 노드가 데이터를 토픽으로 발행한다.
- 수질 센서 노드와 GPS 노드는 서로 분리되어 있지만 하나의 Arduino 스케치를
  공유한다.

```text
수질 센서 ─┐
            ├─ Arduino sketch ─ RouterBridge ─ water_quality_node ─ /water_quality/*
NEO-M8N ────┘                    └───────────── gps_node ─────────── /gps/*
```

## 2. Arduino 핀과 통신 설정

| 장치 | UNO Q 연결 | 용도 |
|---|---:|---|
| DS18B20 수온 센서 | D4 | 수온 측정 |
| pH 센서 | A1 | pH 센서 전압 측정 |
| DO 센서 | A5 | 용존산소 센서 전압 측정 |
| 탁도 센서 | A0 | 탁도 센서 전압 측정 |
| NEO-M8N GPS | `Serial1` | NMEA 데이터 수신, 9600 baud |

GPS와 수질 센서는 하나의 `sketch/sketch.ino`에 통합되어 있다. 센서 측정 중에도
GPS UART를 계속 읽어서 수신 버퍼가 넘치지 않도록 구성했다.

## 3. 수질 센서 ROS 2 노드

- 노드 이름: `water_quality_node`
- 실행 명령: `ros2 run ros_led led`
- MCU Bridge 함수: `get_water_quality`
- 기본 발행 주기: 5초

### 수질 센서 토픽

| 토픽 | 메시지 타입 | 값과 단위 | 의미 |
|---|---|---|---|
| `/water_quality/data` | `std_msgs/msg/String` | JSON 문자열 | 한 번 측정한 수질 데이터 전체 |
| `/water_quality/temperature_c` | `std_msgs/msg/Float32` | °C | DS18B20으로 측정한 수온 |
| `/water_quality/ph` | `std_msgs/msg/Float32` | pH | 보정값과 수온을 적용해 계산한 pH |
| `/water_quality/do_mg_l` | `std_msgs/msg/Float32` | mg/L | 수온 보정을 적용한 용존산소 농도 |
| `/water_quality/turbidity_voltage_v` | `std_msgs/msg/Float32` | V | 분압비를 반영한 탁도 센서 전압 |
| `/water_quality/clarity_pct` | `std_msgs/msg/Float32` | 0~100% | 탁도 전압으로 계산한 물의 맑기 비율 |
| `/water_quality/clarity_level` | `std_msgs/msg/String` | 문자열 | 맑기 비율을 구간으로 분류한 값 |

`/water_quality/clarity_level`은 다음 문자열 중 하나를 발행한다.

| 값 | 의미 |
|---|---|
| `very_clear` | 매우 맑음, 80% 이상 |
| `clear` | 맑음, 60% 이상 80% 미만 |
| `normal` | 보통, 40% 이상 60% 미만 |
| `turbid` | 탁함, 20% 이상 40% 미만 |
| `very_turbid` | 매우 탁함, 20% 미만 |

### `/water_quality/data` JSON 필드

```json
{
  "ms": 123456,
  "temp_c": 24.31,
  "ph": 7.12,
  "do_mg_l": 8.25,
  "turbidity_voltage_v": 2.345,
  "clarity_pct": 47.2,
  "clarity_level": "normal"
}
```

| 필드 | 의미 |
|---|---|
| `ms` | MCU 부팅 후 경과 시간(ms) |
| `temp_c` | 수온(°C) |
| `ph` | 계산된 pH |
| `do_mg_l` | 용존산소 농도(mg/L) |
| `turbidity_voltage_v` | 탁도 센서 보정 전압(V) |
| `clarity_pct` | 맑기 비율(%) |
| `clarity_level` | 맑기 단계 문자열 |

센서 값을 계산할 수 없으면 MCU JSON에서는 해당 값이 `null`이 된다. Python
노드는 유효한 유한 숫자만 개별 `Float32` 토픽에 발행한다.

## 4. GPS ROS 2 노드

- 노드 이름: `gps_node`
- 실행 명령: `ros2 run ros_led gps`
- MCU Bridge 함수: `get_gps`
- 기본 조회 및 발행 주기: 1초
- 지원 NMEA 문장: `GGA`, `RMC`
- 지원 Talker ID: `GP`, `GN` 등을 포함한 표준 ID

### GPS 토픽

| 토픽 | 메시지 타입 | 값 | 의미 |
|---|---|---|---|
| `/gps/fix` | `sensor_msgs/msg/NavSatFix` | 위도·경도 | 유효한 GPS Fix가 있을 때만 발행되는 표준 위치 메시지 |
| `/gps/has_fix` | `std_msgs/msg/Bool` | `true`/`false` | 현재 유효한 위치 고정 여부 |
| `/gps/satellites` | `std_msgs/msg/UInt8` | 0~255 | GGA 문장에서 확인한 사용 위성 수 |
| `/gps/status` | `std_msgs/msg/String` | JSON 문자열 | GPS 파서, UART 수신, Fix 상태를 포함한 전체 진단 정보 |

### `/gps/fix` 주요 필드

| 필드 | 값과 의미 |
|---|---|
| `header.stamp` | ROS 노드가 메시지를 발행한 시각 |
| `header.frame_id` | `gps_link` |
| `status.status` | 유효 좌표 발행 시 `STATUS_FIX` |
| `status.service` | `SERVICE_GPS` |
| `latitude` | 십진수 위도, 북위는 양수이고 남위는 음수 |
| `longitude` | 십진수 경도, 동경은 양수이고 서경은 음수 |
| `altitude` | 현재 파서에서 제공하지 않으므로 `NaN` |
| `position_covariance_type` | 정밀도 정보가 없어 `COVARIANCE_TYPE_UNKNOWN` |

GPS Fix가 없거나 좌표가 유효하지 않으면 `/gps/fix`는 발행하지 않는다.
대신 `/gps/has_fix`, `/gps/satellites`, `/gps/status`는 계속 발행한다.

### `/gps/status` JSON 필드

GPS가 연결되지 않은 상태의 예시는 다음과 같다.

```json
{
  "ms": 41704,
  "parser_ok": true,
  "fix": false,
  "satellites": 0,
  "latitude": null,
  "longitude": null,
  "bytes": 0,
  "sentences": 0
}
```

| 필드 | 의미 |
|---|---|
| `ms` | MCU 부팅 후 경과 시간(ms) |
| `parser_ok` | 내장 샘플 NMEA로 수행한 GPS 파서 자체 테스트 결과 |
| `fix` | RMC/GGA 기준 위치 고정 여부 |
| `satellites` | GGA에서 확인한 사용 위성 수 |
| `latitude` | 유효 Fix가 있을 때의 십진수 위도, 아니면 `null` |
| `longitude` | 유효 Fix가 있을 때의 십진수 경도, 아니면 `null` |
| `bytes` | `Serial1`에서 받은 누적 GPS 바이트 수 |
| `sentences` | `$`로 시작하는 누적 NMEA 문장 수 |

### GPS 상태 판정

| 상태 | 판정 방법 | 의미 |
|---|---|---|
| 코드 통합 정상 | `parser_ok=true` | GPS 파서와 Bridge 코드가 정상 작동 |
| GPS 미연결 | `bytes=0`, `sentences=0` | UART에 GPS 데이터가 들어오지 않음 |
| 배선/baud 이상 가능 | `bytes>0`, `sentences=0` | 바이트는 들어오지만 NMEA 문장으로 인식하지 못함 |
| GPS 통신 정상, Fix 전 | `sentences>0`, `fix=false` | 모듈 통신은 정상이나 위치 고정 전 |
| GPS 위치 정상 | `fix=true`, 좌표가 숫자 | `/gps/fix`에서 실제 위치 발행 |

## 5. 실행 및 확인 명령

전체 App과 ROS 컨테이너 시작:

```bash
cd ~/ArduinoApps/ros_arduino_uno_Q
./start_water_quality.sh
```

토픽 목록 확인:

```bash
ros2 topic list
```

GPS 상태 확인:

```bash
ros2 topic echo /gps/status
ros2 topic echo /gps/has_fix
ros2 topic echo /gps/satellites
ros2 topic echo /gps/fix
```

수질 센서 상태 확인:

```bash
ros2 topic echo /water_quality/data
```

ROS 명령을 UNO Q 호스트에서 실행할 때 노드는 Docker 컨테이너 내부에 있으므로
다음과 같이 실행할 수 있다.

```bash
docker exec -it ros_jazzy_container bash
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
ros2 topic list
```

## 6. 현재 검증 결과

- Arduino UNO Q용 통합 스케치 컴파일 성공
- 수질 센서와 GPS 코드가 하나의 Arduino 스케치에 통합됨
- `get_water_quality`, `get_gps` RouterBridge 함수 동작
- `water_quality_node`, `gps_node` 동시 실행 확인
- 수질 센서 토픽과 GPS 토픽 생성 확인
- GPS 미연결 상태에서 `parser_ok=true`, `fix=false`, `satellites=0` 발행 확인
- 실제 GPS 좌표와 실제 센서값은 하드웨어 연결 후 별도 검증 필요
