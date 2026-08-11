"""Points of interest via the OpenStreetMap Overpass API (free, key-less)."""

from __future__ import annotations

from ..models import Coordinates, OpeningHours, PlaceCategory, PointOfInterest
from .http import new_client

# Each category maps to a list of OSM ``key=value`` tag filters. A POI matches
# the category if it carries any of the tags.
_CATEGORY_FILTERS: dict[PlaceCategory, list[tuple[str, str]]] = {
    PlaceCategory.MUSEUM: [("tourism", "museum")],
    PlaceCategory.GALLERY: [("tourism", "gallery"), ("tourism", "artwork")],
    PlaceCategory.SIGHT: [("tourism", "attraction"), ("tourism", "viewpoint")],
    PlaceCategory.LANDMARK: [
        ("historic", "monument"),
        ("historic", "memorial"),
        ("historic", "castle"),
    ],
    PlaceCategory.PARK: [("leisure", "park"), ("leisure", "garden")],
    PlaceCategory.NATURE: [("leisure", "nature_reserve"), ("natural", "beach")],
    PlaceCategory.RESTAURANT: [("amenity", "restaurant")],
    PlaceCategory.CAFE: [("amenity", "cafe")],
    PlaceCategory.BAR: [("amenity", "bar"), ("amenity", "pub")],
    PlaceCategory.SHOPPING: [("shop", "mall"), ("shop", "department_store")],
    PlaceCategory.ENTERTAINMENT: [
        ("tourism", "theme_park"),
        ("amenity", "cinema"),
        ("amenity", "theatre"),
    ],
}

# Categories whose visits are sheltered — used for rainy-day substitution.
_INDOOR = {
    PlaceCategory.MUSEUM,
    PlaceCategory.GALLERY,
    PlaceCategory.RESTAURANT,
    PlaceCategory.CAFE,
    PlaceCategory.BAR,
    PlaceCategory.SHOPPING,
    PlaceCategory.ENTERTAINMENT,
}

# Sensible default dwell times (minutes) per category.
_DEFAULT_DURATION: dict[PlaceCategory, int] = {
    PlaceCategory.MUSEUM: 120,
    PlaceCategory.GALLERY: 90,
    PlaceCategory.SIGHT: 60,
    PlaceCategory.LANDMARK: 45,
    PlaceCategory.PARK: 75,
    PlaceCategory.NATURE: 90,
    PlaceCategory.RESTAURANT: 75,
    PlaceCategory.CAFE: 45,
    PlaceCategory.BAR: 90,
    PlaceCategory.SHOPPING: 90,
    PlaceCategory.ENTERTAINMENT: 120,
}

# Reverse index so a matched tag tells us the category.
_TAG_TO_CATEGORY: dict[tuple[str, str], PlaceCategory] = {
    tag: cat for cat, tags in _CATEGORY_FILTERS.items() for tag in tags
}


class OverpassPoiProvider:
    """Fetch candidate POIs around a point from OpenStreetMap."""

    BASE_URL = "https://overpass-api.de"

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or self.BASE_URL

    def find_pois(
        self,
        center: Coordinates,
        *,
        categories: set[PlaceCategory],
        radius_m: int = 4000,
        limit: int = 60,
    ) -> list[PointOfInterest]:
        wanted = [c for c in categories if c in _CATEGORY_FILTERS]
        if not wanted:
            return []
        query = self._build_query(center, wanted, radius_m, limit)
        with new_client(self._base_url) as client:
            resp = client.post("/api/interpreter", data={"data": query})
            resp.raise_for_status()
            payload = resp.json()
        return self._parse(payload, center, limit)

    @staticmethod
    def _build_query(
        center: Coordinates,
        categories: list[PlaceCategory],
        radius_m: int,
        limit: int,
    ) -> str:
        clauses: list[str] = []
        area = f"(around:{radius_m},{center.lat},{center.lon})"
        for cat in categories:
            for key, value in _CATEGORY_FILTERS[cat]:
                # named POIs only — an unnamed node is not something we can plan.
                clauses.append(f'  node["{key}"="{value}"]["name"]{area};')
                clauses.append(f'  way["{key}"="{value}"]["name"]{area};')
        body = "\n".join(clauses)
        return f"[out:json][timeout:25];\n(\n{body}\n);\nout center {limit * 2};"

    @classmethod
    def _parse(
        cls,
        payload: dict,
        center: Coordinates,
        limit: int,
    ) -> list[PointOfInterest]:
        pois: list[PointOfInterest] = []
        seen: set[str] = set()
        for el in payload.get("elements", []):
            tags = el.get("tags") or {}
            name = tags.get("name")
            if not name:
                continue
            category = cls._category_of(tags)
            if category is None:
                continue
            coords = cls._coords_of(el)
            if coords is None:
                continue
            osm_id = f"{el.get('type', 'node')}/{el.get('id')}"
            if osm_id in seen:
                continue
            seen.add(osm_id)
            pois.append(
                PointOfInterest(
                    id=osm_id,
                    name=name,
                    category=category,
                    coordinates=coords,
                    indoor=category in _INDOOR,
                    opening_hours=cls._parse_hours(tags.get("opening_hours")),
                    visit_duration_minutes=_DEFAULT_DURATION.get(category, 60),
                    interests=set(),
                    source="overpass",
                    raw={"tags": tags},
                )
            )
        # Nearest first — a stable, sensible ordering for the engine to draw from.
        pois.sort(key=lambda p: center.distance_km(p.coordinates))
        return pois[:limit]

    @staticmethod
    def _category_of(tags: dict) -> PlaceCategory | None:
        for key, value in tags.items():
            cat = _TAG_TO_CATEGORY.get((key, value))
            if cat is not None:
                return cat
        return None

    @staticmethod
    def _coords_of(el: dict) -> Coordinates | None:
        if "lat" in el and "lon" in el:
            return Coordinates(lat=el["lat"], lon=el["lon"])
        center = el.get("center")
        if center:
            return Coordinates(lat=center["lat"], lon=center["lon"])
        return None

    @staticmethod
    def _parse_hours(_raw: str | None) -> OpeningHours | None:
        # OSM's ``opening_hours`` grammar is large; parsing it fully is out of
        # scope for the MVP. We treat hours as unknown (always available) rather
        # than risk mis-parsing and dropping a valid POI. This is the single
        # obvious place to slot a real opening_hours parser later.
        return None
