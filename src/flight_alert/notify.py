from __future__ import annotations

from urllib import request

from flight_alert.aircraft import Aircraft
from flight_alert.config import Config
from flight_alert.logging import log
from flight_alert.route import RouteInfo


def build_message(aircraft: Aircraft, route: RouteInfo | None = None) -> str:
    lines = [
        f"{aircraft.display_callsign} - {aircraft.aircraft_type or 'unknown type'}",
        f"起飞城市: {route.departure_display if route else 'unknown'}",
        f"Altitude: {_fmt_m(aircraft.altitude_m)}",
        f"Distance: {aircraft.distance_km:.1f} km from home",
    ]
    if aircraft.registration:
        lines.append(f"Registration: {aircraft.registration}")
    if aircraft.speed_kmh is not None:
        lines.append(f"Speed: {aircraft.speed_kmh:.0f} km/h")
    if aircraft.track_deg is not None:
        lines.append(f"Track: {aircraft.track_deg:.0f} deg")
    lines.append("Route: open link to inspect live flight details")
    lines.append(aircraft.tracking_url)
    return "\n".join(lines)


def publish_ntfy(
    config: Config,
    aircraft: Aircraft,
    *,
    route: RouteInfo | None = None,
    dry_run: bool = False,
) -> None:
    body = build_message(aircraft, route).encode("utf-8")
    req = request.Request(
        config.ntfy_endpoint,
        data=body,
        method="POST",
        headers={
            "Title": f"Widebody over Weesp: {aircraft.display_callsign}",
            "Priority": config.ntfy_priority,
            "Tags": config.ntfy_tags,
            "Click": aircraft.tracking_url,
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    if dry_run:
        log(f"[dry-run] would publish to {config.ntfy_endpoint}")
        log(body.decode("utf-8").replace("\n", " | "))
        return
    with request.urlopen(req, timeout=10) as response:
        response.read()
        status = getattr(response, "status", response.getcode())
    print(
        f"ntfy published {aircraft.display_callsign} to {config.ntfy_endpoint} "
        f"status={status}",
        flush=True,
    )


def _fmt_m(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.0f} m"
