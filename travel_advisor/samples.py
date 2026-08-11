"""A small offline dataset so the engine can be demonstrated and tested without
touching the network. Real runs use the providers in :mod:`travel_advisor.providers`."""

from __future__ import annotations

from datetime import date

from .models import (
    Coordinates,
    Interest,
    Pace,
    PlaceCategory,
    PointOfInterest,
    TripRequest,
)

# A handful of real Kyoto points of interest with plausible attributes.
KYOTO_POIS: list[PointOfInterest] = [
    PointOfInterest(
        id="sample/kinkakuji", name="Kinkaku-ji (Golden Pavilion)",
        category=PlaceCategory.SIGHT, coordinates=Coordinates(lat=35.0394, lon=135.7292),
        indoor=False, visit_duration_minutes=60, estimated_cost=5, rating=4.7,
    ),
    PointOfInterest(
        id="sample/fushimi-inari", name="Fushimi Inari Taisha",
        category=PlaceCategory.SIGHT, coordinates=Coordinates(lat=34.9671, lon=135.7727),
        indoor=False, visit_duration_minutes=90, estimated_cost=0, rating=4.8,
    ),
    PointOfInterest(
        id="sample/national-museum", name="Kyoto National Museum",
        category=PlaceCategory.MUSEUM, coordinates=Coordinates(lat=34.9903, lon=135.7731),
        indoor=True, visit_duration_minutes=120, estimated_cost=7, rating=4.5,
    ),
    PointOfInterest(
        id="sample/nishiki", name="Nishiki Market",
        category=PlaceCategory.SHOPPING, coordinates=Coordinates(lat=35.0050, lon=135.7649),
        indoor=True, visit_duration_minutes=60, estimated_cost=0, rating=4.4,
    ),
    PointOfInterest(
        id="sample/arashiyama", name="Arashiyama Bamboo Grove",
        category=PlaceCategory.NATURE, coordinates=Coordinates(lat=35.0170, lon=135.6716),
        indoor=False, visit_duration_minutes=75, estimated_cost=0, rating=4.6,
    ),
    PointOfInterest(
        id="sample/railway-museum", name="Kyoto Railway Museum",
        category=PlaceCategory.MUSEUM, coordinates=Coordinates(lat=34.9877, lon=135.7470),
        indoor=True, visit_duration_minutes=120, estimated_cost=12, rating=4.6,
    ),
    PointOfInterest(
        id="sample/gion", name="Gion District",
        category=PlaceCategory.LANDMARK, coordinates=Coordinates(lat=35.0037, lon=135.7752),
        indoor=False, visit_duration_minutes=60, estimated_cost=0, rating=4.5,
    ),
    PointOfInterest(
        id="sample/nijo", name="Nijo Castle",
        category=PlaceCategory.LANDMARK, coordinates=Coordinates(lat=35.0142, lon=135.7481),
        indoor=False, visit_duration_minutes=90, estimated_cost=8, rating=4.5,
    ),
    PointOfInterest(
        id="sample/manga-museum", name="Kyoto International Manga Museum",
        category=PlaceCategory.MUSEUM, coordinates=Coordinates(lat=35.0170, lon=135.7590),
        indoor=True, visit_duration_minutes=90, estimated_cost=9, rating=4.3,
    ),
    PointOfInterest(
        id="sample/maruyama", name="Maruyama Park",
        category=PlaceCategory.PARK, coordinates=Coordinates(lat=35.0035, lon=135.7809),
        indoor=False, visit_duration_minutes=45, estimated_cost=0, rating=4.2,
    ),
    PointOfInterest(
        id="sample/aquarium", name="Kyoto Aquarium",
        category=PlaceCategory.ENTERTAINMENT, coordinates=Coordinates(lat=34.9884, lon=135.7477),
        indoor=True, visit_duration_minutes=90, estimated_cost=20, rating=4.4,
    ),
    PointOfInterest(
        id="sample/toei-park", name="Toei Kyoto Studio Park",
        category=PlaceCategory.ENTERTAINMENT, coordinates=Coordinates(lat=35.0158, lon=135.6835),
        indoor=True, visit_duration_minutes=150, estimated_cost=22, rating=4.1,
    ),
    PointOfInterest(
        id="sample/ginkakuji", name="Ginkaku-ji (Silver Pavilion)",
        category=PlaceCategory.SIGHT, coordinates=Coordinates(lat=35.0270, lon=135.7982),
        indoor=False, visit_duration_minutes=60, estimated_cost=5, rating=4.6,
    ),
    PointOfInterest(
        id="sample/imperial-palace", name="Kyoto Imperial Palace",
        category=PlaceCategory.LANDMARK, coordinates=Coordinates(lat=35.0254, lon=135.7621),
        indoor=False, visit_duration_minutes=75, estimated_cost=0, rating=4.4,
    ),
]

# A rough hotel location near Kyoto Station to anchor each day.
KYOTO_BASE = Coordinates(lat=34.9858, lon=135.7588)


def sample_kyoto_request() -> TripRequest:
    return TripRequest(
        destination="Kyoto, Japan",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        party_size=2,
        interests=[Interest.HISTORY, Interest.ART, Interest.NATURE],
        pace=Pace.BALANCED,
        base_location=KYOTO_BASE,
    )
