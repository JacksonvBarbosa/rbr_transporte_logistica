from __future__ import annotations

from rbr_transporte_logistica.dto import RoutePoint, SimulationResult


def test_simulation_result_to_dict_returns_plain_payload():
    origin = RoutePoint(
        label="Origem",
        city="Sao Paulo",
        state="SP",
        latitude=-23.5505,
        longitude=-46.6333,
        point_type="endpoint",
    )
    destination = RoutePoint(
        label="Destino",
        city="Campinas",
        state="SP",
        latitude=-22.9099,
        longitude=-47.0626,
        point_type="endpoint",
    )
    result = SimulationResult(
        partner_id=1,
        partner_name="Parceiro Azul",
        city="Campinas",
        state="SP",
        price=150.0,
        deadline_days=2,
        rule_type="FIXED",
        latitude=-22.9099,
        longitude=-47.0626,
        distance_km=100.0,
        segment_index=1,
        origin_point=origin,
        destination_point=destination,
    )

    assert result.to_dict() == {
        "partner_id": 1,
        "partner_name": "Parceiro Azul",
        "city": "Campinas",
        "state": "SP",
        "price": 150.0,
        "deadline_days": 2,
        "rule_type": "FIXED",
        "latitude": -22.9099,
        "longitude": -47.0626,
        "distance_km": 100.0,
        "segment_index": 1,
        "origin_point": {
            "label": "Origem",
            "city": "Sao Paulo",
            "state": "SP",
            "latitude": -23.5505,
            "longitude": -46.6333,
            "partner_id": None,
            "point_type": "endpoint",
        },
        "destination_point": {
            "label": "Destino",
            "city": "Campinas",
            "state": "SP",
            "latitude": -22.9099,
            "longitude": -47.0626,
            "partner_id": None,
            "point_type": "endpoint",
        },
    }
