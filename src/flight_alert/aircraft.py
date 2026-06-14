from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any


@dataclass(frozen=True)
class Aircraft:
    hex: str
    callsign: str | None
    aircraft_type: str | None
    registration: str | None
    altitude_m: float | None
    distance_km: float
    lat: float | None
    lon: float | None
    track_deg: float | None
    speed_kmh: float | None
    seen_seconds: int | None
    origin_country: str | None

    @property
    def tracking_url(self) -> str:
        return f"https://globe.airplanes.live/?icao={self.hex}"

    @property
    def display_callsign(self) -> str:
        return self.callsign or self.registration or self.hex.upper()


def parse_airplanes_live(payload: dict[str, Any], home_lat: float, home_lon: float) -> list[Aircraft]:
    aircraft = payload.get("ac")
    if not isinstance(aircraft, list):
        return []

    result: list[Aircraft] = []
    for item in aircraft:
        if not isinstance(item, dict):
            continue
        parsed = parse_aircraft(item, home_lat, home_lon)
        if parsed is not None:
            result.append(parsed)
    return result


def parse_aircraft(item: dict[str, Any], home_lat: float, home_lon: float) -> Aircraft | None:
    hex_id = _clean_str(item.get("hex"))
    if not hex_id:
        return None

    lat = _number(item.get("lat"))
    lon = _number(item.get("lon"))
    distance_km = None
    if lat is not None and lon is not None:
        distance_km = haversine_km(home_lat, home_lon, lat, lon)
    elif _number(item.get("dst")) is not None:
        distance_km = _number(item.get("dst")) * 1.852
    if distance_km is None:
        return None

    altitude_m = altitude_to_meters(item.get("alt_geom"))
    if altitude_m is None:
        altitude_m = altitude_to_meters(item.get("alt_baro"))

    speed_kmh = speed_to_kmh(item.get("gs"))

    return Aircraft(
        hex=hex_id.lower(),
        callsign=_clean_str(item.get("flight")) or _clean_str(item.get("r")),
        aircraft_type=_clean_str(item.get("t")),
        registration=_clean_str(item.get("r")),
        altitude_m=altitude_m,
        distance_km=distance_km,
        lat=lat,
        lon=lon,
        track_deg=_number(item.get("track")),
        speed_kmh=speed_kmh,
        seen_seconds=_int(item.get("seen_pos")) or _int(item.get("seen")),
        origin_country=_clean_str(item.get("ownOp")) or _clean_str(item.get("desc")),
    )


def is_alert_candidate(
    aircraft: Aircraft,
    *,
    widebody_types: frozenset[str],
    max_altitude_m: float,
    max_stale_seconds: int,
) -> bool:
    if aircraft.aircraft_type is None:
        return False
    if aircraft.aircraft_type.upper() not in widebody_types:
        return False
    if aircraft.altitude_m is None or aircraft.altitude_m > max_altitude_m:
        return False
    if aircraft.seen_seconds is not None and aircraft.seen_seconds > max_stale_seconds:
        return False
    return True


def altitude_to_meters(value: Any) -> float | None:
    if value in (None, "ground"):
        return None
    number = _number(value)
    if number is None:
        return None
    # Airplanes.live reports altitude fields in feet.
    return number * 0.3048


def speed_to_kmh(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    # Ground speed is reported in knots.
    return number * 1.852


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius_km * asin(sqrt(a))


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    number = _number(value)
    if number is None:
        return None
    return int(number)
