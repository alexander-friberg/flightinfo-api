"""Settings read from the environment. The API key never leaves this object in printable form."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.swedavia.se/flightinfo/v2"
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_CACHE_TTL_S = 120.0

MISSING_KEY_MESSAGE = (
    "SWEDAVIA_API_KEY is not set. Copy .env.example to .env, put your subscription key in it, "
    "and start the app with: uv run --env-file .env python -m flightboard "
    "(or use --offline to run on sample data without a key)."
)


class ConfigError(Exception):
    """The environment holds a missing or invalid setting."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings. `api_key` is empty in offline mode.

    `repr()` masks the key, but `dataclasses.asdict()` and `vars()` don't: never log those.
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = DEFAULT_TIMEOUT_S
    cache_ttl_s: float = DEFAULT_CACHE_TTL_S

    def __repr__(self) -> str:
        shown_key = "'***'" if self.api_key else "''"
        return (
            f"Settings(api_key={shown_key}, base_url={self.base_url!r}, "
            f"timeout_s={self.timeout_s!r}, cache_ttl_s={self.cache_ttl_s!r})"
        )


def load_settings(env: Mapping[str, str], *, offline: bool = False) -> Settings:
    """Build `Settings` from an environment mapping.

    Offline mode needs no key and drops any key it is given, so it can never reach the API.
    """
    api_key = "" if offline else env.get("SWEDAVIA_API_KEY", "").strip()
    if not api_key and not offline:
        raise ConfigError(MISSING_KEY_MESSAGE)

    return Settings(
        api_key=api_key,
        timeout_s=_seconds(env, "SWEDAVIA_TIMEOUT_S", DEFAULT_TIMEOUT_S, positive=True),
        # A TTL of 0 or less is allowed: it switches the response cache off.
        cache_ttl_s=_seconds(env, "SWEDAVIA_CACHE_TTL_S", DEFAULT_CACHE_TTL_S, positive=False),
    )


def _seconds(env: Mapping[str, str], name: str, default: float, *, positive: bool) -> float:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number of seconds, got {raw!r}.") from None
    if not math.isfinite(value):
        raise ConfigError(f"{name} must be a number of seconds, got {raw!r}.")
    if positive and value <= 0:
        raise ConfigError(f"{name} must be greater than 0, got {raw!r}.")
    return value
