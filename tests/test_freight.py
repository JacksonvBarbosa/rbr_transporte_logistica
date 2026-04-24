from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from rbr_transporte_logistica.core.database import Base, create_db_engine
from rbr_transporte_logistica.repositories.freight_repository import FreightRepository
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.services import freight_service as freight_service_module
from rbr_transporte_logistica.services import route_builder as route_builder_module
from rbr_transporte_logistica.services.freight_service import FreightService
from rbr_transporte_logistica.services.partner_service import PartnerService


def make_session():
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def setup_partner_with_rule(
    rule_type: str = "LINEAR",
    extra_config=None,
    *,
    name: str = "Rapido Cargo",
    city: str = "Campinas",
    state: str = "SP",
    latitude: float = -22.9099,
    longitude: float = -47.0626,
):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner = partner_service.create_partner(
        name=name,
        city=city,
        state=state,
        latitude=latitude,
        longitude=longitude,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner.id,
        deadline_days=2,
        rule_type=rule_type,
        base_price=100,
        price_per_km=2.5,
        max_km=500,
        extra_config=extra_config,
    )
    session.commit()
    return session


def test_linear_freight_calculation(monkeypatch):
    session = setup_partner_with_rule()
    freight_service = FreightService(PartnerRepository(session))
    lookup = {("Sao Paulo", "SP"): (0.0, 0.0), ("Campinas", "SP"): (10.0, 10.0)}
    distance_map = {((0.0, 0.0), (10.0, 10.0)): 100.0}
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    result = freight_service.simulate("Sao Paulo", "SP", "Campinas", "SP")

    assert len(result["results"]) == 1
    assert result["best_price"].price == 350.0
    assert result["distance_km"] == 100.0
    assert result["best_price"].route_segments[0].segment_days == 2


def test_fixed_rule_application(monkeypatch):
    session = setup_partner_with_rule("FIXED", {"fixed_price": 420})
    freight_service = FreightService(PartnerRepository(session))
    lookup = {("Sao Paulo", "SP"): (0.0, 0.0), ("Campinas", "SP"): (10.0, 10.0)}
    distance_map = {((0.0, 0.0), (10.0, 10.0)): 250.0}
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    result = freight_service.simulate("Sao Paulo", "SP", "Campinas", "SP")

    assert result["best_price"].price == 420.0


def test_fixed_rule_remains_loaded_after_reload():
    session = setup_partner_with_rule("FIXED", {"fixed_price": 420})
    repository = PartnerRepository(session)

    partner = repository.list_all(active_only=True)[0]
    reloaded_partner = repository.get_by_id(partner.id)

    assert reloaded_partner.freight_rules
    assert reloaded_partner.freight_rules[0].rule_type == "FIXED"


def test_tiered_rule_application(monkeypatch):
    session = setup_partner_with_rule(
        "TIERED",
        {"tiers": [{"up_to_km": 100, "price": 250}, {"up_to_km": 300, "price": 550}]},
    )
    freight_service = FreightService(PartnerRepository(session))
    lookup = {("Sao Paulo", "SP"): (0.0, 0.0), ("Campinas", "SP"): (10.0, 10.0)}
    distance_map = {((0.0, 0.0), (10.0, 10.0)): 280.0}
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    result = freight_service.simulate("Sao Paulo", "SP", "Campinas", "SP")

    assert result["best_price"].price == 550.0


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


def test_multi_leg_route_is_built_automatically_with_one_partner(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_a = partner_service.create_partner(
        name="Partner A",
        city="Campinas",
        state="SP",
        latitude=1.0,
        longitude=1.0,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner_a.id,
        deadline_days=1,
        rule_type="FIXED",
        extra_config={"fixed_price": 200},
        max_km=100.0,
    )
    session.commit()

    lookup = {
        ("Sao Paulo", "SP"): (0.0, 0.0),
        ("Campinas", "SP"): (10.0, 10.0),
    }
    distance_map = {
        ((0.0, 0.0), (1.0, 1.0)): 40.0,
        ((1.0, 1.0), (10.0, 10.0)): 60.0,
        ((0.0, 0.0), (10.0, 10.0)): 90.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))
    route = freight_service.simulate_multi_leg(
        origin_city="Sao Paulo",
        origin_state="SP",
        destination_city="Campinas",
        destination_state="SP",
    )

    assert [point.label for point in route["route_points"]] == ["Origem", "Partner A", "Destino"]
    assert route["selected_partner_ids"] == [partner_a.id]
    assert len(route["segments"]) == 1
    assert [segment.price for segment in route["segments"]] == [200.0]
    assert route["segments"][-1].destination_label == "Destino"
    assert route["total_cost"] == 200.0
    assert route["total_distance_km"] == 90.0
    assert route["total_deadline_days"] == 1
    assert route["manual_override"] is False


