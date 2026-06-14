import unittest

from flight_alert.aircraft import altitude_to_meters, is_alert_candidate, parse_airplanes_live
from flight_alert.config import DEFAULT_WIDEBODY_TYPES
from flight_alert.notify import build_message
from flight_alert.route import RouteInfo, parse_route_payload


class AircraftTest(unittest.TestCase):
    def test_parse_airplanes_live_candidate(self) -> None:
        payload = {
            "ac": [
                {
                    "hex": "48418c",
                    "flight": "KLM895 ",
                    "t": "B789",
                    "r": "PH-BHC",
                    "alt_geom": 2500,
                    "lat": 52.31,
                    "lon": 5.04,
                    "gs": 220,
                    "track": 180,
                    "seen_pos": 2,
                }
            ]
        }

        aircraft = parse_airplanes_live(payload, 52.3076, 5.0413)[0]

        self.assertEqual(aircraft.hex, "48418c")
        self.assertEqual(aircraft.callsign, "KLM895")
        self.assertEqual(aircraft.aircraft_type, "B789")
        self.assertEqual(aircraft.altitude_m, 762)
        self.assertTrue(
            is_alert_candidate(
                aircraft,
                widebody_types=frozenset(DEFAULT_WIDEBODY_TYPES),
                max_altitude_m=1000,
                max_stale_seconds=30,
            )
        )

    def test_altitude_ignores_ground(self) -> None:
        self.assertIsNone(altitude_to_meters("ground"))

    def test_notification_includes_departure_city(self) -> None:
        aircraft = parse_airplanes_live(
            {
                "ac": [
                    {
                        "hex": "48418c",
                        "flight": "KLM895",
                        "t": "B789",
                        "alt_geom": 2500,
                        "lat": 52.31,
                        "lon": 5.04,
                    }
                ]
            },
            52.3076,
            5.0413,
        )[0]
        message = build_message(aircraft, RouteInfo(departure_city="Amsterdam", departure_airport="AMS"))

        self.assertIn("起飞城市: Amsterdam (AMS)", message)

    def test_parse_adsbdb_style_route_payload(self) -> None:
        route = parse_route_payload(
            {
                "response": {
                    "flightroute": {
                        "origin": {"municipality": "Amsterdam", "iata_code": "AMS"},
                        "destination": {"municipality": "Shanghai", "iata_code": "PVG"},
                    }
                }
            }
        )

        self.assertIsNotNone(route)
        self.assertEqual(route.departure_display, "Amsterdam (AMS)")


if __name__ == "__main__":
    unittest.main()
