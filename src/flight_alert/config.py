from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_WIDEBODY_TYPES = {
    "A300",
    "A310",
    "A330",
    "A332",
    "A333",
    "A338",
    "A339",
    "A340",
    "A342",
    "A343",
    "A345",
    "A346",
    "A350",
    "A359",
    "A35K",
    "A380",
    "A388",
    "B741",
    "B742",
    "B743",
    "B744",
    "B748",
    "B74S",
    "B74R",
    "B762",
    "B763",
    "B764",
    "B772",
    "B773",
    "B77L",
    "B77W",
    "B778",
    "B779",
    "B788",
    "B789",
    "B78X",
    "MD11",
    "DC10",
    "IL96",
}


@dataclass(frozen=True)
class Config:
    home_lat: float = 52.3076
    home_lon: float = 5.0413
    radius_km: float = 5.0
    max_altitude_m: float = 1000.0
    poll_seconds: float = 10.0
    alert_cooldown_seconds: int = 1800
    stale_aircraft_seconds: int = 30
    ntfy_url: str = "https://ntfy.sh"
    ntfy_topic: str = "over-weesp-flights-alerts"
    ntfy_priority: str = "high"
    ntfy_tags: str = "airplane"
    aircraft_api_url: str = "https://api.airplanes.live/v2/point/{lat}/{lon}/{radius_nm}"
    fallback_aircraft_api_url: str = "https://api.adsb.fi/v2/point/{lat}/{lon}/{radius_nm}"
    route_lookup_enabled: bool = True
    route_api_url: str = "https://api.adsbdb.com/v0/callsign/{callsign}"
    route_cache_seconds: int = 1800
    widebody_types: frozenset[str] = frozenset(DEFAULT_WIDEBODY_TYPES)

    @property
    def radius_nm(self) -> float:
        return self.radius_km / 1.852

    @property
    def ntfy_endpoint(self) -> str:
        return f"{self.ntfy_url.rstrip('/')}/{self.ntfy_topic}"


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def load_config() -> Config:
    load_dotenv()
    return Config(
        home_lat=_float_env("HOME_LAT", Config.home_lat),
        home_lon=_float_env("HOME_LON", Config.home_lon),
        radius_km=_float_env("RADIUS_KM", Config.radius_km),
        max_altitude_m=_float_env("MAX_ALTITUDE_M", Config.max_altitude_m),
        poll_seconds=_float_env("POLL_SECONDS", Config.poll_seconds),
        alert_cooldown_seconds=_int_env("ALERT_COOLDOWN_SECONDS", Config.alert_cooldown_seconds),
        stale_aircraft_seconds=_int_env("STALE_AIRCRAFT_SECONDS", Config.stale_aircraft_seconds),
        ntfy_url=os.getenv("NTFY_URL", Config.ntfy_url),
        ntfy_topic=os.getenv("NTFY_TOPIC", Config.ntfy_topic),
        ntfy_priority=os.getenv("NTFY_PRIORITY", Config.ntfy_priority),
        ntfy_tags=os.getenv("NTFY_TAGS", Config.ntfy_tags),
        aircraft_api_url=os.getenv("AIRCRAFT_API_URL", Config.aircraft_api_url),
        fallback_aircraft_api_url=os.getenv("FALLBACK_AIRCRAFT_API_URL", Config.fallback_aircraft_api_url),
        route_lookup_enabled=_bool_env("ROUTE_LOOKUP_ENABLED", Config.route_lookup_enabled),
        route_api_url=os.getenv("ROUTE_API_URL", Config.route_api_url),
        route_cache_seconds=_int_env("ROUTE_CACHE_SECONDS", Config.route_cache_seconds),
        widebody_types=_types_env("WIDEBODY_TYPES", DEFAULT_WIDEBODY_TYPES),
    )


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _types_env(name: str, default: set[str]) -> frozenset[str]:
    raw = os.getenv(name)
    if not raw:
        return frozenset(default)
    return frozenset(part.strip().upper() for part in raw.split(",") if part.strip())