def test_multi_leg_route_is_built_automatically_with_multiple_partners(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_a = partner_service.create_partner(
        name="Partner A",
        city="Campinas",
        state="SP",
        latitude=5.0,
        longitude=5.0,
        active=True,
    )
    partner_b = partner_service.create_partner(
        name="Partner B",
        city="Rio de Janeiro",
        state="RJ",
        latitude=15.0,
        longitude=15.0,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner_a.id,
        deadline_days=1,
        rule_type="FIXED",
        extra_config={"fixed_price": 200},
        max_km=260.0,
    )
    partner_service.add_rule(
        partner_id=partner_b.id,
        deadline_days=2,
        rule_type="FIXED",
        extra_config={"fixed_price": 300},
        max_km=250.0,
    )
    session.commit()

    lookup = {
        ("Guarulhos", "SP"): (0.0, 0.0),
        ("Camamu", "BA"): (30.0, 30.0),
    }
    distance_map = {
        ((0.0, 0.0), (5.0, 5.0)): 100.0,
        ((0.0, 0.0), (15.0, 15.0)): 100.0,
        ((5.0, 5.0), (15.0, 15.0)): 140.0,
        ((5.0, 5.0), (30.0, 30.0)): 500.0,
        ((15.0, 15.0), (30.0, 30.0)): 200.0,
        ((0.0, 0.0), (30.0, 30.0)): 700.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))
    route = freight_service.simulate_multi_leg(
        origin_city="Guarulhos",
        origin_state="SP",
        destination_city="Camamu",
        destination_state="BA",
    )

    assert [point.label for point in route["route_points"]] == ["Origem", "Partner A", "Partner B", "Destino"]
    assert route["selected_partner_ids"] == [partner_a.id, partner_b.id]
    assert len(route["segments"]) == 2
    assert [segment.price for segment in route["segments"]] == [200.0, 300.0]
    assert route["total_cost"] == 500.0
    assert route["total_distance_km"] == 440.0
    assert route["total_deadline_days"] == 4
    assert route["segment_pickup_modes"] == ["HUB", "DIRECT"]


def test_multi_leg_route_chooses_lowest_total_cost_then_lowest_time(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_a = partner_service.create_partner(
        name="Partner A",
        city="Campinas",
        state="SP",
        latitude=5.0,
        longitude=5.0,
        active=True,
    )
    partner_b = partner_service.create_partner(
        name="Partner B",
        city="Rio de Janeiro",
        state="RJ",
        latitude=15.0,
        longitude=15.0,
        active=True,
    )
    partner_c = partner_service.create_partner(
        name="Partner C",
        city="Vitoria",
        state="ES",
        latitude=20.0,
        longitude=20.0,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner_a.id,
        deadline_days=1,
        rule_type="FIXED",
        extra_config={"fixed_price": 200},
        max_km=260.0,
    )
    partner_service.add_rule(
        partner_id=partner_b.id,
        deadline_days=2,
        rule_type="FIXED",
        extra_config={"fixed_price": 300},
        max_km=250.0,
    )
    partner_service.add_rule(
        partner_id=partner_c.id,
        deadline_days=1,
        rule_type="FIXED",
        extra_config={"fixed_price": 700},
        max_km=400.0,
    )
    session.commit()

    lookup = {("Guarulhos", "SP"): (0.0, 0.0), ("Camamu", "BA"): (30.0, 30.0)}
    distance_map = {
        ((0.0, 0.0), (5.0, 5.0)): 100.0,
        ((0.0, 0.0), (15.0, 15.0)): 100.0,
        ((0.0, 0.0), (20.0, 20.0)): 310.0,
        ((5.0, 5.0), (15.0, 15.0)): 140.0,
        ((5.0, 5.0), (20.0, 20.0)): 160.0,
        ((15.0, 15.0), (30.0, 30.0)): 200.0,
        ((20.0, 20.0), (30.0, 30.0)): 190.0,
        ((0.0, 0.0), (30.0, 30.0)): 700.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))
    route = freight_service.simulate_multi_leg(
        origin_city="Guarulhos",
        origin_state="SP",
        destination_city="Camamu",
        destination_state="BA",
    )

    assert route["selected_partner_ids"] == [partner_a.id, partner_b.id]
    assert route["total_cost"] == 500.0


