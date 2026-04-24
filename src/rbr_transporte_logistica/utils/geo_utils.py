from __future__ import annotations

from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from typing import Iterable

from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim


GEOCODER = Nominatim(user_agent="rbr_transporte_logistica")


@lru_cache(maxsize=256)
def get_coordinates(city: str, state: str) -> tuple[float, float]:
    query = f"{city.strip()}, {state.strip().upper()}, Brasil"
    try:
        location = GEOCODER.geocode(query, exactly_one=True, timeout=10)
    except (GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable) as exc:
        raise ValueError("Nao foi possivel consultar o servico de geolocalizacao.") from exc

    if not location:
        raise ValueError(f"Localidade nao encontrada para '{city}/{state}'.")
    return float(location.latitude), float(location.longitude)


def calculate_distance_km(
    origin: tuple[float, float], destination: tuple[float, float], precision: int = 2
) -> float:
    return round(float(geodesic(origin, destination).km), precision)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(a))


def map_center(points: Iterable[tuple[float, float]]) -> tuple[float, float]:
    points_list = list(points)
    if not points_list:
        return (-14.2350, -51.9253)
    lat = sum(point[0] for point in points_list) / len(points_list)
    lon = sum(point[1] for point in points_list) / len(points_list)
    return lat, lon
