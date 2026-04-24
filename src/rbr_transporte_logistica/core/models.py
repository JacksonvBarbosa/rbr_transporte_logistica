from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rbr_transporte_logistica.core.database import Base


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    freight_rules: Mapped[list["FreightRule"]] = relationship(
        "FreightRule",
        back_populates="partner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class FreightRule(Base):
    __tablename__ = "freight_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    price_per_km: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    max_km: Mapped[float] = mapped_column(Float, nullable=False)
    deadline_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, default="LINEAR")
    extra_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    partner: Mapped[Partner] = relationship("Partner", back_populates="freight_rules")
