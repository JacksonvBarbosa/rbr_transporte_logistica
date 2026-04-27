from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String
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
    quotes: Mapped[list["Quote"]] = relationship(
        "Quote",
        back_populates="partner",
        lazy="selectin",
    )
    imported_tables: Mapped[list["FreightTableImport"]] = relationship(
        "FreightTableImport",
        back_populates="partner",
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


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    route_label: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"), nullable=True)
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="aberto", index=True)
    freight_gross: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    icms_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    icms_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    iss_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    iss_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    margin_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    margin_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_deadline_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    direct_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    route_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    partner: Mapped[Partner | None] = relationship("Partner", back_populates="quotes")
    items: Mapped[list["QuoteItem"]] = relationship(
        "QuoteItem",
        back_populates="quote",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    segment_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"), nullable=True)
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_label: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_label: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_city: Mapped[str] = mapped_column(String(120), nullable=False)
    origin_state: Mapped[str] = mapped_column(String(2), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_state: Mapped[str] = mapped_column(String(2), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    deadline_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, default="LINEAR")
    pickup_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="DIRECT")

    quote: Mapped[Quote] = relationship("Quote", back_populates="items")


class FreightTableImport(Base):
    __tablename__ = "freight_table_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ativa")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    column_mapping: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    partner: Mapped[Partner] = relationship("Partner", back_populates="imported_tables")
