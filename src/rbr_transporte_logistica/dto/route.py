from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RouteSegment:
    partner_id: int
    partner_name: str
    origin: tuple[float, float]
    destination: tuple[float, float]
    distance_km: float
    pickup_mode: str
    segment_days: int
    segment_cost: float
    rule_type: str | None = None
