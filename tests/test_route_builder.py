from __future__ import annotations

from types import SimpleNamespace

import pytest

from rbr_transporte_logistica.dto import RoutePoint
from rbr_transporte_logistica.services import route_builder


def _partner(partner_id: int, name: str, latitude: float, longitude: float, max_km: float):
    return SimpleNamespace(
        id=partner_id,
        name=name,
        city=name,
        state="SP",
        latitude=latitude,
        longitude=longitude,
        freight_rules=[SimpleNamespace(max_km=max_km)],
    )


def _distance_fn(distance_map: dict[tuple[tuple[float, float], tuple[float, float]], float]):
    def _calculate(origin: tuple[float, float], destination: tuple[float, float]) -> float:
        key = (origin, destination)
        if key in distance_map:
            return distance_map[key]
        reverse_key = (destination, origin)
        if reverse_key in distance_map:
            return distance_map[reverse_key]
        raise AssertionError(f"Distancia nao mapeada para {origin} -> {destination}")

    return _calculate


def test_build_route_with_one_partner(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Santos", "SP", 10.0, 10.0, point_type="endpoint")
    partner_a = _partner(1, "Partner A", 1.0, 1.0, 100.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn(
            {
                ((0.0, 0.0), (1.0, 1.0)): 50.0,
                ((1.0, 1.0), (10.0, 10.0)): 70.0,
            }
        ),
    )

    route = route_builder.build_route(origin, destination, [partner_a])

    assert [point.label for point in route] == ["Origem", "Partner A", "Destino"]


def test_build_route_with_multiple_partners(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Camamu", "BA", 30.0, 30.0, point_type="endpoint")
    partner_a = _partner(1, "Partner A", 5.0, 5.0, 120.0)
    partner_b = _partner(2, "Partner B", 15.0, 15.0, 250.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn(
            {
                ((0.0, 0.0), (5.0, 5.0)): 100.0,
                ((0.0, 0.0), (15.0, 15.0)): 300.0,
                ((5.0, 5.0), (15.0, 15.0)): 140.0,
                ((5.0, 5.0), (30.0, 30.0)): 500.0,
                ((15.0, 15.0), (30.0, 30.0)): 200.0,
            }
        ),
    )

    route = route_builder.build_route(origin, destination, [partner_a, partner_b])

    assert [point.label for point in route] == ["Origem", "Partner A", "Partner B", "Destino"]


def test_build_route_raises_when_route_is_impossible(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Camamu", "BA", 30.0, 30.0, point_type="endpoint")
    partner_a = _partner(1, "Partner A", 5.0, 5.0, 80.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn(
            {
                ((0.0, 0.0), (5.0, 5.0)): 100.0,
                ((5.0, 5.0), (30.0, 30.0)): 400.0,
            }
        ),
    )

    with pytest.raises(ValueError, match="No valid route found"):
        route_builder.build_route(origin, destination, [partner_a])
