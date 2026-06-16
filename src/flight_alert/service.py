from __future__ import annotations

import json
import signal
import sys
import time
from urllib import error, request

from flight_alert.aircraft import Aircraft, is_alert_candidate, parse_airplanes_live
from flight_alert.config import Config
from flight_alert.logging import log
from flight_alert.notify import publish_ntfy
from flight_alert.route import RouteResolver


class FlightAlertService:
    def __init__(self, config: Config, *, once: bool = False, dry_run: bool = False) -> None:
        self.config = config
        self.once = once
        self.dry_run = dry_run
        self._running = True
        self._last_alert_by_hex: dict[str, float] = {}
        self._routes = RouteResolver(config)

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)
        log(
            "Watching for widebodies near "
            f"{self.config.home_lat},{self.config.home_lon} "
            f"within {self.config.radius_km} km below {self.config.max_altitude_m:.0f} m"
        )
        log(f"Using ntfy endpoint: {self.config.ntfy_endpoint}")
        while self._running:
            try:
                self.check_once()
            except Exception as exc:  # noqa: BLE001 - keep the daemon alive after transient API failures.
                log(f"check failed: {exc}", error=True)
            if self.once:
                return
            time.sleep(self.config.poll_seconds)

    def check_once(self) -> None:
        aircraft = self.fetch_aircraft()
        self.log_aircraft(aircraft)
        candidates = [
            item
            for item in aircraft
            if is_alert_candidate(
                item,
                widebody_types=self.config.widebody_types,
                max_altitude_m=self.config.max_altitude_m,
                max_stale_seconds=self.config.stale_aircraft_seconds,
            )
        ]
        for item in sorted(candidates, key=lambda a: a.distance_km):
            if self.should_alert(item):
                log(
                    f"alerting {item.display_callsign} {item.aircraft_type} "
                    f"{item.altitude_m:.0f}m {item.distance_km:.1f}km"
                )
                route = self._routes.resolve(item.callsign)
                if route:
                    log(f"route for {item.display_callsign}: 起飞城市={route.departure_display}")
                try:
                    publish_ntfy(self.config, item, route=route, dry_run=self.dry_run)
                    self._last_alert_by_hex[item.hex] = time.time()
                except Exception as exc:  # noqa: BLE001
                    log(f"notification failed for {item.display_callsign}: {exc}", error=True)

    def fetch_aircraft(self) -> list[Aircraft]:
        try:
            return self._fetch_from_url(self.config.aircraft_api_url)
        except error.HTTPError as exc:
            if exc.code == 429:
                log("primary aircraft API returned 429, trying fallback")
                try:
                    return self._fetch_from_url(self.config.fallback_aircraft_api_url)
                except error.HTTPError as fallback_exc:
                    if fallback_exc.code == 429:
                        log("both primary and fallback APIs are rate-limited", error=True)
                        return []
                    raise
            raise

    def _fetch_from_url(self, url_template: str) -> list[Aircraft]:
        url = url_template.format(
            lat=self.config.home_lat,
            lon=self.config.home_lon,
            radius_nm=round(self.config.radius_nm, 2),
        )
        req = request.Request(url, headers={"User-Agent": "flight-alert/0.1"})
        with request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return parse_airplanes_live(payload, self.config.home_lat, self.config.home_lon)

    def should_alert(self, aircraft: Aircraft) -> bool:
        last_alert = self._last_alert_by_hex.get(aircraft.hex)
        if last_alert is None:
            return True
        return time.time() - last_alert >= self.config.alert_cooldown_seconds

    def log_aircraft(self, aircraft: list[Aircraft]) -> None:
        if not aircraft:
            log("no aircraft found nearby")
            return

        log(f"found {len(aircraft)} aircraft nearby")
        for item in sorted(aircraft, key=lambda a: a.distance_km):
            log(
                "plane "
                f"{item.display_callsign} "
                f"hex={item.hex} "
                f"type={item.aircraft_type or 'unknown'} "
                f"alt={self._format_altitude(item)} "
                f"distance={item.distance_km:.1f}km "
                f"registration={item.registration or 'unknown'} "
                f"seen={item.seen_seconds if item.seen_seconds is not None else 'unknown'}s"
            )

    def _stop(self, *_args: object) -> None:
        self._running = False

    @staticmethod
    def _format_altitude(aircraft: Aircraft) -> str:
        if aircraft.altitude_m is None:
            return "unknown"
        return f"{aircraft.altitude_m:.0f}m"
