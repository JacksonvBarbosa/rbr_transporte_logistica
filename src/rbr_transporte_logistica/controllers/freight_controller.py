from __future__ import annotations

from io import BytesIO

from rbr_transporte_logistica.services.etl_service import ETLService
from rbr_transporte_logistica.services.freight_service import FreightService


class FreightController:
    def __init__(self, freight_service: FreightService, etl_service: ETLService) -> None:
        self.freight_service = freight_service
        self.etl_service = etl_service

    def simulate(
        self, origin_city: str, origin_state: str, destination_city: str, destination_state: str
    ) -> dict:
        return self.freight_service.simulate(
            origin_city, origin_state, destination_city, destination_state
        )

    def simulate_multi_leg(
        self,
        origin_city: str,
        origin_state: str,
        destination_city: str,
        destination_state: str,
        partner_ids: list[int],
    ) -> dict:
        return self.freight_service.simulate_multi_leg(
            origin_city, origin_state, destination_city, destination_state, partner_ids
        )

    def ingest_file(self, filename: str, file_bytes: bytes):
        return self.etl_service.ingest(filename, BytesIO(file_bytes))
