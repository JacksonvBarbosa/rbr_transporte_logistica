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
