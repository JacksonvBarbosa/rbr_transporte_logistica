from __future__ import annotations

from io import BytesIO

from rbr_transporte_logistica.services.etl_service import ETLService
from rbr_transporte_logistica.services.freight_service import FreightService


class FreightController:
    def __init__(self, freight_service: FreightService, etl_service: ETLService) -> None:
        self.freight_service = freight_service
        self.etl_service = etl_service

    def simulate(
        self,
        origin_city: str,
        origin_state: str,
        destination_city: str,
        destination_state: str,
        optimization_mode: str = "cost",
        origin_coords: tuple[float, float] | None = None,
        destination_coords: tuple[float, float] | None = None,
    ) -> dict:
        return self.freight_service.simulate(
            origin_city,
            origin_state,
            destination_city,
            destination_state,
            optimization_mode,
            origin_coords=origin_coords,
            destination_coords=destination_coords,
        )

    def simulate_multi_leg(
        self,
        origin_city: str,
        origin_state: str,
        destination_city: str,
        destination_state: str,
        partner_ids: list[int] | None = None,
        segment_pickup_modes: list[str] | None = None,
        optimization_mode: str = "cost",
        origin_coords: tuple[float, float] | None = None,
        destination_coords: tuple[float, float] | None = None,
    ) -> dict:
        return self.freight_service.simulate_multi_leg(
            origin_city,
            origin_state,
            destination_city,
            destination_state,
            partner_ids,
            segment_pickup_modes,
            optimization_mode,
            origin_coords=origin_coords,
            destination_coords=destination_coords,
        )

    def ingest_file(self, filename: str, file_bytes: bytes):
        return self.etl_service.ingest(filename, BytesIO(file_bytes))
