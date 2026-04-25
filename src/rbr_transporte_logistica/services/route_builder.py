from __future__ import annotations

from math import isfinite
from time import monotonic
from collections.abc import Callable, Iterable

from rbr_transporte_logistica.core.models import Partner
from rbr_transporte_logistica.dto.simulation import RoutePoint
from rbr_transporte_logistica.utils.geo_utils import calculate_distance_km

RouteScorer = Callable[[list[RoutePoint]], tuple[float, int]]
VALID_PICKUP_MODES = {"DIRECT", "HUB"}
MAX_STEPS = 10
MAX_ROUTE_SECONDS = 5.0


def build_route(
    origin: RoutePoint,
    destination: RoutePoint,
    partners: Iterable[Partner],
    scorer: RouteScorer | None = None,
) -> list[RoutePoint]:
    candidates = build_candidate_routes(origin, destination, partners)
    if not candidates:
        raise ValueError("No valid route found")
    if scorer is None:
        scorer = _default_scorer
    return min(candidates, key=scorer)


def build_candidate_routes(
    origin: RoutePoint,
    destination: RoutePoint,
    partners: Iterable[Partner],
) -> list[list[RoutePoint]]:
    partner_candidates = [
        partner
        for partner in partners
        if partner.latitude is not None
        and partner.longitude is not None
        and _partner_max_distance(partner) > 0
    ]

    routes: list[list[Partner]] = []
    for partner in partner_candidates:
        try:
            routes.append(
                _build_greedy_sequence(
                    origin=origin,
                    destination=destination,
                    partners=partner_candidates,
                    starting_partner=partner,
                )
            )
        except ValueError as exc:
            if str(exc).strip() != "No valid route found":
                raise
            continue

    unique_routes: list[list[RoutePoint]] = []
    seen_route_ids: set[tuple[int, ...]] = set()
    for route in routes:
        route_ids = tuple(partner.id for partner in route)
        if route_ids in seen_route_ids:
            continue
        seen_route_ids.add(route_ids)
        unique_routes.append([origin, *[_partner_to_point(partner) for partner in route], destination])
    return unique_routes


def filter_valid_partners(
    origin: RoutePoint,
    destination: RoutePoint,
    partners: Iterable[Partner],
) -> list[Partner]:
    partner_list = list(partners)
    partner_lookup = {partner.id: partner for partner in partner_list}
    valid_partner_ids = {
        point.partner_id
        for route in build_candidate_routes(origin, destination, partner_lookup.values())
        for point in route
        if point.partner_id is not None
    }
    return [partner for partner in partner_list if partner.id in valid_partner_ids]


