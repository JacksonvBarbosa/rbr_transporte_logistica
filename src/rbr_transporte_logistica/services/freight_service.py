from __future__ import annotations

from decimal import Decimal
from math import ceil
from typing import Any

from rbr_transporte_logistica.core.models import FreightRule, Partner
from rbr_transporte_logistica.dto.route import RouteSegment
from rbr_transporte_logistica.dto.simulation import (
    RoutePoint,
    RouteSummary,
    SegmentResult,
    SimulationResult,
)
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.services.route_builder import (
    build_candidate_routes,
    build_physical_path,
    build_route,
    calculate_effective_distance,
    filter_valid_partners,
    normalize_pickup_mode,
    resolve_segment_pickup_modes,
)
from rbr_transporte_logistica.utils.geo_utils import calculate_distance_km, get_coordinates


class FreightService:
    def __init__(self, partner_repository: PartnerRepository) -> None:
        self.partner_repository = partner_repository

    def simulate(
        self, origin_city: str, origin_state: str, destination_city: str, destination_state: str
    ) -> dict[str, Any]:
        origin = self._build_point("Origem", origin_city, origin_state)
        destination = self._build_point("Destino", destination_city, destination_state)
        km = calculate_distance_km(
            (origin.latitude, origin.longitude), (destination.latitude, destination.longitude)
        )
        if km <= 0:
            raise ValueError("Distancia precisa ser maior que zero.")

        partners = [
            partner
            for partner in self.partner_repository.list_all(active_only=True)
            if partner.latitude is not None and partner.longitude is not None
        ]
        valid_partners = filter_valid_partners(origin, destination, partners)
        candidate_routes = build_candidate_routes(origin, destination, valid_partners)
        best_route = (
            self._find_best_route_plan(origin, destination, valid_partners, candidate_routes)
            if candidate_routes
            else None
        )
        results: list[SimulationResult] = []
        best_by_first_partner: dict[int, dict[str, Any]] = {}
        for route in candidate_routes:
            plan = self._compile_route_plan(route, valid_partners, manual_override=False)
            first_segment = plan["segments"][0]
            first_partner = plan["selected_partners"][0]
            current_best = best_by_first_partner.get(first_partner.id)
            candidate_key = (plan["total_cost"], plan["total_deadline_days"], first_partner.name)
            current_key = None
            if current_best:
                current_key = (
                    current_best["total_cost"],
                    current_best["total_deadline_days"],
                    current_best["selected_partners"][0].name,
                )
            if current_best is None or candidate_key < current_key:
                best_by_first_partner[first_partner.id] = plan

        for plan in best_by_first_partner.values():
            first_segment = plan["route_segments"][0]
            first_partner = plan["selected_partners"][0]
            results.append(
                SimulationResult(
                    partner_id=first_partner.id,
                    partner_name=first_partner.name,
                    city=first_partner.city,
                    state=first_partner.state,
                    price=plan["total_cost"],
                    deadline_days=plan["total_deadline_days"],
                    rule_type=plan["segments"][0].rule_type,
                    latitude=first_partner.latitude,
                    longitude=first_partner.longitude,
                    distance_km=plan["total_distance_km"],
                    route_segments=plan["route_segments"],
                    total_days=plan["total_deadline_days"],
                    total_cost=plan["total_cost"],
                )
            )

        ordered = sorted(results, key=lambda item: (item.price, item.deadline_days, item.partner_name))
        best_price = min(ordered, key=lambda item: item.price, default=None)
        best_deadline = min(ordered, key=lambda item: (item.deadline_days, item.price), default=None)

        return {
            "origin": origin,
            "destination": destination,
            "distance_km": km,
            "results": ordered,
            "best_price": best_price,
            "best_deadline": best_deadline,
            "valid_partner_ids": [partner.id for partner in valid_partners],
            "suggested_route": best_route,
        }

    def simulate_multi_leg(
        self,
        origin_city: str,
        origin_state: str,
        destination_city: str,
        destination_state: str,
        partner_ids: list[int] | None = None,
        segment_pickup_modes: list[str] | None = None,
    ) -> dict[str, Any]:
        origin = self._build_point("Origem", origin_city, origin_state)
        destination = self._build_point("Destino", destination_city, destination_state)
        manual_override = partner_ids is not None
        partners = self._load_route_partners(partner_ids)
        if manual_override:
            self._validate_partner_coordinates(partners)
            route_points = self._build_manual_route_points(origin, destination, partners)
            plan = self._compile_route_plan(
                route_points,
                partners,
                manual_override=True,
                segment_pickup_modes=segment_pickup_modes,
            )
        else:
            routeable_partners = [
                partner for partner in partners if partner.latitude is not None and partner.longitude is not None
            ]
            candidate_routes = build_candidate_routes(origin, destination, routeable_partners)
            plan = self._find_best_route_plan(origin, destination, routeable_partners, candidate_routes)
            partners = routeable_partners

        plan["valid_partner_ids"] = [partner.id for partner in filter_valid_partners(origin, destination, partners)]
        return plan

    def calculate_rule_price(self, rule: FreightRule, km: float) -> float:
        rule_type = rule.rule_type.upper()

        if rule_type == "LINEAR":
            if km > rule.max_km:
                raise ValueError("Distancia excedeu a regra de cobertura maxima.")
            total = Decimal(str(rule.base_price)) + Decimal(str(km)) * Decimal(str(rule.price_per_km))
            return float(total.quantize(Decimal("0.01")))

        if rule_type == "FIXED":
            config = rule.extra_config or {}
            fixed_price = config.get("fixed_price")
            if fixed_price is None:
                raise ValueError("Regra FIXED requer extra_config.fixed_price.")
            return float(Decimal(str(fixed_price)).quantize(Decimal("0.01")))

        if rule_type == "TIERED":
            config = rule.extra_config or {}
            tiers = sorted(config.get("tiers", []), key=lambda item: item.get("up_to_km", 0))
            for tier in tiers:
                if km <= float(tier["up_to_km"]):
                    return float(Decimal(str(tier["price"])).quantize(Decimal("0.01")))
            raise ValueError("Nenhuma faixa corresponde a distancia informada.")

        raise ValueError("Tipo de regra nao suportado.")

    @staticmethod
    def build_route_summary(
        *,
        origin: str,
        destination: str,
        direct_distance_km: float,
        segments: list[SegmentResult],
        tax_rate: float,
        margin_rate: float,
        additional_fee: float,
    ) -> RouteSummary:
        subtotal = round(sum(segment.price for segment in segments), 2)
        taxes = round(subtotal * tax_rate, 2)
        margin = round(subtotal * margin_rate, 2)
        route_distance_km = round(sum(segment.distance_km for segment in segments), 2)
        total = round(subtotal + taxes + margin + additional_fee, 2)
        total_deadline_days = sum(segment.segment_days for segment in segments)
        return RouteSummary(
            origin=origin,
            destination=destination,
            direct_distance_km=direct_distance_km,
            route_distance_km=route_distance_km,
            subtotal=subtotal,
            taxes=taxes,
            margin=margin,
            additional_fees=round(additional_fee, 2),
            total=total,
            total_deadline_days=total_deadline_days,
        )

    def _load_route_partners(self, partner_ids: list[int] | None) -> list[Partner]:
        if partner_ids is not None:
            if not partner_ids:
                raise ValueError("Selecione ao menos um parceiro para montar a rota manual.")
            partners = self.partner_repository.get_by_ids(partner_ids)
            if len(partners) != len(partner_ids):
                raise ValueError("Um ou mais parceiros selecionados nao foram encontrados.")
            return partners

        partners = self.partner_repository.list_all(active_only=True)
        if not partners:
            raise ValueError("Nenhum parceiro ativo esta disponivel para montar a rota.")
        return partners

    def _build_route_points(
        self,
        origin: RoutePoint,
        destination: RoutePoint,
        partners: list[Partner],
        *,
        manual_override: bool,
    ) -> list[RoutePoint]:
        self._validate_partner_coordinates(partners)
        if manual_override:
            return self._build_manual_route_points(origin, destination, partners)

        try:
            return build_route(origin, destination, partners, scorer=lambda route: self._score_route(route, partners))
        except ValueError as exc:
            raise ValueError("No valid route found") from exc

    def _build_manual_route_points(
        self, origin: RoutePoint, destination: RoutePoint, partners: list[Partner]
    ) -> list[RoutePoint]:
        route_points = [origin]
        for partner in partners:
            route_points.append(self._partner_to_point(partner))
        route_points.append(destination)
        self._compile_route_plan(route_points, partners, manual_override=True)
        return route_points

    def _build_route_segments(
        self,
        route_points: list[RoutePoint],
        partners: list[Partner],
        segment_pickup_modes: list[str],
    ) -> list[SegmentResult]:
        partner_lookup = {partner.id: partner for partner in partners}
        segments: list[SegmentResult] = []
        running_cost = 0.0
        running_days = 0
        for index, handler_point in enumerate(route_points[1:-1], start=1):
            partner = partner_lookup.get(handler_point.partner_id)
            if not partner:
                raise ValueError(f"Parceiro da rota nao encontrado para o ponto {handler_point.label}.")
            start = route_points[0] if index == 1 else handler_point
            end = route_points[index + 1]
            segment = self._build_segment(
                index,
                partner,
                start,
                end,
                segment_pickup_modes[index - 1],
                running_cost,
                running_days,
            )
            running_cost = segment.total_cost
            running_days = segment.total_days
            segments.append(segment)
        return segments

    def _build_segment(
        self,
        segment_order: int,
        partner: Partner,
        start: RoutePoint,
        end: RoutePoint,
        pickup_mode: str,
        running_cost: float,
        running_days: int,
    ) -> SegmentResult:
        normalized_pickup_mode = normalize_pickup_mode(pickup_mode)
        distance_km = calculate_effective_distance(partner, start, end, normalized_pickup_mode)
        rule, price, segment_days = self._select_best_rule_quote(partner, distance_km, normalized_pickup_mode)
        return SegmentResult(
            segment_order=segment_order,
            partner_id=partner.id,
            partner_name=partner.name,
            origin_label=start.label,
            destination_label=end.label,
            origin_city=start.city,
            origin_state=start.state,
            destination_city=end.city,
            destination_state=end.state,
            distance_km=distance_km,
            price=price,
            deadline_days=segment_days,
            rule_type=rule.rule_type,
            segment_distance_km=distance_km,
            segment_days=segment_days,
            pickup_mode=normalized_pickup_mode,
            total_cost=round(running_cost + price, 2),
            total_days=running_days + segment_days,
        )

    @staticmethod
    def _partner_max_distance(partner: Partner) -> float:
        return max(
            (float(rule.max_km) for rule in partner.freight_rules if rule.max_km is not None),
            default=0.0,
        )

    @staticmethod
    def _validate_partner_coordinates(partners: list[Partner]) -> None:
        partners_sem_coords = [
            partner.name for partner in partners if partner.latitude is None or partner.longitude is None
        ]
        if partners_sem_coords:
            partner_list = ", ".join(partners_sem_coords)
            raise ValueError(
                f"Os seguintes parceiros nao possuem latitude/longitude e nao podem "
                f"ser usados na rota: {partner_list}. "
                f"Edite o parceiro e salve novamente para geocodificar automaticamente."
            )

    @staticmethod
    def _select_applicable_rule(partner: Partner, km: float) -> FreightRule | None:
        if not partner.freight_rules:
            raise ValueError(f"Partner {partner.name} has no rules loaded")

        normalized_rules: list[FreightRule] = []
        for rule in partner.freight_rules:
            rule.rule_type = (rule.rule_type or "").upper()
            normalized_rules.append(rule)

        tiered_rules = [rule for rule in normalized_rules if rule.rule_type == "TIERED"]
        for rule in sorted(tiered_rules, key=lambda item: (item.max_km, item.deadline_days)):
            tiers = sorted(
                (rule.extra_config or {}).get("tiers", []),
                key=lambda item: item.get("up_to_km", 0),
            )
            if any(km <= float(tier["up_to_km"]) for tier in tiers):
                return rule

        linear_rules = [
            rule
            for rule in normalized_rules
            if rule.rule_type == "LINEAR" and (rule.max_km is None or km <= rule.max_km)
        ]
        if linear_rules:
            return sorted(
                linear_rules, key=lambda item: (item.max_km or float("inf"), item.deadline_days)
            )[0]

        fixed_rules = [rule for rule in normalized_rules if rule.rule_type == "FIXED"]
        if fixed_rules:
            return sorted(fixed_rules, key=lambda item: (item.deadline_days, item.id))[0]

        return None

    def _select_best_rule_quote(
        self,
        partner: Partner,
        km: float,
        pickup_mode: str,
    ) -> tuple[FreightRule, float, int]:
        valid_quotes: list[tuple[float, int, str, FreightRule]] = []
        for rule in partner.freight_rules:
            normalized_type = (rule.rule_type or "").upper()
            if rule.max_km is not None and km > float(rule.max_km):
                continue
            if normalized_type == "LINEAR" and km > float(rule.max_km):
                continue
            if normalized_type == "TIERED":
                tiers = sorted(
                    (rule.extra_config or {}).get("tiers", []),
                    key=lambda item: item.get("up_to_km", 0),
                )
                if not any(km <= float(tier["up_to_km"]) for tier in tiers):
                    continue
            try:
                price = self.calculate_rule_price(rule, km)
            except ValueError:
                continue
            segment_days = self._calculate_segment_days(rule, km, pickup_mode)
            valid_quotes.append((price, segment_days, normalized_type, rule))

        if not valid_quotes:
            raise ValueError(
                f"O parceiro {partner.name} nao possui regra para o trecho de {km} km."
            )

        price, segment_days, _rule_type, rule = min(valid_quotes, key=lambda item: (item[0], item[1], item[2]))
        return rule, price, segment_days

    @staticmethod
    def _calculate_segment_days(rule: FreightRule, km: float, pickup_mode: str) -> int:
        max_km = float(rule.max_km or 0)
        if max_km <= 0:
            raise ValueError("Km maximo precisa ser maior que zero para estimar prazo.")
        estimated_days = ceil(km / max_km) * int(rule.deadline_days)
        if str(pickup_mode or "DIRECT").upper() == "HUB":
            estimated_days += 1
        return max(estimated_days, 1)

    def _compile_route_plan(
        self,
        route_points: list[RoutePoint],
        partners: list[Partner],
        *,
        manual_override: bool,
        segment_pickup_modes: list[str] | None = None,
    ) -> dict[str, Any]:
        if len(route_points) < 3:
            raise ValueError("No valid route found")
        resolved_pickup_modes = resolve_segment_pickup_modes(route_points, segment_pickup_modes)
        segments = self._build_route_segments(route_points, partners, resolved_pickup_modes)
        selected_partner_ids = [point.partner_id for point in route_points[1:-1] if point.partner_id is not None]
        partner_lookup = {partner.id: partner for partner in partners}
        selected_partners = [
            partner_lookup[partner_id] for partner_id in selected_partner_ids if partner_id in partner_lookup
        ]
        total_cost = round(segments[-1].total_cost if segments else 0.0, 2)
        total_distance_km = round(sum(segment.segment_distance_km for segment in segments), 2)
        total_deadline_days = segments[-1].total_days if segments else 0
        physical_path_points = build_physical_path(
            route_points,
            {partner.id: partner for partner in selected_partners},
            resolved_pickup_modes,
        )
        origin = route_points[0]
        destination = route_points[-1]
        route_segments = [
            RouteSegment(
                partner_id=segment.partner_id,
                partner_name=segment.partner_name,
                origin=(segment_start.latitude, segment_start.longitude),
                destination=(segment_end.latitude, segment_end.longitude),
                distance_km=segment.segment_distance_km,
                pickup_mode=segment.pickup_mode,
                segment_days=segment.segment_days,
                segment_cost=segment.price,
                rule_type=segment.rule_type,
            )
            for segment, segment_start, segment_end in [
                (
                    segment,
                    route_points[0] if segment.segment_order == 1 else route_points[segment.segment_order],
                    route_points[segment.segment_order + 1],
                )
                for segment in segments
            ]
        ]
        return {
            "origin": origin,
            "destination": destination,
            "direct_distance_km": calculate_distance_km(
                (origin.latitude, origin.longitude), (destination.latitude, destination.longitude)
            ),
            "selected_partners": selected_partners,
            "selected_partner_ids": selected_partner_ids,
            "segments": segments,
            "route_segments": route_segments,
            "segment_pickup_modes": resolved_pickup_modes,
            "route_points": route_points,
            "physical_path_points": physical_path_points,
            "total_cost": total_cost,
            "total_distance_km": total_distance_km,
            "total_deadline_days": total_deadline_days,
            "manual_override": manual_override,
        }

    def _find_best_route_plan(
        self,
        origin: RoutePoint,
        destination: RoutePoint,
        partners: list[Partner],
        candidate_routes: list[list[RoutePoint]],
    ) -> dict[str, Any]:
        if not candidate_routes:
            raise ValueError("No valid route found")
        plans = [
            self._compile_route_plan(route_points, partners, manual_override=False)
            for route_points in candidate_routes
        ]
        return min(plans, key=lambda plan: (plan["total_cost"], plan["total_deadline_days"]))

    def _score_route(self, route_points: list[RoutePoint], partners: list[Partner]) -> tuple[float, int]:
        plan = self._compile_route_plan(route_points, partners, manual_override=False)
        return (plan["total_cost"], plan["total_deadline_days"])

    @staticmethod
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

    @staticmethod
    def _build_point(label: str, city: str, state: str) -> RoutePoint:
        latitude, longitude = get_coordinates(city, state)
        return RoutePoint(
            label=label,
            city=city.strip(),
            state=state.strip().upper(),
            latitude=latitude,
            longitude=longitude,
            point_type="endpoint",
        )
