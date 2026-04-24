from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from rbr_transporte_logistica.core.models import FreightRule


class FreightRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_partner(self, partner_id: int) -> list[FreightRule]:
        stmt = (
            select(FreightRule)
            .where(FreightRule.partner_id == partner_id)
            .order_by(FreightRule.max_km)
        )
        return list(self.session.scalars(stmt).all())

    def get_by_id(self, rule_id: int) -> FreightRule | None:
        return self.session.get(FreightRule, rule_id)

    def add(self, rule: FreightRule) -> FreightRule:
        self.session.add(rule)
        self.session.flush()
        self.session.refresh(rule)
        return rule

    def save(self) -> None:
        self.session.flush()

    def delete(self, rule: FreightRule) -> None:
        self.session.delete(rule)
