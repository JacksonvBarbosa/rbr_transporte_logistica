from __future__ import annotations

from typing import Any

from rbr_transporte_logistica.services.freight_service import FreightService
from rbr_transporte_logistica.utils.export_excel import build_quote_excel
from rbr_transporte_logistica.utils.export_pdf import build_quote_pdf


class QuoteService:
    def build_quote(
        self,
        *,
        origin: str,
        destination: str,
        direct_distance_km: float,
        segments: list,
        tax_rate: float,
        margin_rate: float,
        additional_fee: float,
    ) -> dict[str, Any]:
        summary = FreightService.build_route_summary(
            origin=origin,
            destination=destination,
            direct_distance_km=direct_distance_km,
            segments=segments,
            tax_rate=tax_rate,
            margin_rate=margin_rate,
            additional_fee=additional_fee,
        )
        return {"summary": summary, "items": list(segments)}

    def export_excel(self, quote_data: dict) -> bytes:
        return build_quote_excel(quote_data["summary"], quote_data["items"])

    def export_pdf(self, quote_data: dict) -> bytes:
        return build_quote_pdf(quote_data["summary"], quote_data["items"])
