import dataclasses
from collections.abc import Callable

import pytest

from flightboard.config import ConfigError, Settings, load_settings

KEY = "s3cret-subscription-key-0123456789"


def test_loads_key_and_defaults() -> None:
    settings = load_settings({"SWEDAVIA_API_KEY": KEY})

    assert settings.api_key == KEY
    assert settings.base_url == "https://api.swedavia.se/flightinfo/v2"
    assert settings.timeout_s == 10.0
    assert settings.cache_ttl_s == 120.0


def test_settings_are_frozen() -> None:
    settings = load_settings({"SWEDAVIA_API_KEY": KEY})

    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.api_key = "other"  # type: ignore[misc]


def test_key_is_stripped_of_surrounding_whitespace() -> None:
    assert load_settings({"SWEDAVIA_API_KEY": f"  {KEY}\n"}).api_key == KEY


@pytest.mark.parametrize("env", [{}, {"SWEDAVIA_API_KEY": ""}, {"SWEDAVIA_API_KEY": "   "}])
def test_missing_or_empty_key_explains_how_to_fix_it(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError) as error:
        load_settings(env)

    message = str(error.value)
    assert "SWEDAVIA_API_KEY" in message
    assert ".env.example" in message
    assert "uv run --env-file .env" in message


def test_reads_only_the_given_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SWEDAVIA_API_KEY", KEY)

    with pytest.raises(ConfigError):
        load_settings({})


@pytest.mark.parametrize("show", [repr, str])
def test_key_never_appears_when_settings_are_printed(show: Callable[[object], str]) -> None:
    settings = load_settings({"SWEDAVIA_API_KEY": KEY})

    text = show(settings)

    assert KEY not in text
    assert "api_key='***'" in text
    assert "timeout_s=10.0" in text


def test_masked_repr_shows_when_no_key_is_set() -> None:
    assert "api_key=''" in repr(load_settings({}, offline=True))


def test_numeric_overrides() -> None:
    settings = load_settings(
        {"SWEDAVIA_API_KEY": KEY, "SWEDAVIA_TIMEOUT_S": "2.5", "SWEDAVIA_CACHE_TTL_S": "0"}
    )

    assert settings.timeout_s == 2.5
    assert settings.cache_ttl_s == 0.0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SWEDAVIA_TIMEOUT_S", "abc"),
        ("SWEDAVIA_TIMEOUT_S", "0"),
        ("SWEDAVIA_TIMEOUT_S", "-1"),
        ("SWEDAVIA_TIMEOUT_S", "nan"),
        ("SWEDAVIA_CACHE_TTL_S", "ten"),
        ("SWEDAVIA_CACHE_TTL_S", "inf"),
    ],
)
def test_invalid_numbers_name_the_variable_and_value(name: str, value: str) -> None:
    with pytest.raises(ConfigError) as error:
        load_settings({"SWEDAVIA_API_KEY": KEY, name: value})

    message = str(error.value)
    assert name in message
    assert repr(value) in message
    assert KEY not in message


def test_offline_mode_needs_no_key() -> None:
    settings = load_settings({}, offline=True)

    assert settings.api_key == ""


def test_offline_mode_drops_a_key_that_is_set() -> None:
    settings = load_settings({"SWEDAVIA_API_KEY": KEY}, offline=True)

    assert settings.api_key == ""


def test_offline_mode_still_validates_numbers() -> None:
    with pytest.raises(ConfigError):
        load_settings({"SWEDAVIA_TIMEOUT_S": "abc"}, offline=True)


def test_settings_can_be_built_directly_with_defaults() -> None:
    settings = Settings(api_key=KEY)

    assert settings.base_url == "https://api.swedavia.se/flightinfo/v2"
    assert KEY not in repr(settings)
