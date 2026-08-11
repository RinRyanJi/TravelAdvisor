"""Weather forecast model used to make the plan weather-aware."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel


class WeatherCondition(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    STORM = "storm"
    UNKNOWN = "unknown"

    @property
    def is_wet(self) -> bool:
        return self in {WeatherCondition.RAIN, WeatherCondition.SNOW, WeatherCondition.STORM}


class DayWeather(BaseModel):
    """A single day's forecast for the destination."""

    date: date
    condition: WeatherCondition = WeatherCondition.UNKNOWN
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    precipitation_probability: int | None = None  # percent, 0..100

    @property
    def is_wet(self) -> bool:
        """A day worth steering indoors: wet condition or high rain chance."""
        if self.condition.is_wet:
            return True
        return self.precipitation_probability is not None and self.precipitation_probability >= 60