def estimate_delivery_days(partner: Partner, start: RoutePoint, end: RoutePoint) -> int:
    max_distance = _partner_max_distance(partner)
    if max_distance <= 0:
        raise ValueError(f"Parceiro {partner.name} nao possui cobertura valida.")
    effective_distance = calculate_effective_distance(partner, start, end, pickup_mode="DIRECT")
    base_deadline = _partner_deadline_days(partner)
    estimated_days = -(-effective_distance // max_distance)
    return max(int(estimated_days) * base_deadline, 1)


def calculate_effective_distance(
    partner: Partner,
    start: RoutePoint,
    end: RoutePoint,
    pickup_mode: str,
) -> float:
    end_distance = _distance_between_points(start, end)
    if normalize_pickup_mode(pickup_mode) == "DIRECT":
        return end_distance

    base_point = _partner_to_point(partner)
    to_base = _distance_between_points(start, base_point)
    from_base = _distance_between_points(base_point, end)
    return to_base + from_base


def can_partner_deliver(partner: Partner, start: RoutePoint, end: RoutePoint, pickup_mode: str) -> bool:
    return calculate_effective_distance(partner, start, end, pickup_mode) <= _partner_max_distance(partner)


def build_physical_path(
    route_points: list[RoutePoint],
    partner_lookup: dict[int, Partner],
    segment_pickup_modes: list[str] | None = None,
) -> list[RoutePoint]:
    if len(route_points) < 2:
        return route_points

    resolved_modes = resolve_segment_pickup_modes(route_points, segment_pickup_modes)
    path = [route_points[0]]
    for index, handler_point in enumerate(route_points[1:-1], start=1):
        partner = partner_lookup[handler_point.partner_id]
        pickup_mode = resolved_modes[index - 1]
        end = route_points[index + 1]
        if pickup_mode == "HUB":
            hub_point = _partner_to_point(partner)
            if path[-1].label != hub_point.label or path[-1].partner_id != hub_point.partner_id:
                path.append(hub_point)
        if path[-1] != end:
            path.append(end)
    return path


def _build_greedy_sequence(
    *,
    origin: RoutePoint,
    destination: RoutePoint,
    partners: list[Partner],
    starting_partner: Partner,
) -> list[Partner]:
    route: list[Partner] = []
    visited: set[int] = set()
    current_point = origin
    current_partner = starting_partner
    started_at = monotonic()

    for _step in range(MAX_STEPS):
        if monotonic() - started_at > MAX_ROUTE_SECONDS:
            raise ValueError("Route calculation exceeded safe limits")
        if current_partner.id in visited:
            raise ValueError("No valid route found")

        print("Current point:", current_point)
        print("Available partners:", len(partners))
        print("Visited:", visited)

        visited.add(current_partner.id)
        route.append(current_partner)
        max_distance = _partner_max_distance(current_partner)
        if max_distance <= 0:
            raise ValueError("No valid route found")

        remaining_distance = _distance_between_points(current_point, destination)
        if remaining_distance <= max_distance:
            return route

        next_candidates: list[tuple[float, float, Partner]] = []
        for partner in partners:
            if partner.id in visited:
                continue
            next_point = _partner_to_point(partner)
            if not can_partner_deliver(current_partner, current_point, next_point, pickup_mode="HUB"):
                continue
            distance_to_destination = _distance_between_points(next_point, destination)
            next_candidates.append((distance_to_destination, -_partner_max_distance(partner), partner))

        if not next_candidates:
            raise ValueError("No valid route found")

        current_partner = min(next_candidates, key=lambda item: (item[0], item[1], item[2].id))[2]
        current_point = _partner_to_point(current_partner)

    raise ValueError("Route calculation exceeded safe limits")


def _partner_max_distance(partner: Partner) -> float:
    return max((float(rule.max_km) for rule in partner.freight_rules if rule.max_km is not None), default=0.0)


def _partner_deadline_days(partner: Partner) -> int:
    return min((int(rule.deadline_days) for rule in partner.freight_rules if rule.deadline_days), default=1)


def validate_distance_km(distance: float, *, context: str) -> float:
    if distance is None or not isinstance(distance, (int, float)) or not isfinite(float(distance)):
        raise ValueError(f"Distancia invalida calculada para {context}.")
    return float(distance)


def _distance_between_points(start: RoutePoint, end: RoutePoint) -> float:
    if start.latitude == end.latitude and start.longitude == end.longitude:
        return 0.0
    return validate_distance_km(
        calculate_distance_km((start.latitude, start.longitude), (end.latitude, end.longitude)),
        context=f"{start.label} -> {end.label}",
    )


def normalize_pickup_mode(value: str | None) -> str:
    normalized = str(value or "DIRECT").strip().upper()
    if normalized not in VALID_PICKUP_MODES:
        raise ValueError("Pickup mode invalido. Use DIRECT ou HUB.")
    return normalized


def default_segment_pickup_modes(partner_count: int) -> list[str]:
    if partner_count <= 0:
        return []
    return ["HUB" if index < partner_count - 1 else "DIRECT" for index in range(partner_count)]


def resolve_segment_pickup_modes(
    route_points: list[RoutePoint],
    segment_pickup_modes: list[str] | None = None,
) -> list[str]:
    partner_count = max(len(route_points) - 2, 0)
    if segment_pickup_modes is None:
        return default_segment_pickup_modes(partner_count)
    if len(segment_pickup_modes) != partner_count:
        raise ValueError("Quantidade de pickup modes nao corresponde aos segmentos da rota.")
    return [normalize_pickup_mode(mode) for mode in segment_pickup_modes]


def _partner_to_point(partner: Partner) -> RoutePoint:
    return RoutePoint(
        label=partner.name,
        city=partner.city,
        state=partner.state,
        latitude=float(partner.latitude),
        longitude=float(partner.longitude),
        partner_id=partner.id,
        point_type="partner",
    )


def _default_scorer(route_points: list[RoutePoint]) -> tuple[float, int]:
    return (float(len(route_points)), len(route_points))
