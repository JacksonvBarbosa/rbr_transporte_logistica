from __future__ import annotations

from types import SimpleNamespace

import pytest

from rbr_transporte_logistica.dto import RoutePoint
from rbr_transporte_logistica.services import route_builder


def _partner(
    partner_id: int,
    name: str,
    latitude: float,
    longitude: float,
    max_km: float,
):
    return SimpleNamespace(
        id=partner_id,
        name=name,
        city=name,
        state="SP",
        latitude=latitude,
        longitude=longitude,
        freight_rules=[SimpleNamespace(max_km=max_km, deadline_days=2)],
    )


def _distance_fn(distance_map: dict[tuple[tuple[float, float], tuple[float, float]], float]):
    def _calculate(origin: tuple[float, float], destination: tuple[float, float]) -> float:
        key = (origin, destination)
        if key in distance_map:
            return distance_map[key]
        reverse_key = (destination, origin)
        if reverse_key in distance_map:
            return distance_map[reverse_key]
        return 999999.0

    return _calculate


def test_build_route_with_one_partner(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Santos", "SP", 10.0, 10.0, point_type="endpoint")
    partner_a = _partner(1, "Partner A", 1.0, 1.0, 100.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn({((0.0, 0.0), (10.0, 10.0)): 90.0}),
    )

    route = route_builder.build_route(origin, destination, [partner_a])

    assert [point.label for point in route] == ["Origem", "Partner A", "Destino"]


def test_build_route_with_multiple_partners(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Camamu", "BA", 30.0, 30.0, point_type="endpoint")
    partner_a = _partner(1, "Partner A", 5.0, 5.0, 260.0)
    partner_b = _partner(2, "Partner B", 15.0, 15.0, 250.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn(
            {
                ((0.0, 0.0), (5.0, 5.0)): 100.0,
                ((5.0, 5.0), (15.0, 15.0)): 140.0,
                ((15.0, 15.0), (30.0, 30.0)): 200.0,
                ((0.0, 0.0), (30.0, 30.0)): 700.0,
            }
        ),
    )

    route = route_builder.build_route(origin, destination, [partner_a, partner_b])

    assert [point.label for point in route] == ["Origem", "Partner A", "Partner B", "Destino"]


def test_filter_valid_partners_returns_only_routeable_entries(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Camamu", "BA", 30.0, 30.0, point_type="endpoint")
    partner_a = _partner(1, "Partner A", 5.0, 5.0, 260.0)
    partner_b = _partner(2, "Partner B", 15.0, 15.0, 250.0)
    partner_c = _partner(3, "Partner C", 50.0, 50.0, 40.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn(
            {
                ((0.0, 0.0), (5.0, 5.0)): 100.0,
                ((5.0, 5.0), (15.0, 15.0)): 140.0,
                ((15.0, 15.0), (30.0, 30.0)): 200.0,
                ((0.0, 0.0), (30.0, 30.0)): 700.0,
                ((0.0, 0.0), (50.0, 50.0)): 900.0,
                ((50.0, 50.0), (30.0, 30.0)): 600.0,
            }
        ),
    )

    valid_partners = route_builder.filter_valid_partners(origin, destination, [partner_a, partner_b, partner_c])

    assert [partner.id for partner in valid_partners] == [1, 2]


def test_hub_partner_uses_base_detour_for_delivery(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Santos", "SP", 10.0, 10.0, point_type="endpoint")
    partner_hub = _partner(1, "Partner Hub", 4.0, 4.0, 100.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn(
            {
                ((0.0, 0.0), (4.0, 4.0)): 30.0,
                ((4.0, 4.0), (10.0, 10.0)): 60.0,
                ((0.0, 0.0), (10.0, 10.0)): 70.0,
            }
        ),
    )

    assert route_builder.can_partner_deliver(partner_hub, origin, destination, "HUB") is True
    assert route_builder.calculate_effective_distance(partner_hub, origin, destination, "HUB") == 90.0


def test_last_segment_defaults_to_direct():
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Santos", "SP", 10.0, 10.0, point_type="endpoint")
    partner_a = RoutePoint("Partner A", "Campinas", "SP", 1.0, 1.0, partner_id=1, point_type="partner")
    partner_b = RoutePoint("Partner B", "Sorocaba", "SP", 2.0, 2.0, partner_id=2, point_type="partner")

    assert route_builder.resolve_segment_pickup_modes([origin, partner_a, partner_b, destination]) == [
        "HUB",
        "DIRECT",
    ]


def test_build_route_raises_when_route_is_impossible(monkeypatch):
    origin = RoutePoint("Origem", "Guarulhos", "SP", 0.0, 0.0, point_type="endpoint")
    destination = RoutePoint("Destino", "Camamu", "BA", 30.0, 30.0, point_type="endpoint")
    partner_a = _partner(1, "Partner A", 5.0, 5.0, 80.0)

    monkeypatch.setattr(
        route_builder,
        "calculate_distance_km",
        _distance_fn({((0.0, 0.0), (30.0, 30.0)): 120.0}),
    )

    with pytest.raises(ValueError, match="No valid route found"):
        route_builder.build_route(origin, destination, [partner_a])
