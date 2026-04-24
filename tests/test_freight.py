from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from rbr_transporte_logistica.core.database import Base, create_db_engine
from rbr_transporte_logistica.repositories.freight_repository import FreightRepository
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.services import freight_service as freight_service_module
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
    monkeypatch.setattr(
        freight_service_module, "get_coordinates", lambda city, state: (-23.5505, -46.6333)
    )
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", lambda origin, destination: 100.0)

    result = freight_service.simulate("Sao Paulo", "SP", "Campinas", "SP")

    assert len(result["results"]) == 1
    assert result["best_price"].price == 350.0
    assert result["distance_km"] == 100.0


def test_fixed_rule_application(monkeypatch):
    session = setup_partner_with_rule("FIXED", {"fixed_price": 420})
    freight_service = FreightService(PartnerRepository(session))
    monkeypatch.setattr(
        freight_service_module, "get_coordinates", lambda city, state: (-23.5505, -46.6333)
    )
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", lambda origin, destination: 250.0)

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
    monkeypatch.setattr(
        freight_service_module, "get_coordinates", lambda city, state: (-23.5505, -46.6333)
    )
    monkeypatch.setattr(freight_service_module, "calculate_distance_km", lambda origin, destination: 280.0)

    result = freight_service.simulate("Sao Paulo", "SP", "Campinas", "SP")

    assert result["best_price"].price == 550.0


def test_multi_leg_route_calculation(monkeypatch):
    session = make_session()
    partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
    partner_a = partner_service.create_partner(
        name="Partner A",
        city="Campinas",
        state="SP",
        latitude=-22.9099,
        longitude=-47.0626,
        active=True,
    )
    partner_b = partner_service.create_partner(
        name="Partner B",
        city="Belo Horizonte",
        state="MG",
        latitude=-19.9167,
        longitude=-43.9345,
        active=True,
    )
    partner_service.add_rule(
        partner_id=partner_a.id,
        deadline_days=1,
        rule_type="FIXED",
        extra_config={"fixed_price": 200},
        max_km=999999,
    )
    partner_service.add_rule(
        partner_id=partner_b.id,
        deadline_days=2,
        rule_type="FIXED",
        extra_config={"fixed_price": 300},
        max_km=999999,
    )
    session.commit()

    lookup = {
        ("Sao Paulo", "SP"): (-23.5505, -46.6333),
        ("Salvador", "BA"): (-12.9714, -38.5014),
    }
    distance_values = iter([100.0, 200.0, 300.0, 900.0])
    monkeypatch.setattr(
        freight_service_module,
        "get_coordinates",
        lambda city, state: lookup[(city, state)],
    )
    monkeypatch.setattr(
        freight_service_module,
        "calculate_distance_km",
        lambda origin, destination: next(distance_values),
    )

    freight_service = FreightService(PartnerRepository(session))
    route = freight_service.simulate_multi_leg(
        origin_city="Sao Paulo",
        origin_state="SP",
        destination_city="Salvador",
        destination_state="BA",
        partner_ids=[partner_a.id, partner_b.id],
    )

    assert len(route["segments"]) == 3
    assert [segment.price for segment in route["segments"]] == [200.0, 300.0, 300.0]
    assert route["segments"][-1].destination_label == "Destino"
    assert route["direct_distance_km"] == 900.0


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
    monkeypatch.setattr(
        freight_service_module,
        "get_coordinates",
        lambda city, state: lookup[(city, state)],
    )

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
