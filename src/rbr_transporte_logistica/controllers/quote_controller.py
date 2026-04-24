from __future__ import annotations

from rbr_transporte_logistica.services.quote_service import QuoteService


class QuoteController:
    def __init__(self, service: QuoteService) -> None:
        self.service = service

    def create_quote(
        self,
        *,
        origin: str,
        destination: str,
        direct_distance_km: float,
        segments,
        tax_rate: float,
        margin_rate: float,
        additional_fee: float,
    ):
        return self.service.build_quote(
            origin=origin,
            destination=destination,
            direct_distance_km=direct_distance_km,
            segments=segments,
            tax_rate=tax_rate,
            margin_rate=margin_rate,
            additional_fee=additional_fee,
        )

    def export_excel(self, quote_data: dict) -> bytes:
        return self.service.export_excel(quote_data)

    def export_pdf(self, quote_data: dict) -> bytes:
        return self.service.export_pdf(quote_data)
