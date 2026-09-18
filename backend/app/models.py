import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
try:
    from sqlalchemy import Uuid
except ImportError:  # pragma: no cover
    Uuid = PG_UUID


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    watchlist_alerts: Mapped[list["WatchlistAlert"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    holding_exits: Mapped[list["HoldingExit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Numeric(10, 3))
    avg_buy_price: Mapped[float] = mapped_column(Numeric(12, 4))
    stop_loss: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    target_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_ltp: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    one_day_change_pct: Mapped[float | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="holdings")
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="holding", cascade="all, delete-orphan"
    )


class HoldingExit(Base):
    __tablename__ = "holding_exits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Numeric(10, 3))
    avg_buy_price: Mapped[float] = mapped_column(Numeric(12, 4))
    exit_price: Mapped[float] = mapped_column(Numeric(12, 4))
    cost_basis: Mapped[float] = mapped_column(Numeric(14, 4))
    proceeds: Mapped[float] = mapped_column(Numeric(14, 4))
    realized_pnl: Mapped[float] = mapped_column(Numeric(14, 4))
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    exited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped[User] = relationship(back_populates="holding_exits")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    holding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("holdings.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20))
    price: Mapped[float] = mapped_column(Numeric(12, 4))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="alerts")
    holding: Mapped[Holding] = relationship(back_populates="alerts")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_ltp: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="watchlist_items")
    levels: Mapped[list["WatchlistLevel"]] = relationship(
        back_populates="watchlist_item", cascade="all, delete-orphan", order_by="WatchlistLevel.sort_order"
    )
    alerts: Mapped[list["WatchlistAlert"]] = relationship(
        back_populates="watchlist_item", cascade="all, delete-orphan"
    )


class WatchlistLevel(Base):
    __tablename__ = "watchlist_levels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    watchlist_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlist_items.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lower_price: Mapped[float] = mapped_column(Numeric(12, 4))
    upper_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    condition_met: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    watchlist_item: Mapped[WatchlistItem] = relationship(back_populates="levels")
    alerts: Mapped[list["WatchlistAlert"]] = relationship(
        back_populates="watchlist_level", cascade="all, delete-orphan"
    )


class WatchlistAlert(Base):
    __tablename__ = "watchlist_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    watchlist_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlist_items.id", ondelete="CASCADE"), index=True
    )
    watchlist_level_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlist_levels.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(30))
    price: Mapped[float] = mapped_column(Numeric(12, 4))
    message: Mapped[str] = mapped_column(Text)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="watchlist_alerts")
    watchlist_item: Mapped[WatchlistItem] = relationship(back_populates="alerts")
    watchlist_level: Mapped[WatchlistLevel] = relationship(back_populates="alerts")


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    key_prefix: Mapped[str] = mapped_column(String(20), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="api_keys")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    holding_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("holdings.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="CREATED", index=True)
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider: Mapped[str] = mapped_column(String(40))
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    holding_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("holdings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    symbol: Mapped[str] = mapped_column(String(40))
    rating: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    portfolio_weight: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    thesis_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    why: Mapped[str | None] = mapped_column(Text, nullable=True)
    bull_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    bear_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_reasons: Mapped[list] = mapped_column(JSON, default=list)
    key_risks: Mapped[list] = mapped_column(JSON, default=list)
    buy_conditions: Mapped[list] = mapped_column(JSON, default=list)
    reduce_conditions: Mapped[list] = mapped_column(JSON, default=list)
    exit_conditions: Mapped[list] = mapped_column(JSON, default=list)
    support_levels: Mapped[list] = mapped_column(JSON, default=list)
    resistance_levels: Mapped[list] = mapped_column(JSON, default=list)
    fair_value_range: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_quality: Mapped[str] = mapped_column(String(20))
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positives: Mapped[list] = mapped_column(JSON, default=list)
    concerns: Mapped[list] = mapped_column(JSON, default=list)
    priority_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_timestamps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InvestmentProfile(Base):
    __tablename__ = "investment_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    investment_style: Mapped[str] = mapped_column(String(30), default="Moderate")
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="Medium")
    investment_horizon: Mapped[str] = mapped_column(
        String(30), default="Medium term: 6-24 months"
    )
    max_single_stock_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=15.0)
    max_sector_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=35.0)
    warn_single_stock_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=10.0)
    warn_sector_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=25.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
