"""Tests for the pure parsing/classification helpers in coordinator.py.

classify_condition in particular encodes DHMZ's Croatian symbol vocabulary as
keyword matching — worth pinning each branch explicitly so a refactor doesn't
silently misclassify a condition.
"""
from custom_components.meteo_hr.coordinator import _parse_wind, classify_condition


def test_parse_wind_two_letter_direction():
    assert _parse_wind("NE1") == (10, 45)


def test_parse_wind_one_letter_direction():
    assert _parse_wind("W4") == (55, 270)


def test_parse_wind_calm_has_no_bearing():
    assert _parse_wind("C0") == (0, None)


def test_parse_wind_invalid_code_returns_none_none():
    assert _parse_wind("") == (None, None)
    assert _parse_wind(None) == (None, None)
    assert _parse_wind("bogus") == (None, None)


def test_classify_condition_snow_and_rain_mix():
    assert classify_condition("Susnježica, snijeg i kiša", night=False) == "snowy-rainy"


def test_classify_condition_snow_only():
    assert classify_condition("Obilan snijeg", night=False) == "snowy"


def test_classify_condition_thunder_and_rain():
    assert classify_condition("Grmljavina i kiša", night=False) == "lightning-rainy"


def test_classify_condition_thunder_only():
    assert classify_condition("Grmljavinsko nevrijeme", night=False) == "lightning"


def test_classify_condition_heavy_rain():
    assert classify_condition("Znatnu kišu", night=False) == "pouring"


def test_classify_condition_rain():
    assert classify_condition("Kiša", night=False) == "rainy"


def test_classify_condition_fog():
    assert classify_condition("Maglovito", night=False) == "fog"
    assert classify_condition("Magla", night=False) == "fog"


def test_classify_condition_overcast():
    assert classify_condition("Potpuno oblačno", night=False) == "cloudy"
    assert classify_condition("Pretežno oblačno", night=False) == "cloudy"


def test_classify_condition_partly_cloudy():
    assert classify_condition("Umjereno oblačno", night=False) == "partlycloudy"
    assert classify_condition("Malo oblačno", night=False) == "partlycloudy"


def test_classify_condition_vedro_is_always_clear_night():
    # DHMZ uses "vedro" for a clear sky regardless of the symbol's own day/night flag.
    assert classify_condition("Vedro", night=False) == "clear-night"
    assert classify_condition("Vedro", night=True) == "clear-night"


def test_classify_condition_sunny_flips_to_clear_night_after_dark():
    assert classify_condition("Sunčano", night=False) == "sunny"
    assert classify_condition("Sunčano", night=True) == "clear-night"


def test_classify_condition_unknown_text_falls_back_to_partly_cloudy():
    assert classify_condition("", night=False) == "partlycloudy"
    assert classify_condition("some new DHMZ symbol text", night=False) == "partlycloudy"
