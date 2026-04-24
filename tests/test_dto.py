from __future__ import annotations

from rbr_transporte_logistica.dto import SimulationResult


def test_simulation_result_to_dict_returns_plain_payload():
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
    }
