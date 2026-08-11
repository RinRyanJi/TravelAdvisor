"""Weather via Open-Meteo (free, key-less, https://open-meteo.com)."""

from __future__ import annotations

from datetime import date

from ..models import Coordinates, DayWeather, WeatherCondition
from .http import new_client

# WMO weather interpretation codes -> our coarse condition.
# https://open-meteo.com/en/docs  (see "WMO Weather interpretation codes")
_WMO: dict[int, WeatherCondition] = {
    0: WeatherCondition.CLEAR,
    1: WeatherCondition.CLEAR,
    2: WeatherCondition.CLOUDY,
    3: WeatherCondition.CLOUDY,
    45: WeatherCondition.CLOUDY,
    48: WeatherCondition.CLOUDY,
    51: WeatherCondition.RAIN,
    53: WeatherCondition.RAIN,
    55: WeatherCondition.RAIN,
    56: WeatherCondition.RAIN,
    57: WeatherCondition.RAIN,
    61: WeatherCondition.RAIN,
    63: WeatherCondition.RAIN,
    65: WeatherCondition.RAIN,
    66: WeatherCondition.RAIN,
    67: WeatherCondition.RAIN,
    71: WeatherCondition.SNOW,
    73: WeatherCondition.SNOW,
    75: WeatherCondition.SNOW,
    77: WeatherCondition.SNOW,
    80: WeatherCondition.RAIN,
    81: WeatherCondition.RAIN,
    82: WeatherCondition.STORM,
    85: WeatherCondition.SNOW,
    86: WeatherCondition.SNOW,
    95: WeatherCondition.STORM,
    96: WeatherCondition.STORM,
    99: WeatherCondition.STORM,
}


def _condition_for(code: int | None) -> WeatherCondition:
    if code is None:
        return WeatherCondition.UNKNOWN
    return _WMO.get(int(code), WeatherCondition.UNKNOWN)


class OpenMeteoWeatherProvider:
    """Daily forecast provider backed by Open-Meteo.

    Open-Meteo only forecasts ~16 days ahead; dates outside that horizon simply
    come back as ``UNKNOWN``, which the engine treats as "no weather signal".
    """

    BASE_URL = "https://api.open-meteo.com"

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or self.BASE_URL

    def forecast(
        self,
        coords: Coordinates,
        start: date,
        end: date,
    ) -> dict[date, DayWeather]:
        params = {
            "latitude": coords.lat,
            "longitude": coords.lon,
            "daily": ",".join(
                [
                    "weathercode",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                ]
            ),
            "timezone": "auto",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        with new_client(self._base_url) as client:
            resp = client.get("/v1/forecast", params=params)
            resp.raise_for_status()
            payload = resp.json()
        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict) -> dict[date, DayWeather]:
        daily = payload.get("daily") or {}
        days = daily.get("time") or []
        codes = daily.get("weathercode") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        pprob = daily.get("precipitation_probability_max") or []

        def at(seq: list, i: int):
            return seq[i] if i < len(seq) else None

        out: dict[date, DayWeather] = {}
        for i, day_str in enumerate(days):
            d = date.fromisoformat(day_str)
            out[d] = DayWeather(
                date=d,
                condition=_condition_for(at(codes, i)),
                temp_max_c=at(tmax, i),
                temp_min_c=at(tmin, i),
                precipitation_probability=at(pprob, i),
            )
        return out
