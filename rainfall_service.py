import httpx
from datetime import date, timedelta


# Fallback value used only if BOTH live API calls fail
FALLBACK_ANNUAL_RAINFALL_MM = 1100.0

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# NEW: simple in-memory cache so repeated requests for the same (rounded)
# location don't hit the external API again and again during testing/demo.
# Key: (rounded_lat, rounded_lon) -> rainfall_mm
_rainfall_cache = {}


def _cache_key(latitude: float, longitude: float):
    # Round to 3 decimal places (~100m precision) so nearby points share a cache entry
    return (round(latitude, 3), round(longitude, 3))


async def _fetch_from_open_meteo(client: httpx.AsyncClient, latitude: float, longitude: float):
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=365)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "precipitation_sum",
        "timezone": "auto"
    }

    response = await client.get(OPEN_METEO_ARCHIVE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    daily_values = data.get("daily", {}).get("precipitation_sum", [])
    valid_values = [v for v in daily_values if v is not None]

    if not valid_values:
        raise ValueError("Open-Meteo returned no usable rainfall data")

    return float(sum(valid_values))


async def _fetch_from_nasa_power(client: httpx.AsyncClient, latitude: float, longitude: float):
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=365)

    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON"
    }

    response = await client.get(NASA_POWER_URL, params=params)
    response.raise_for_status()
    data = response.json()

    daily_dict = data.get("properties", {}).get("parameter", {}).get("PRECTOTCORR", {})
    valid_values = [v for v in daily_dict.values() if v is not None and v >= 0]

    if not valid_values:
        raise ValueError("NASA POWER returned no usable rainfall data")

    return float(sum(valid_values))


async def fetch_annual_rainfall(latitude: float, longitude: float) -> float:
    """
    Fetches total rainfall (mm) for the past 365 days at the given
    coordinates. Tries Open-Meteo first, falls back to NASA POWER if
    that fails (e.g. rate-limited), and finally falls back to a fixed
    default value if both external calls fail. Results are cached in
    memory per location to avoid repeated calls during testing/demo.
    """
    key = _cache_key(latitude, longitude)
    if key in _rainfall_cache:
        return _rainfall_cache[key]

    rainfall_mm = None

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Try Open-Meteo first
        try:
            rainfall_mm = await _fetch_from_open_meteo(client, latitude, longitude)
        except Exception as e:
            print(f"OPEN-METEO ERROR: {e}")

        # If Open-Meteo failed, try NASA POWER as a backup source
        if rainfall_mm is None:
            try:
                rainfall_mm = await _fetch_from_nasa_power(client, latitude, longitude)
            except Exception as e:
                print(f"NASA POWER ERROR: {e}")

    # If both external sources failed, use the fixed fallback
    if rainfall_mm is None:
        rainfall_mm = FALLBACK_ANNUAL_RAINFALL_MM

    _rainfall_cache[key] = rainfall_mm
    return rainfall_mm