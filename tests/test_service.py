import json
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from flight_alert.config import Config
from flight_alert.service import FlightAlertService


class ServiceTest(unittest.TestCase):
    def test_fetch_aircraft_falls_back_on_429(self) -> None:
        config = Config(
            aircraft_api_url="https://primary/{lat}/{lon}/{radius_nm}",
            fallback_aircraft_api_url="https://fallback/{lat}/{lon}/{radius_nm}"
        )
        service = FlightAlertService(config)

        # Mock responses
        primary_response = MagicMock()
        primary_response.read.side_effect = HTTPError("https://primary/...", 429, "Too Many Requests", {}, BytesIO(b""))

        fallback_payload = {"ac": [{"hex": "abcdef", "lat": 52.3, "lon": 5.0, "alt_geom": 2000}]}
        fallback_response = MagicMock()
        fallback_response.read.return_value = json.dumps(fallback_payload).encode("utf-8")
        fallback_response.__enter__.return_value = fallback_response

        # We need to mock urlopen. Since it's used as a context manager, we need to handle that.
        with patch("flight_alert.service.request.urlopen") as mock_urlopen:
            # First call raises 429
            # Second call returns fallback payload
            mock_urlopen.side_effect = [
                HTTPError("https://primary/...", 429, "Too Many Requests", {}, BytesIO(b"")),
                fallback_response
            ]

            aircraft = service.fetch_aircraft()

            self.assertEqual(len(aircraft), 1)
            self.assertEqual(aircraft[0].hex, "abcdef")

            # Verify it was called twice
            self.assertEqual(mock_urlopen.call_count, 2)

            # Verify URLs
            call_args_list = mock_urlopen.call_args_list
            self.assertIn("https://primary/", call_args_list[0][0][0].full_url)
            self.assertIn("https://fallback/", call_args_list[1][0][0].full_url)

    def test_fetch_aircraft_both_429(self) -> None:
        config = Config(
            aircraft_api_url="https://primary/{lat}/{lon}/{radius_nm}",
            fallback_aircraft_api_url="https://fallback/{lat}/{lon}/{radius_nm}"
        )
        service = FlightAlertService(config)

        with patch("flight_alert.service.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [
                HTTPError("https://primary/...", 429, "Too Many Requests", {}, BytesIO(b"")),
                HTTPError("https://fallback/...", 429, "Too Many Requests", {}, BytesIO(b"")),
            ]

            aircraft = service.fetch_aircraft()
            self.assertEqual(aircraft, [])

    def test_check_once_notification_failure_continues(self) -> None:
        config = Config(
            aircraft_api_url="https://primary/{lat}/{lon}/{radius_nm}",
            widebody_types=frozenset(["A388"])
        )
        service = FlightAlertService(config)

        payload = {
            "ac": [
                {"hex": "aaaaaa", "flight": "TEST1", "t": "A388", "lat": 52.3, "lon": 5.0, "alt_geom": 1000},
                {"hex": "bbbbbb", "flight": "TEST2", "t": "A388", "lat": 52.3, "lon": 5.0, "alt_geom": 1000},
            ]
        }

        with patch("flight_alert.service.request.urlopen") as mock_urlopen, \
             patch("flight_alert.service.publish_ntfy") as mock_publish:

            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(payload).encode("utf-8")
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            # First notification fails, second should still be attempted
            mock_publish.side_effect = [Exception("Failed"), None]

            service.check_once()

            self.assertEqual(mock_publish.call_count, 2)

    def test_fetch_aircraft_raises_other_http_errors(self) -> None:
        config = Config(aircraft_api_url="https://primary/{lat}/{lon}/{radius_nm}")
        service = FlightAlertService(config)

        with patch("flight_alert.service.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError("https://primary/...", 500, "Internal Server Error", {}, BytesIO(b""))

            with self.assertRaises(HTTPError):
                service.fetch_aircraft()

            self.assertEqual(mock_urlopen.call_count, 1)

if __name__ == "__main__":
    unittest.main()
