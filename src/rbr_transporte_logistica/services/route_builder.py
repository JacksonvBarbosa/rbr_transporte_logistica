from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from collections.abc import Callable, Iterable

from rbr_transporte_logistica.core.models import Partner
from rbr_transporte_logistica.dto.simulation import RoutePoint
from rbr_transporte_logistica.utils.geo_utils import calculate_distance_km

RouteScorer = Callable[[list[RoutePoint]], tuple[float, int]]
VALID_PICKUP_MODES = {"DIRECT", "HUB"}


@dataclass(slots=True)
class PartnerReach:
    partner_id: int
    partner_name: str
    reachable_distance_km: float
    remaining_distance_km: float
    max_km: float
    partner_point: RoutePoint
    max_reach_point: RoutePoint
    reachable_region: str


class RouteBuildError(ValueError):
    def __init__(
        self,
        *,
        message: str,
        last_reachable_point: RoutePoint,
        max_reachable_distance_km: float,
        closest_partners: list[PartnerReach],
    ) -> None:
        super().__init__(message)
        self.message = message
        self.last_reachable_point = last_reachable_point
        self.max_reachable_distance_km = max_reachable_distance_km
        self.closest_partners = closest_partners

    def to_payload(self) -> dict[str, object]:
        return {
            "error": True,
            "message": self.message,
            "last_reachable_point": self.last_reachable_point,
            "max_reachable_distance_km": round(self.max_reachable_distance_km, 2),
            "closest_partners": [
                {
                    "partner_id": reach.partner_id,
                    "partner_name": reach.partner_name,
                    "reachable_distance_km": round(reach.reachable_distance_km, 2),
                    "remaining_distance_km": round(reach.remaining_distance_km, 2),
                    "max_km": round(reach.max_km, 2),
                    "reachable_region": reach.reachable_region,
                    "partner_point": reach.partner_point,
                    "max_reach_point": reach.max_reach_point,
                }
                for reach in self.closest_partners
            ],
        }


def build_route(
    origin: RoutePoint,
    destination: RoutePoint,
    partners: Iterable[Partner],
    scorer: RouteScorer | None = None,
) -> list[RoutePoint]:
    candidates = build_candidate_routes(origin, destination, partners)
    if not candidates:
        raise build_route_error(origin, destination, partners)
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
    routes: list[list[RoutePoint]] = []
    seen_route_ids: set[tuple[int, ...]] = set()

    def _register_route(current_route: list[RoutePoint]) -> None:
        route_ids = tuple(point.partner_id for point in current_route)
        if route_ids in seen_route_ids:
            return
        seen_route_ids.add(route_ids)
        routes.append([origin, *current_route, destination])

    def _dfs(current_point: RoutePoint, visited: set[int], current_route: list[RoutePoint], current_partner: Partner) -> None:
        if _distance_between_points(current_point, destination) <= _partner_max_distance(current_partner):
            _register_route(current_route)

        next_partners = filter_partners_for_progression(current_point, destination, partner_candidates)
        for partner in next_partners:
            if partner.id in visited:
                continue
            next_point = _partner_to_point(partner)
            if next_point.latitude == current_point.latitude and next_point.longitude == current_point.longitude:
                continue
            _dfs(next_point, {*visited, partner.id}, [*current_route, next_point], partner)

    for partner in partner_candidates:
        partner_point = _partner_to_point(partner)
        if _distance_between_points(origin, partner_point) <= _partner_max_distance(partner):
            _dfs(partner_point, {partner.id}, [partner_point], partner)
    return routes


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


def filter_partners_for_segment(
    current_point: RoutePoint,
    target_point: RoutePoint,
    partners: Iterable[Partner],
) -> list[Partner]:
    valid_partners: list[Partner] = []
    for partner in partners:
        if partner.latitude is None or partner.longitude is None:
            continue
        segment_distance = _distance_between_points(current_point, target_point)
        if segment_distance <= _partner_max_distance(partner):
            valid_partners.append(partner)
    return valid_partners


