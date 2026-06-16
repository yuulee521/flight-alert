from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib import parse, request

from flight_alert.config import Config
from flight_alert.logging import log


@dataclass(frozen=True)
class RouteInfo:
    departure_city: str | None = None
    departure_airport: str | None = None
    destination_city: str | None = None
    destination_airport: str | None = None

    @property
    def departure_display(self) -> str:
        if self.departure_city and self.departure_airport:
            return f"{self.departure_city} ({self.departure_airport})"
        if self.departure_city:
            return self.departure_city
        if self.departure_airport:
            return self.departure_airport
        return "unknown"


class RouteResolver:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._cache: dict[str, tuple[float, RouteInfo | None]] = {}

    def resolve(self, callsign: str | None) -> RouteInfo | None:
        if not self.config.route_lookup_enabled or not callsign:
            return None

        normalized = callsign.strip().upper()
        if not normalized:
            return None

        cached = self._cache.get(normalized)
        now = time.time()
        if cached and now - cached[0] < self.config.route_cache_seconds:
            return cached[1]

        route = self._fetch(normalized)
        self._cache[normalized] = (now, route)
        return route

    def _fetch(self, callsign: str) -> RouteInfo | None:
        url = self.config.route_api_url.format(callsign=parse.quote(callsign, safe=""))
        req = request.Request(url, headers={"User-Agent": "flight-alert/0.1"})
        try:
            with request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:  # noqa: BLE001 - route data is optional enrichment.
            return None

        route = parse_route_payload(payload)
        if route is None:
            log(f"route lookup found no departure city for {callsign}")
        return route


def parse_route_payload(payload: dict[str, Any]) -> RouteInfo | None:
    response = payload.get("response")
    if isinstance(response, dict):
        payload = response

    flight_route = payload.get("flightroute") or payload.get("flight_route") or payload.get("route")
    if not isinstance(flight_route, dict):
        flight_route = payload

    origin = _dict_value(flight_route, "origin", "departure", "from")
    destination = _dict_value(flight_route, "destination", "arrival", "to")

    departure_city = _airport_city(origin)
    departure_airport = _airport_code(origin)
    destination_city = _airport_city(destination)
    destination_airport = _airport_code(destination)

    if not any([departure_city, departure_airport, destination_city, destination_airport]):
        return None

    return RouteInfo(
        departure_city=departure_city,
        departure_airport=departure_airport,
        destination_city=destination_city,
        destination_airport=destination_airport,
    )


def _dict_value(mapping: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, dict):
            return value
    return None


def _airport_city(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    return _clean_str(
        value.get("municipality")
        or value.get("city")
        or value.get("city_name")
        or value.get("name")
    )


def _airport_code(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    return _clean_str(
        value.get("iata_code")
        or value.get("iata")
        or value.get("icao_code")
        or value.get("icao")
    )


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
