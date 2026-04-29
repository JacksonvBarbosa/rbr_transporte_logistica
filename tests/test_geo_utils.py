from __future__ import annotations

from types import SimpleNamespace

from rbr_transporte_logistica.utils import geo_utils


def test_get_coordinates_uses_cache(monkeypatch):
    calls = {"count": 0}

    def fake_geocode(query, exactly_one=True, timeout=10):
        calls["count"] += 1
        return SimpleNamespace(latitude=-23.5505, longitude=-46.6333)

    geo_utils.get_coordinates.cache_clear()
    monkeypatch.setattr(geo_utils.GEOCODER, "geocode", fake_geocode)

    first = geo_utils.get_coordinates("Sao Paulo", "SP")
    second = geo_utils.get_coordinates("Sao Paulo", "SP")

    assert first == (-23.5505, -46.6333)
    assert second == first
    assert calls["count"] == 1


def test_calculate_distance_km_returns_positive_distance():
    distance = geo_utils.calculate_distance_km((-23.5505, -46.6333), (-22.9068, -43.1729))

    assert round(distance) == 361


def test_get_coordinates_full_address_uses_full_query_then_returns_coordinates(monkeypatch):
    calls = {"query": None}

    class FakeGeolocator:
        def __init__(self, user_agent: str, timeout: int) -> None:
            calls["user_agent"] = user_agent
            calls["timeout"] = timeout

        def geocode(self, query: str):
            calls["query"] = query
            return SimpleNamespace(latitude=-23.561, longitude=-46.656)

    monkeypatch.setattr(geo_utils, "Nominatim", FakeGeolocator)
    monkeypatch.setattr(geo_utils.time, "sleep", lambda _seconds: None)

    coords = geo_utils.get_coordinates_full_address("Av Paulista, 1000", "Sao Paulo", "SP", "01310-100")

    assert coords == (-23.561, -46.656)
    assert calls["query"] == "Av Paulista, 1000, Sao Paulo, SP, 01310-100, Brasil"


def test_get_coordinates_full_address_falls_back_to_city_lookup(monkeypatch):
    class FakeGeolocator:
        def __init__(self, user_agent: str, timeout: int) -> None:
            self.user_agent = user_agent
            self.timeout = timeout

        def geocode(self, _query: str):
            return None

    monkeypatch.setattr(geo_utils, "Nominatim", FakeGeolocator)
    monkeypatch.setattr(geo_utils.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(geo_utils, "get_coordinates", lambda cidade, uf: (-22.9, -43.1) if (cidade, uf) == ("Rio de Janeiro", "RJ") else (0.0, 0.0))

    coords = geo_utils.get_coordinates_full_address("", "Rio de Janeiro", "RJ")

    assert coords == (-22.9, -43.1)