def test_hub_pickup_mode_adds_detour_and_extra_day(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_hub = partner_service.create_partner(
        name="Partner Hub",
        city="Campinas",
        state="SP",
        latitude=4.0,
        longitude=4.0,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner_hub.id,
        deadline_days=2,
        rule_type="FIXED",
        extra_config={"fixed_price": 250},
        max_km=100.0,
    )
    session.commit()

    lookup = {("Guarulhos", "SP"): (0.0, 0.0), ("Santos", "SP"): (10.0, 10.0)}
    distance_map = {
        ((0.0, 0.0), (4.0, 4.0)): 30.0,
        ((4.0, 4.0), (10.0, 10.0)): 60.0,
        ((0.0, 0.0), (10.0, 10.0)): 70.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))
    route = freight_service.simulate_multi_leg(
        origin_city="Guarulhos",
        origin_state="SP",
        destination_city="Santos",
        destination_state="SP",
        partner_ids=[partner_hub.id],
        segment_pickup_modes=["HUB"],
    )

    assert route["total_distance_km"] == 90.0
    assert route["total_deadline_days"] == 3
    assert route["route_segments"][0].pickup_mode == "HUB"
    assert route["route_segments"][0].segment_days == 3


def test_direct_pickup_mode_does_not_add_extra_day(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_direct = partner_service.create_partner(
        name="Partner Direct",
        city="Campinas",
        state="SP",
        latitude=4.0,
        longitude=4.0,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner_direct.id,
        deadline_days=2,
        rule_type="FIXED",
        extra_config={"fixed_price": 250},
        max_km=100.0,
    )
    session.commit()

    lookup = {("Guarulhos", "SP"): (0.0, 0.0), ("Santos", "SP"): (10.0, 10.0)}
    distance_map = {
        ((0.0, 0.0), (10.0, 10.0)): 70.0,
        ((0.0, 0.0), (4.0, 4.0)): 30.0,
        ((4.0, 4.0), (10.0, 10.0)): 60.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))
    route = freight_service.simulate_multi_leg(
        origin_city="Guarulhos",
        origin_state="SP",
        destination_city="Santos",
        destination_state="SP",
        partner_ids=[partner_direct.id],
        segment_pickup_modes=["DIRECT"],
    )

    assert route["total_distance_km"] == 70.0
    assert route["total_deadline_days"] == 2
    assert route["route_segments"][0].pickup_mode == "DIRECT"


def test_mixed_route_hub_hub_direct(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_a = partner_service.create_partner(
        name="Partner A",
        city="Campinas",
        state="SP",
        latitude=5.0,
        longitude=5.0,
        active=True,
    )
    partner_b = partner_service.create_partner(
        name="Partner B",
        city="Rio de Janeiro",
        state="RJ",
        latitude=15.0,
        longitude=15.0,
        active=True,
    )
    partner_c = partner_service.create_partner(
        name="Partner C",
        city="Vitoria",
        state="ES",
        latitude=25.0,
        longitude=25.0,
        active=True,
    )
    for partner_id, price, max_km in [
        (partner_a.id, 200, 120.0),
        (partner_b.id, 300, 220.0),
        (partner_c.id, 400, 220.0),
    ]:
        partner_service.add_rule(
            partner_id=partner_id,
            deadline_days=1,
            rule_type="FIXED",
            extra_config={"fixed_price": price},
            max_km=max_km,
        )
    session.commit()

    lookup = {("Guarulhos", "SP"): (0.0, 0.0), ("Salvador", "BA"): (35.0, 35.0)}
    distance_map = {
        ((0.0, 0.0), (5.0, 5.0)): 40.0,
        ((5.0, 5.0), (15.0, 15.0)): 60.0,
        ((15.0, 15.0), (25.0, 25.0)): 70.0,
        ((25.0, 25.0), (35.0, 35.0)): 80.0,
        ((15.0, 15.0), (35.0, 35.0)): 150.0,
        ((0.0, 0.0), (15.0, 15.0)): 90.0,
        ((15.0, 15.0), (15.0, 15.0)): 0.0,
        ((25.0, 25.0), (25.0, 25.0)): 0.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))
    route = freight_service.simulate_multi_leg(
        origin_city="Guarulhos",
        origin_state="SP",
        destination_city="Salvador",
        destination_state="BA",
        partner_ids=[partner_a.id, partner_b.id, partner_c.id],
        segment_pickup_modes=["HUB", "HUB", "DIRECT"],
    )

    assert [segment.pickup_mode for segment in route["route_segments"]] == ["HUB", "HUB", "DIRECT"]
    assert route["total_deadline_days"] == 5


