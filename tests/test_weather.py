"""Tests for the pure helper in weather.py."""
from datetime import datetime, timedelta, timezone

from custom_components.meteo_hr.weather import _closest_hour

_TZ = timezone.utc


def _hour(hours_from_now: int, now: datetime) -> dict:
    return {"datetime": now + timedelta(hours=hours_from_now), "marker": hours_from_now}


def test_closest_hour_picks_nearest_regardless_of_direction():
    now = datetime(2026, 7, 15, 14, 30, tzinfo=_TZ)
    hourly = [_hour(-2, now), _hour(1, now), _hour(3, now)]
    assert _closest_hour(hourly, now)["marker"] == 1


def test_closest_hour_exact_match():
    now = datetime(2026, 7, 15, 14, 0, tzinfo=_TZ)
    hourly = [_hour(-1, now), _hour(0, now), _hour(2, now)]
    assert _closest_hour(hourly, now)["marker"] == 0


def test_closest_hour_empty_list_returns_none():
    assert _closest_hour([], datetime(2026, 7, 15, tzinfo=_TZ)) is None
