import httpx
from datetime import date, timedelta


FALLBACK_ANNUAL_RAINFALL_MM = 1100.0

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

_rainfall_cache = {}


def _cache_key(latitude: float, longitude: float):
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
    Fetches total rainfall (mm) with a strict 1.5s timeout.
    If outbound internet is unavailable (e.g. lab environment),
    instantly returns standard annual rainfall fallback (1100.0 mm)
    without blocking the API worker.
    """
    key = _cache_key(latitude, longitude)
    if key in _rainfall_cache:
        return _rainfall_cache[key]

    rainfall_mm = None

    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            try:
                rainfall_mm = await _fetch_from_open_meteo(client, latitude, longitude)
            except Exception:
                try:
                    rainfall_mm = await _fetch_from_nasa_power(client, latitude, longitude)
                except Exception:
                    pass
    except Exception:
        pass

    if rainfall_mm is None:
        rainfall_mm = FALLBACK_ANNUAL_RAINFALL_MM

    _rainfall_cache[key] = rainfall_mm
    return rainfall_mm