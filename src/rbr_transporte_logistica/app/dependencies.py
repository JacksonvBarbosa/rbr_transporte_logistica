from __future__ import annotations

from sqlalchemy.orm import Session

from rbr_transporte_logistica.controllers.freight_controller import FreightController
from rbr_transporte_logistica.controllers.partner_controller import PartnerController
from rbr_transporte_logistica.controllers.quote_controller import QuoteController
from rbr_transporte_logistica.repositories.freight_repository import FreightRepository
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.services.etl_service import ETLService
from rbr_transporte_logistica.services.freight_service import FreightService
from rbr_transporte_logistica.services.partner_service import PartnerService
from rbr_transporte_logistica.services.quote_service import QuoteService


def build_partner_controller(session: Session) -> PartnerController:
    partner_repository = PartnerRepository(session)
    freight_repository = FreightRepository(session)
    partner_service = PartnerService(partner_repository, freight_repository)
    return PartnerController(partner_service)


def build_freight_controller(session: Session) -> FreightController:
    partner_repository = PartnerRepository(session)
    freight_repository = FreightRepository(session)
    partner_service = PartnerService(partner_repository, freight_repository)
    freight_service = FreightService(partner_repository)
    etl_service = ETLService(partner_service)
    return FreightController(freight_service, etl_service)


def build_quote_controller() -> QuoteController:
    return QuoteController(QuoteService())
