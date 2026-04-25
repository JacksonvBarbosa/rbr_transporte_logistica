from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from rbr_transporte_logistica.core.database import Base, create_db_engine
from rbr_transporte_logistica.repositories.freight_repository import FreightRepository
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.services import partner_service as partner_service_module
from rbr_transporte_logistica.services.partner_service import PartnerService


def make_session():
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_create_partner_with_automatic_coordinates(monkeypatch):
    session = make_session()
    service = PartnerService(PartnerRepository(session), FreightRepository(session))
    monkeypatch.setattr(
        partner_service_module, "get_coordinates", lambda city, state: (-23.5505, -46.6333)
    )

    partner = service.create_partner(
        name="Transportadora Azul",
        city="Sao Paulo",
        state="SP",
        active=True,
    )

    assert partner.id is not None
    assert partner.name == "Transportadora Azul"
    assert partner.state == "SP"
    assert partner.latitude == -23.5505
    assert partner.longitude == -46.6333


def test_update_partner_refreshes_coordinates(monkeypatch):
    session = make_session()
    service = PartnerService(PartnerRepository(session), FreightRepository(session))
    coordinates = iter([(-23.5505, -46.6333), (-22.9068, -43.1729)])
    monkeypatch.setattr(partner_service_module, "get_coordinates", lambda city, state: next(coordinates))

    partner = service.create_partner(
        name="Transportadora Azul",
        city="Sao Paulo",
        state="SP",
        active=True,
    )
    updated = service.update_partner(partner.id, city="Rio de Janeiro", state="RJ")

    assert updated.city == "Rio de Janeiro"
    assert updated.state == "RJ"
    assert updated.latitude == -22.9068
    assert updated.longitude == -43.1729


def test_add_rule_auto_calculates_deadline_from_max_km(monkeypatch):
    session = make_session()
    service = PartnerService(PartnerRepository(session), FreightRepository(session))
    monkeypatch.setattr(
        partner_service_module, "get_coordinates", lambda city, state: (-23.5505, -46.6333)
    )
    partner = service.create_partner(
        name="Transportadora Verde",
        city="Sao Paulo",
        state="SP",
        active=True,
    )

    rule = service.add_rule(
        partner_id=partner.id,
        deadline_days=1,
        rule_type="FIXED",
        max_km=750,
        extra_config={"fixed_price": 320},
    )

    assert rule.max_km == 750
    assert rule.deadline_days == 4


def test_delete_partner_removes_partner_and_linked_rules(monkeypatch):
    session = make_session()
    service = PartnerService(PartnerRepository(session), FreightRepository(session))
    monkeypatch.setattr(
        partner_service_module, "get_coordinates", lambda city, state: (-23.5505, -46.6333)
    )

    partner = service.create_partner(
        name="Transportadora Verde",
        city="Sao Paulo",
        state="SP",
        active=True,
    )
    rule = service.add_rule(
        partner_id=partner.id,
        deadline_days=2,
        rule_type="FIXED",
        max_km=999999,
        extra_config={"fixed_price": 320},
    )
    session.commit()

    service.delete_partner(partner.id)
    session.commit()

    assert service.list_partners() == []
    assert FreightRepository(session).get_by_id(rule.id) is None


def test_delete_partner_raises_for_unknown_partner():
    session = make_session()
    service = PartnerService(PartnerRepository(session), FreightRepository(session))

    with pytest.raises(ValueError, match="Parceiro nao encontrado."):
        service.delete_partner(999)
