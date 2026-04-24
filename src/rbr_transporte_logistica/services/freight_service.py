from __future__ import annotations

from decimal import Decimal
from typing import Any

from rbr_transporte_logistica.core.models import FreightRule, Partner
from rbr_transporte_logistica.dto.simulation import (
    RoutePoint,
    RouteSummary,
    SegmentResult,
    SimulationResult,
)
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.services.route_builder import build_route
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

        partners = self.partner_repository.list_all(active_only=True)
        results: list[SimulationResult] = []

        for partner in partners:
            try:
                rule = self._select_applicable_rule(partner, km)
            except ValueError:
                continue
            if not rule:
                continue
            price = self.calculate_rule_price(rule, km)
            results.append(
                SimulationResult(
                    partner_id=partner.id,
                    partner_name=partner.name,
                    city=partner.city,
                    state=partner.state,
                    price=price,
                    deadline_days=rule.deadline_days,
                    rule_type=rule.rule_type,
                    latitude=partner.latitude,
                    longitude=partner.longitude,
                    distance_km=km,
                    origin_point=origin,
                    destination_point=destination,
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
        }

    def simulate_multi_leg(
        self,
        origin_city: str,
        origin_state: str,
        destination_city: str,
        destination_state: str,
        partner_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        origin = self._build_point("Origem", origin_city, origin_state)
        destination = self._build_point("Destino", destination_city, destination_state)
        manual_override = partner_ids is not None
        partners = self._load_route_partners(partner_ids)
        route_points = self._build_route_points(origin, destination, partners, manual_override=manual_override)
        segments = self._build_route_segments(route_points, partners)
        total_cost = round(sum(segment.price for segment in segments), 2)
        total_distance_km = round(sum(segment.distance_km for segment in segments), 2)
        total_deadline_days = sum(segment.deadline_days for segment in segments)
        selected_partner_ids = [
            point.partner_id for point in route_points if point.partner_id is not None
        ]
        partner_lookup = {partner.id: partner for partner in partners}

        return {
            "origin": origin,
            "destination": destination,
            "direct_distance_km": calculate_distance_km(
                (origin.latitude, origin.longitude), (destination.latitude, destination.longitude)
            ),
            "selected_partners": [
                partner_lookup[partner_id]
                for partner_id in selected_partner_ids
                if partner_id in partner_lookup
            ],
            "selected_partner_ids": selected_partner_ids,
            "segments": segments,
            "route_points": route_points,
            "total_cost": total_cost,
            "total_distance_km": total_distance_km,
            "total_deadline_days": total_deadline_days,
            "manual_override": manual_override,
        }

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
        total_deadline_days = sum(segment.deadline_days for segment in segments)
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
            return build_route(origin, destination, partners)
        except ValueError as exc:
            raise ValueError("No valid route found") from exc

    def _build_manual_route_points(
        self, origin: RoutePoint, destination: RoutePoint, partners: list[Partner]
    ) -> list[RoutePoint]:
        route_points = [origin]
        for partner in partners:
            max_distance = self._partner_max_distance(partner)
            partner_point = RoutePoint(
                label=partner.name,
                city=partner.city,
                state=partner.state,
                latitude=float(partner.latitude),
                longitude=float(partner.longitude),
                partner_id=partner.id,
                point_type="partner",
            )
            start = route_points[-1]
            distance_to_partner = calculate_distance_km(
                (start.latitude, start.longitude),
                (partner_point.latitude, partner_point.longitude),
            )
            if distance_to_partner > max_distance:
                raise ValueError(
                    f"O parceiro {partner.name} nao consegue assumir o trecho de "
                    f"{start.label} ate {partner_point.label}."
                )
            route_points.append(partner_point)

        last_partner = partners[-1]
        last_partner_distance = calculate_distance_km(
            (route_points[-1].latitude, route_points[-1].longitude),
            (destination.latitude, destination.longitude),
        )
        if last_partner_distance > self._partner_max_distance(last_partner):
            raise ValueError(
                f"O parceiro {last_partner.name} nao consegue finalizar a entrega para "
                f"{destination.city}/{destination.state}."
            )
        route_points.append(destination)
        return route_points

    def _build_route_segments(
        self, route_points: list[RoutePoint], partners: list[Partner]
    ) -> list[SegmentResult]:
        partner_lookup = {partner.id: partner for partner in partners}
        segments: list[SegmentResult] = []

        for index in range(1, len(route_points) - 1):
            end = route_points[index]
            partner = partner_lookup.get(end.partner_id)
            if not partner:
                raise ValueError(f"Parceiro da rota nao encontrado para o ponto {end.label}.")
            start = route_points[index - 1]
            segments.append(self._build_segment(index, partner, start, end))

        last_partner_point = route_points[-2]
        last_partner = partner_lookup.get(last_partner_point.partner_id)
        if not last_partner:
            raise ValueError("A rota precisa terminar em um parceiro valido antes do destino.")
        segments.append(
            self._build_segment(
                len(segments) + 1,
                last_partner,
                last_partner_point,
                route_points[-1],
            )
        )
        return segments

    def _build_segment(
        self, segment_order: int, partner: Partner, start: RoutePoint, end: RoutePoint
    ) -> SegmentResult:
        distance_km = calculate_distance_km(
            (start.latitude, start.longitude), (end.latitude, end.longitude)
        )
        rule = self._select_applicable_rule(partner, distance_km)
        if not rule:
            raise ValueError(
                f"O parceiro {partner.name} nao possui regra para o trecho de {distance_km} km."
            )
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
            price=self.calculate_rule_price(rule, distance_km),
            deadline_days=rule.deadline_days,
            rule_type=rule.rule_type,
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

        print(
            f"partner={partner.name} loaded_rules="
            f"{[(rule.id, rule.rule_type, rule.max_km) for rule in partner.freight_rules]}"
        )

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
