# Flight Alert

Notify both iPhones via ntfy when a low widebody aircraft passes near Weesp, Netherlands.

The service polls Airplanes.live around your home coordinates, filters aircraft by altitude and ICAO type code, deduplicates repeated sightings, and publishes a notification to the ntfy topic `over-weesp-flights-alerts`.

## What You Get

Notifications include:

- Flight callsign when available
- Aircraft ICAO type, for example `B789` or `A388`
- Registration when available
- Altitude and distance from home
- A link to inspect the aircraft live on Airplanes.live

Route origin/destination is not reliably present in raw ADS-B data. The notification includes a live tracking link so you can inspect route details when the tracking site has them.

## iPhone Setup

1. Install the ntfy app from the iOS App Store on both phones.
2. Subscribe both phones to:

   ```text
   over-weesp-flights-alerts
   ```

Public ntfy topics are shared secrets. Anyone who knows the topic can subscribe or publish. For more privacy, self-host ntfy or change `NTFY_TOPIC` to a long random value.

## Local Setup

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create config:

```bash
cp .env.example .env
```

Run one dry check:

```bash
PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python -m flight_alert.cli --once --dry-run
```

Run continuously:

```bash
PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python -m flight_alert.cli
```

## Deploy With PM2

On the KVM:

```bash
git clone <your-repo-url> flight-alert
cd flight-alert
cp .env.example .env
PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python -m flight_alert.cli --once --dry-run
pm2 start ecosystem.config.cjs
pm2 save
```

Check logs:

```bash
pm2 logs flight-alert
```

Restart after changing `.env`:

```bash
pm2 restart flight-alert
```

## Configuration

Edit `.env`:

```text
HOME_LAT=52.3076
HOME_LON=5.0413
RADIUS_KM=5
MAX_ALTITUDE_M=1000
POLL_SECONDS=10
ALERT_COOLDOWN_SECONDS=1800
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=over-weesp-flights-alerts
```

The default widebody allowlist includes common Airbus and Boeing widebodies such as A330, A350, A380, B767, B777, B787, and B747.

## Development

Run tests:

```bash
PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python -m unittest discover -s tests
```

Run one real polling cycle without sending notifications:

```bash
PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python -m flight_alert.cli --once --dry-run
```
