from __future__ import annotations

from decimal import Decimal
from typing import Any

from rbr_transporte_logistica.core.models import FreightRule, Partner
from rbr_transporte_logistica.repositories.freight_repository import FreightRepository
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.utils.geo_utils import get_coordinates


class PartnerService:
    def __init__(
        self, partner_repository: PartnerRepository, freight_repository: FreightRepository
    ) -> None:
        self.partner_repository = partner_repository
        self.freight_repository = freight_repository

    def list_partners(self, active_only: bool = False) -> list[Partner]:
        return self.partner_repository.list_all(active_only=active_only)

    def create_partner(
        self,
        name: str,
        city: str,
        state: str,
        latitude: float | None = None,
        longitude: float | None = None,
        active: bool = True,
    ) -> Partner:
        normalized_name = name.strip()
        normalized_city = city.strip()
        normalized_state = state.strip().upper()
        if not normalized_name or not normalized_city or not normalized_state:
            raise ValueError("Nome, cidade e estado sao obrigatorios.")
        existing = self.partner_repository.get_by_name(normalized_name)
        if existing:
            raise ValueError(f"Parceiro '{normalized_name}' ja existe.")

        if latitude is None or longitude is None:
            latitude, longitude = get_coordinates(normalized_city, normalized_state)

        partner = Partner(
            name=normalized_name,
            city=normalized_city,
            state=normalized_state,
            latitude=latitude,
            longitude=longitude,
            active=active,
        )
        return self.partner_repository.add(partner)

    def update_partner(self, partner_id: int, **fields: Any) -> Partner:
        partner = self.partner_repository.get_by_id(partner_id)
        if not partner:
            raise ValueError("Parceiro nao encontrado.")

        city = str(fields.get("city", partner.city)).strip()
        state = str(fields.get("state", partner.state)).strip().upper()
        if not str(fields.get("name", partner.name)).strip() or not city or not state:
            raise ValueError("Nome, cidade e estado sao obrigatorios.")
        latitude = fields.get("latitude", partner.latitude)
        longitude = fields.get("longitude", partner.longitude)

        if city != partner.city or state != partner.state or latitude is None or longitude is None:
            latitude, longitude = get_coordinates(city, state)

        partner.name = str(fields.get("name", partner.name)).strip()
        partner.city = city
        partner.state = state
        partner.latitude = latitude
        partner.longitude = longitude
        partner.active = bool(fields.get("active", partner.active))

        self.partner_repository.save()
        return partner

    def delete_partner(self, partner_id: int) -> None:
        partner = self.partner_repository.get_by_id(partner_id)
        if not partner:
            raise ValueError("Parceiro nao encontrado.")
        self.partner_repository.delete(partner)

    def set_partner_active(self, partner_id: int, active: bool) -> Partner:
        partner = self.partner_repository.get_by_id(partner_id)
        if not partner:
            raise ValueError("Parceiro nao encontrado.")
        partner.active = active
        self.partner_repository.save()
        return partner

    def add_rule(
        self,
        partner_id: int,
        deadline_days: int,
        rule_type: str = "LINEAR",
        base_price: float = 0.0,
        price_per_km: float = 0.0,
        max_km: float = 0.0,
        extra_config: dict[str, Any] | None = None,
    ) -> FreightRule:
        partner = self.partner_repository.get_by_id(partner_id)
        if not partner:
            raise ValueError("Parceiro nao encontrado.")

        payload = self._build_rule_payload(
            rule_type=rule_type.upper(),
            base_price=base_price,
            price_per_km=price_per_km,
            max_km=max_km,
            deadline_days=deadline_days,
            extra_config=extra_config,
        )
        rule = FreightRule(partner_id=partner_id, **payload)
        rule.rule_type = rule.rule_type.upper()
        partner.freight_rules.append(rule)
        self.freight_repository.save()
        self.partner_repository.save()
        reloaded_partner = self.partner_repository.get_by_id(partner_id)
        if not reloaded_partner or not reloaded_partner.freight_rules:
            raise ValueError(f"Falha ao vincular regra ao parceiro {partner.name}.")
        return reloaded_partner.freight_rules[-1]

    def update_rule(
        self,
        rule_id: int,
        *,
        deadline_days: int,
        rule_type: str,
        base_price: float = 0.0,
        price_per_km: float = 0.0,
        max_km: float = 0.0,
        extra_config: dict[str, Any] | None = None,
    ) -> FreightRule:
        rule = self.freight_repository.get_by_id(rule_id)
        if not rule:
            raise ValueError("Regra nao encontrada.")

        payload = self._build_rule_payload(
            rule_type=rule_type.upper(),
            base_price=base_price,
            price_per_km=price_per_km,
            max_km=max_km,
            deadline_days=deadline_days,
            extra_config=extra_config,
        )
        for key, value in payload.items():
            setattr(rule, key, value)
        rule.rule_type = rule.rule_type.upper()
        self.freight_repository.save()
        return rule

    def delete_rule(self, rule_id: int) -> None:
        rule = self.freight_repository.get_by_id(rule_id)
        if not rule:
            raise ValueError("Regra nao encontrada.")
        self.freight_repository.delete(rule)

    @staticmethod
    def _build_rule_payload(
        *,
        rule_type: str,
        base_price: float,
        price_per_km: float,
        max_km: float,
        deadline_days: int,
        extra_config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if deadline_days <= 0:
            raise ValueError("Prazo precisa ser maior que zero.")

        if rule_type == "LINEAR":
            if max_km <= 0:
                raise ValueError("Km maximo precisa ser maior que zero.")
            return {
                "base_price": float(Decimal(str(base_price))),
                "price_per_km": float(Decimal(str(price_per_km))),
                "max_km": float(max_km),
                "deadline_days": int(deadline_days),
                "rule_type": "LINEAR",
                "extra_config": None,
            }

        if rule_type == "FIXED":
            fixed_price = float((extra_config or {}).get("fixed_price", 0))
            if fixed_price <= 0:
                raise ValueError("Preco fixo precisa ser maior que zero.")
            return {
                "base_price": 0.0,
                "price_per_km": 0.0,
                "max_km": float(max_km or 999999),
                "deadline_days": int(deadline_days),
                "rule_type": "FIXED",
                "extra_config": {"fixed_price": fixed_price},
            }

        if rule_type == "TIERED":
            tiers = (extra_config or {}).get("tiers", [])
            if not tiers:
                raise ValueError("Informe ao menos uma faixa para a regra TIERED.")
            normalized_tiers = []
            for tier in tiers:
                km_limit = float(tier["up_to_km"])
                price = float(tier["price"])
                if km_limit <= 0 or price <= 0:
                    raise ValueError("Cada faixa precisa ter km e preco positivos.")
                normalized_tiers.append({"up_to_km": km_limit, "price": price})
            max_limit = max(tier["up_to_km"] for tier in normalized_tiers)
            return {
                "base_price": 0.0,
                "price_per_km": 0.0,
                "max_km": float(max_km or max_limit),
                "deadline_days": int(deadline_days),
                "rule_type": "TIERED",
                "extra_config": {"tiers": sorted(normalized_tiers, key=lambda item: item["up_to_km"])},
            }

        raise ValueError("Tipo de regra invalido.")
