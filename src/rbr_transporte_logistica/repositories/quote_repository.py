from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rbr_transporte_logistica.core.models import FreightTableImport, Partner, Quote, QuoteItem


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(Decimal(str(value)))


class ParceiroRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def contar_ativos(self) -> int:
        stmt = select(func.count()).select_from(Partner).where(Partner.active.is_(True))
        return int(self.session.scalar(stmt) or 0)

    def listar_ativos(self) -> list[Partner]:
        stmt = select(Partner).where(Partner.active.is_(True)).order_by(Partner.name)
        return list(self.session.scalars(stmt).unique().all())


class CotacaoRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def criar(
        self,
        *,
        customer_name: str,
        origin: str,
        destination: str,
        route_label: str,
        partner_id: int | None,
        partner_name: str,
        status: str,
        freight_gross: float,
        icms_rate: float,
        icms_value: float,
        iss_rate: float,
        iss_value: float,
        margin_rate: float,
        margin_value: float,
        total_value: float,
        total_deadline_days: int,
        direct_distance_km: float,
        route_distance_km: float,
        items: Iterable[Any],
    ) -> Quote:
        quote = Quote(
            number=self._next_number(),
            customer_name=customer_name.strip() or "Cliente nao informado",
            origin=origin,
            destination=destination,
            route_label=route_label,
            partner_id=partner_id,
            partner_name=partner_name,
            status=status,
            freight_gross=_to_float(freight_gross),
            icms_rate=_to_float(icms_rate),
            icms_value=_to_float(icms_value),
            iss_rate=_to_float(iss_rate),
            iss_value=_to_float(iss_value),
            margin_rate=_to_float(margin_rate),
            margin_value=_to_float(margin_value),
            total_value=_to_float(total_value),
            total_deadline_days=int(total_deadline_days),
            direct_distance_km=_to_float(direct_distance_km),
            route_distance_km=_to_float(route_distance_km),
        )
        self.session.add(quote)
        self.session.flush()
        for item in items:
            payload = asdict(item) if is_dataclass(item) else dict(item)
            quote.items.append(
                QuoteItem(
                    quote_id=quote.id,
                    segment_order=int(payload.get("segment_order", 1)),
                    partner_id=payload.get("partner_id"),
                    partner_name=str(payload.get("partner_name", "")),
                    origin_label=str(payload.get("origin_label", "")),
                    destination_label=str(payload.get("destination_label", "")),
                    origin_city=str(payload.get("origin_city", "")),
                    origin_state=str(payload.get("origin_state", "")),
                    destination_city=str(payload.get("destination_city", "")),
                    destination_state=str(payload.get("destination_state", "")),
                    distance_km=_to_float(payload.get("distance_km", 0)),
                    value=_to_float(payload.get("price", payload.get("value", 0))),
                    deadline_days=int(payload.get("deadline_days", payload.get("segment_days", 0))),
                    rule_type=str(payload.get("rule_type", "LINEAR")),
                    pickup_mode=str(payload.get("pickup_mode", "DIRECT")),
                )
            )
        self.session.flush()
        self.session.refresh(quote)
        return quote

    def listar_recentes(self, limite: int = 20) -> list[Quote]:
        stmt = select(Quote).order_by(Quote.created_at.desc()).limit(limite)
        return list(self.session.scalars(stmt).unique().all())

    def listar_fechadas(self) -> list[Quote]:
        stmt = select(Quote).where(Quote.status == "fechado").order_by(Quote.created_at.desc())
        return list(self.session.scalars(stmt).unique().all())

    def faturamento_fechado(self) -> float:
        stmt = select(func.sum(Quote.total_value)).where(Quote.status == "fechado")
        return _to_float(self.session.scalar(stmt))

    def contar_fechadas(self) -> int:
        stmt = select(func.count()).select_from(Quote).where(Quote.status == "fechado")
        return int(self.session.scalar(stmt) or 0)

    def obter(self, quote_id: int) -> Quote | None:
        return self.session.get(Quote, quote_id)

    def _next_number(self) -> str:
        stmt = select(func.count()).select_from(Quote)
        next_id = int(self.session.scalar(stmt) or 0) + 1
        return f"COT-{next_id:05d}"


class TabelaFreteRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def criar_tabela(
        self,
        *,
        partner_id: int,
        description: str,
        filename: str,
        source_type: str,
        row_count: int,
        column_mapping: dict[str, str] | None = None,
    ) -> FreightTableImport:
        item = FreightTableImport(
            partner_id=partner_id,
            description=description.strip() or "Tabela sem descricao",
            filename=filename,
            source_type=source_type.lower(),
            row_count=int(row_count),
            status="ativa",
            active=True,
            column_mapping=column_mapping or None,
        )
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def listar_tabelas(self) -> list[FreightTableImport]:
        stmt = select(FreightTableImport).order_by(FreightTableImport.created_at.desc())
        return list(self.session.scalars(stmt).unique().all())

    def deletar_tabela(self, tabela_id: int) -> None:
        tabela = self.session.get(FreightTableImport, tabela_id)
        if tabela is None:
            raise ValueError("Tabela nao encontrada.")
        tabela.active = False
        tabela.status = "inativa"
        self.session.flush()
