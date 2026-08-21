"""Unit tests for telemetry validation."""

from ros_led.telemetry import bounded_integer
from ros_led.telemetry import valid_coordinates


def test_bounded_integer_clamps_and_defaults():
    assert bounded_integer(12, 0, 255) == 12
    assert bounded_integer(-4, 0, 255) == 0
    assert bounded_integer(999, 0, 255) == 255
    assert bounded_integer(None, 0, 255) == 0
    assert bounded_integer('invalid', 0, 255) == 0
    assert bounded_integer(True, 0, 255) == 0


def test_valid_coordinates_accepts_geographic_bounds():
    assert valid_coordinates(37.3874583, 127.020575)
    assert valid_coordinates(-90.0, -180.0)
    assert valid_coordinates(90.0, 180.0)


def test_valid_coordinates_rejects_invalid_values():
    assert not valid_coordinates(91.0, 0.0)
    assert not valid_coordinates(0.0, 181.0)
    assert not valid_coordinates(float('nan'), 127.0)
    assert not valid_coordinates(True, 127.0)
    assert not valid_coordinates('37.0', 127.0)