def filter_partners_for_progression(
    current_point: RoutePoint,
    destination: RoutePoint,
    partners: Iterable[Partner],
) -> list[Partner]:
    valid_partners: list[Partner] = []
    for partner in partners:
        if partner.latitude is None or partner.longitude is None:
            continue
        partner_point = _partner_to_point(partner)
        if partner_point.latitude == current_point.latitude and partner_point.longitude == current_point.longitude:
            continue
        if _distance_between_points(current_point, partner_point) <= _partner_max_distance(partner):
            if _distance_between_points(partner_point, destination) < _distance_between_points(current_point, destination):
                valid_partners.append(partner)
    return valid_partners


def analyze_partner_reach(
    current_point: RoutePoint,
    destination: RoutePoint,
    partners: Iterable[Partner],
) -> list[PartnerReach]:
    reaches: list[PartnerReach] = []
    remaining_distance = _distance_between_points(current_point, destination)
    for partner in partners:
        if partner.latitude is None or partner.longitude is None:
            continue
        max_km = _partner_max_distance(partner)
        if max_km <= 0:
            continue
        partner_point = _partner_to_point(partner)
        distance_to_partner = _distance_between_points(current_point, partner_point)
        if distance_to_partner > max_km:
            continue
        reachable_distance = min(max_km, remaining_distance)
        max_reach_point = project_reach_point(current_point, destination, reachable_distance)
        remaining_after_reach = max(remaining_distance - reachable_distance, 0.0)
        reaches.append(
            PartnerReach(
                partner_id=partner.id,
                partner_name=partner.name,
                reachable_distance_km=reachable_distance,
                remaining_distance_km=remaining_after_reach,
                max_km=max_km,
                partner_point=partner_point,
                max_reach_point=max_reach_point,
                reachable_region=f"{max_reach_point.city}/{max_reach_point.state}",
            )
        )
    reaches.sort(
        key=lambda item: (
            item.remaining_distance_km,
            -item.reachable_distance_km,
            item.partner_name,
        )
    )
    return reaches


def build_route_error(
    current_point: RoutePoint,
    destination: RoutePoint,
    partners: Iterable[Partner],
) -> RouteBuildError:
    reaches = analyze_partner_reach(current_point, destination, partners)
    if not reaches:
        message = "Nenhum parceiro disponível para cobrir esse segmento"
        return RouteBuildError(
            message=message,
            last_reachable_point=current_point,
            max_reachable_distance_km=0.0,
            closest_partners=[],
        )

    best = reaches[0]
    location = f"{current_point.city}/{current_point.state}"
    message = (
        f"Nenhum parceiro disponível pertence a {location}. "
        f"Distância máxima de cobertura: {best.reachable_distance_km:.2f} km"
    )
    return RouteBuildError(
        message=message,
        last_reachable_point=best.max_reach_point,
        max_reachable_distance_km=best.reachable_distance_km,
        closest_partners=reaches[:3],
    )


def project_reach_point(start: RoutePoint, destination: RoutePoint, distance_km: float) -> RoutePoint:
    total_distance = _distance_between_points(start, destination)
    if total_distance <= 0:
        return start
    ratio = min(max(distance_km / total_distance, 0.0), 1.0)
    latitude = start.latitude + (destination.latitude - start.latitude) * ratio
    longitude = start.longitude + (destination.longitude - start.longitude) * ratio
    if ratio >= 0.999:
        city = destination.city
        state = destination.state
        label = f"Alcance maximo em {destination.city}/{destination.state}"
    elif ratio <= 0.001:
        city = start.city
        state = start.state
        label = f"Alcance maximo em {start.city}/{start.state}"
    else:
        city = f"Próximo de {destination.city}"
        state = destination.state
        label = f"Alcance parcial rumo a {destination.city}/{destination.state}"
    return RoutePoint(
        label=label,
        city=city,
        state=state,
        latitude=latitude,
        longitude=longitude,
        point_type="projected",
    )


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
