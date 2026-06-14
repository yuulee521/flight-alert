from __future__ import annotations

import argparse

from flight_alert.config import load_config
from flight_alert.service import FlightAlertService


def main() -> None:
    parser = argparse.ArgumentParser(description="Notify ntfy when low widebody aircraft pass over Weesp.")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Log notifications instead of sending them.")
    args = parser.parse_args()

    service = FlightAlertService(load_config(), once=args.once, dry_run=args.dry_run)
    service.run()


if __name__ == "__main__":
    main()
