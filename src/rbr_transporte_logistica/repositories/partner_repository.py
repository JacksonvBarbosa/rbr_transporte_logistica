from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from rbr_transporte_logistica.core.models import Partner


class PartnerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self, active_only: bool = False) -> list[Partner]:
        stmt = select(Partner).order_by(Partner.name)
        if active_only:
            stmt = stmt.where(Partner.active.is_(True))
        return list(self.session.scalars(stmt).unique().all())

    def get_by_id(self, partner_id: int) -> Partner | None:
        return self.session.get(Partner, partner_id)

    def get_by_name(self, name: str) -> Partner | None:
        stmt = select(Partner).where(Partner.name == name)
        return self.session.scalar(stmt)

    def get_by_ids(self, partner_ids: list[int]) -> list[Partner]:
        if not partner_ids:
            return []
        stmt = select(Partner).where(Partner.id.in_(partner_ids))
        partners = list(self.session.scalars(stmt).unique().all())
        order_map = {partner_id: index for index, partner_id in enumerate(partner_ids)}
        return sorted(partners, key=lambda partner: order_map.get(partner.id, len(order_map)))

    def add(self, partner: Partner) -> Partner:
        self.session.add(partner)
        self.session.flush()
        self.session.refresh(partner)
        return partner

    def delete(self, partner: Partner) -> None:
        self.session.delete(partner)

    def save(self) -> None:
        self.session.flush()
