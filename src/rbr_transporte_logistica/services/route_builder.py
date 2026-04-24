from __future__ import annotations

from typing import Iterable

from rbr_transporte_logistica.core.models import Partner
from rbr_transporte_logistica.dto.simulation import RoutePoint
from rbr_transporte_logistica.utils.geo_utils import calculate_distance_km


def build_route(origin: RoutePoint, destination: RoutePoint, partners: Iterable[Partner]) -> list[RoutePoint]:
    candidates = [
        partner
        for partner in partners
        if partner.latitude is not None
        and partner.longitude is not None
        and _partner_max_distance(partner) > 0
    ]
    ordered_path = _search_route(origin, destination, candidates, visited_partner_ids=set())
    if not ordered_path:
        raise ValueError("No valid route found")

    route = [origin]
    route.extend(_partner_to_point(partner) for partner in ordered_path)
    route.append(destination)
    return route


def _search_route(
    current: RoutePoint,
    destination: RoutePoint,
    partners: list[Partner],
    *,
    visited_partner_ids: set[int],
) -> list[Partner] | None:
    reachable_candidates = []
    for partner in partners:
        if partner.id in visited_partner_ids:
            continue
        max_distance = _partner_max_distance(partner)
        if max_distance <= 0:
            continue
        distance_to_partner = calculate_distance_km(
            (current.latitude, current.longitude),
            (float(partner.latitude), float(partner.longitude)),
        )
        if distance_to_partner > max_distance:
            continue
        distance_to_destination = calculate_distance_km(
            (float(partner.latitude), float(partner.longitude)),
            (destination.latitude, destination.longitude),
        )
        reachable_candidates.append((partner, max_distance, distance_to_partner, distance_to_destination))

    reachable_candidates.sort(
        key=lambda item: (item[3], -item[1], item[2], item[0].name)
    )

    for partner, max_distance, _distance_to_partner, distance_to_destination in reachable_candidates:
        if distance_to_destination <= max_distance:
            return [partner]

        next_current = _partner_to_point(partner)
        nested_path = _search_route(
            next_current,
            destination,
            partners,
            visited_partner_ids=visited_partner_ids | {partner.id},
        )
        if nested_path:
            return [partner, *nested_path]

    return None


def _partner_max_distance(partner: Partner) -> float:
    return max((float(rule.max_km) for rule in partner.freight_rules if rule.max_km is not None), default=0.0)


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
