from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class SimulationResult:
    partner_id: int
    partner_name: str
    city: str
    state: str
    price: float
    deadline_days: int
    rule_type: str
    latitude: float | None
    longitude: float | None
    distance_km: float
    segment_index: int | None = None
    origin_point: "RoutePoint | None" = None
    destination_point: "RoutePoint | None" = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class RoutePoint:
    label: str
    city: str
    state: str
    latitude: float
    longitude: float
    partner_id: int | None = None
    point_type: str = "waypoint"


@dataclass(slots=True)
class SegmentResult:
    segment_order: int
    partner_id: int
    partner_name: str
    origin_label: str
    destination_label: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    distance_km: float
    price: float
    deadline_days: int
    rule_type: str


@dataclass(slots=True)
class RouteSummary:
    origin: str
    destination: str
    direct_distance_km: float
    route_distance_km: float
    subtotal: float
    taxes: float
    margin: float
    additional_fees: float
    total: float
    total_deadline_days: int