def test_simulation_filters_to_valid_partners(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_a = partner_service.create_partner(
        name="Partner A",
        city="Campinas",
        state="SP",
        latitude=5.0,
        longitude=5.0,
        active=True,
    )
    partner_b = partner_service.create_partner(
        name="Partner B",
        city="Rio de Janeiro",
        state="RJ",
        latitude=15.0,
        longitude=15.0,
        active=True,
    )
    partner_c = partner_service.create_partner(
        name="Partner C",
        city="Manaus",
        state="AM",
        latitude=50.0,
        longitude=50.0,
        active=True,
    )
    for partner_id, price, max_km in [
        (partner_a.id, 200, 260.0),
        (partner_b.id, 300, 250.0),
        (partner_c.id, 400, 50.0),
    ]:
        partner_service.add_rule(
            partner_id=partner_id,
            deadline_days=2,
            rule_type="FIXED",
            extra_config={"fixed_price": price},
            max_km=max_km,
        )
    session.commit()

    lookup = {("Guarulhos", "SP"): (0.0, 0.0), ("Camamu", "BA"): (30.0, 30.0)}
    distance_map = {
        ((0.0, 0.0), (5.0, 5.0)): 100.0,
        ((0.0, 0.0), (15.0, 15.0)): 100.0,
        ((0.0, 0.0), (50.0, 50.0)): 1000.0,
        ((5.0, 5.0), (15.0, 15.0)): 140.0,
        ((15.0, 15.0), (30.0, 30.0)): 200.0,
        ((50.0, 50.0), (30.0, 30.0)): 500.0,
        ((0.0, 0.0), (30.0, 30.0)): 700.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))
    simulation = freight_service.simulate("Guarulhos", "SP", "Camamu", "BA")

    assert simulation["valid_partner_ids"] == [partner_a.id, partner_b.id]
    assert [result.partner_id for result in simulation["results"]] == [partner_a.id]


def test_multi_leg_route_raises_when_no_valid_route_exists(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_a = partner_service.create_partner(
        name="Partner A",
        city="Campinas",
        state="SP",
        latitude=5.0,
        longitude=5.0,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner_a.id,
        deadline_days=1,
        rule_type="FIXED",
        extra_config={"fixed_price": 200},
        max_km=80.0,
    )
    session.commit()

    lookup = {("Guarulhos", "SP"): (0.0, 0.0), ("Camamu", "BA"): (30.0, 30.0)}
    distance_map = {
        ((0.0, 0.0), (5.0, 5.0)): 100.0,
        ((5.0, 5.0), (30.0, 30.0)): 400.0,
        ((0.0, 0.0), (30.0, 30.0)): 600.0,
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", _distance_fn(distance_map))
    monkeypatch.setattr(route_builder_module, "calculate_distance_km", _distance_fn(distance_map))

    freight_service = FreightService(PartnerRepository(session))

    with pytest.raises(ValueError, match="No valid route found"):
        freight_service.simulate_multi_leg(
            origin_city="Guarulhos",
            origin_state="SP",
            destination_city="Camamu",
            destination_state="BA",
        )


def test_multi_leg_route_raises_readable_error_for_partner_without_coordinates(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner = partner_service.create_partner(
        name="Partner Sem Coordenadas",
        city="Campinas",
        state="SP",
        latitude=-22.9099,
        longitude=-47.0626,
        active=True,
    )
    partner.latitude = None
    partner.longitude = None
    partner_service.add_rule(
        partner_id=partner.id,
        deadline_days=1,
        rule_type="FIXED",
        extra_config={"fixed_price": 200},
        max_km=999999,
    )
    session.commit()

    lookup = {
        ("Sao Paulo", "SP"): (-23.5505, -46.6333),
        ("Salvador", "BA"): (-12.9714, -38.5014),
    }
    monkeypatch.setattr(freight_service_module, "get_coordinates", lambda city, state: lookup[(city, state)])

    freight_service = FreightService(PartnerRepository(session))

    with pytest.raises(ValueError) as exc_info:
        freight_service.simulate_multi_leg(
            origin_city="Sao Paulo",
            origin_state="SP",
            destination_city="Salvador",
            destination_state="BA",
            partner_ids=[partner.id],
        )

    assert (
        str(exc_info.value)
        == "Os seguintes parceiros nao possuem latitude/longitude e nao podem "
        "ser usados na rota: Partner Sem Coordenadas. "
        "Edite o parceiro e salve novamente para geocodificar automaticamente."
    )
