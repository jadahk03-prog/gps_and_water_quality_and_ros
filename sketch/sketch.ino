#include <Arduino.h>
#include <Arduino_RouterBridge.h>
#include <OneWire.h>
#include <math.h>

#define TEMP_PIN 4
#define PH_PIN A1
#define DO_PIN A5
#define TURBIDITY_PIN A0

#define ADC_BITS 12
#define ADC_MAX 4095.0
#define ADC_REFERENCE_V 3.3
#define ADC_REFERENCE_MV 3300.0
#define SAMPLE_COUNT 40

#define PH7_BUFFER_VALUE 7.00
#define PH4_BUFFER_VALUE 4.00

#define PH7_VOLTAGE 1.142
#define PH4_VOLTAGE 0.888

#define PH_CALIBRATION_T 25.47

#define DO_CAL_V 1505.0
#define DO_CAL_T 25.4

#define TURBIDITY_DIVIDER_RATIO 1.5

#define CLEAR_WATER_VOLTAGE 4.810
#define VERY_TURBID_VOLTAGE 0.140

OneWire oneWire(TEMP_PIN);

byte temperatureAddress[8];
bool temperatureSensorFound = false;

const uint16_t DO_TABLE[41] = {
  14460, 14220, 13820, 13440, 13090,
  12740, 12420, 12110, 11810, 11530,
  11260, 11010, 10770, 10530, 10300,
  10080,  9860,  9660,  9460,  9270,
   9080,  8900,  8730,  8570,  8410,
   8250,  8110,  7960,  7820,  7690,
   7560,  7430,  7300,  7180,  7070,
   6950,  6840,  6730,  6630,  6530,
   6410
};


bool findTemperatureSensor()
{
  oneWire.reset_search();

  while (oneWire.search(temperatureAddress))
  {
    if (OneWire::crc8(temperatureAddress, 7)
        != temperatureAddress[7])
      continue;

    if (temperatureAddress[0] == 0x28)
      return true;
  }

  return false;
}


float readTemperatureC()
{
  if (!temperatureSensorFound)
    return NAN;

  byte data[9];

  if (!oneWire.reset())
    return NAN;

  oneWire.select(temperatureAddress);
  oneWire.write(0x44, 1);

  delay(750);

  if (!oneWire.reset())
    return NAN;

  oneWire.select(temperatureAddress);
  oneWire.write(0xBE);

  for (int i = 0; i < 9; i++)
    data[i] = oneWire.read();

  if (OneWire::crc8(data, 8) != data[8])
    return NAN;

  int16_t raw =
    ((int16_t)data[1] << 8) | data[0];

  return raw / 16.0;
}


double readAverageADC(int pin)
{
  uint32_t sum = 0;

  int minValue = 4095;
  int maxValue = 0;

  analogRead(pin);
  delay(5);

  for (int i = 0; i < SAMPLE_COUNT; i++)
  {
    int value = analogRead(pin);

    sum += value;

    if (value < minValue)
      minValue = value;

    if (value > maxValue)
      maxValue = value;

    delay(20);
  }

  sum -= minValue;
  sum -= maxValue;

  return (double)sum /
         (SAMPLE_COUNT - 2);
}


float adcToVoltage(double adcValue)
{
  return adcValue *
         ADC_REFERENCE_V /
         ADC_MAX;
}


float adcToMillivolts(double adcValue)
{
  return adcValue *
         ADC_REFERENCE_MV /
         ADC_MAX;
}


float calculatePH(
  float voltage,
  float temperature
)
{
  if (isnan(temperature))
    return NAN;

  float voltageDifference =
    PH4_VOLTAGE -
    PH7_VOLTAGE;

  if (fabs(voltageDifference) < 0.001)
    return NAN;

  float calibrationSlope =
    (PH4_BUFFER_VALUE -
     PH7_BUFFER_VALUE)
    /
    voltageDifference;

  float temperatureSlope =
    calibrationSlope *
    (
      (PH_CALIBRATION_T + 273.15)
      /
      (temperature + 273.15)
    );

  return
    PH7_BUFFER_VALUE +
    temperatureSlope *
    (voltage - PH7_VOLTAGE);
}


float calculateDO(
  float voltageMv,
  float temperature
)
{
  if (isnan(temperature))
    return NAN;

  int temperatureIndex =
    constrain(
      (int)round(temperature),
      0,
      40
    );

  float saturationVoltage =
    DO_CAL_V +
    35.0 *
    (
      temperatureIndex -
      DO_CAL_T
    );

  if (saturationVoltage <= 0.0)
    return NAN;

  return
    voltageMv *
    DO_TABLE[temperatureIndex]
    /
    saturationVoltage
    /
    1000.0;
}


float calculateCleanliness(
  float voltage
)
{
  float cleanliness =
    (
      voltage -
      VERY_TURBID_VOLTAGE
    )
    /
    (
      CLEAR_WATER_VOLTAGE -
      VERY_TURBID_VOLTAGE
    )
    *
    100.0;

  return constrain(
    cleanliness,
    0.0,
    100.0
  );
}


String getCleanlinessLevel(
  float value
)
{
  if (value >= 80.0)
    return "very_clear";

  if (value >= 60.0)
    return "clear";

  if (value >= 40.0)
    return "normal";

  if (value >= 20.0)
    return "turbid";

  return "very_turbid";
}


String floatToJson(
  float value,
  int digits
)
{
  if (isnan(value))
    return "null";

  return String(
    value,
    digits
  );
}


// =================================================
// Linux/ROS에서 호출할 함수
// =================================================

String get_water_quality()
{
  float temperature =
    readTemperatureC();


  double phADC =
    readAverageADC(PH_PIN);

  float phVoltage =
    adcToVoltage(phADC);

  float ph =
    calculatePH(
      phVoltage,
      temperature
    );


  double doADC =
    readAverageADC(DO_PIN);

  float doVoltageMv =
    adcToMillivolts(doADC);

  float dissolvedOxygen =
    calculateDO(
      doVoltageMv,
      temperature
    );


  double turbidityADC =
    readAverageADC(
      TURBIDITY_PIN
    );

  float turbidityA0Voltage =
    adcToVoltage(
      turbidityADC
    );

  float turbidityVoltage =
    turbidityA0Voltage *
    TURBIDITY_DIVIDER_RATIO;

  float clarity =
    calculateCleanliness(
      turbidityVoltage
    );

  String level =
    getCleanlinessLevel(
      clarity
    );


  String json = "{";

  json += "\"ms\":";
  json += String(millis());

  json += ",\"temp_c\":";
  json += floatToJson(
    temperature,
    2
  );

  json += ",\"ph\":";
  json += floatToJson(
    ph,
    2
  );

  json += ",\"do_mg_l\":";
  json += floatToJson(
    dissolvedOxygen,
    2
  );

  json +=
    ",\"turbidity_voltage_v\":";

  json += floatToJson(
    turbidityVoltage,
    3
  );

  json += ",\"clarity_pct\":";

  json += floatToJson(
    clarity,
    1
  );

  json +=
    ",\"clarity_level\":\"";

  json += level;

  json += "\"}";

  return json;
}


void setup()
{
  analogReadResolution(
    ADC_BITS
  );

  temperatureSensorFound =
    findTemperatureSensor();

  Bridge.begin();

  Bridge.provide(
    "get_water_quality",
    get_water_quality
  );
}


void loop()
{
}
