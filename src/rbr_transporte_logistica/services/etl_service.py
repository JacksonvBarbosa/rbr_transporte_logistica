from __future__ import annotations

from typing import BinaryIO

from rbr_transporte_logistica.core.models import Partner
from rbr_transporte_logistica.dto.etl import ETLResult
from rbr_transporte_logistica.services.partner_service import PartnerService
from rbr_transporte_logistica.utils.file_parser import ParsedFileRow, parse_uploaded_file


class ETLService:
    def __init__(self, partner_service: PartnerService) -> None:
        self.partner_service = partner_service

    def ingest(self, filename: str, file_obj: BinaryIO) -> ETLResult:
        rows = parse_uploaded_file(filename, file_obj)
        partners_created = 0
        rules_created = 0

        for row in rows:
            partner, created = self._get_or_create_partner(row)
            if created:
                partners_created += 1
            rules_created += 1
            self.partner_service.add_rule(
                partner_id=partner.id,
                base_price=row.price,
                price_per_km=0,
                max_km=row.km,
                rule_type="LINEAR",
            )

        return ETLResult(
            rows_processed=len(rows),
            partners_created=partners_created,
            rules_created=rules_created,
        )

    def _get_or_create_partner(self, row: ParsedFileRow) -> tuple[Partner, bool]:
        existing = next(
            (
                partner
                for partner in self.partner_service.list_partners()
                if partner.name == row.partner
            ),
            None,
        )
        if existing:
            return existing, False

        return (
            self.partner_service.create_partner(
                name=row.partner,
                city=row.city,
                state=row.state,
                latitude=None,
                longitude=None,
                active=True,
            ),
            True,
        )
