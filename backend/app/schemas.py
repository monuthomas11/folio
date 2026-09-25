import uuid
from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, FiniteFloat, field_validator, model_validator


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class APIModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class UserOut(APIModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    created_at: datetime


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class HoldingIn(APIModel):
    symbol: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0)
    avg_buy_price: float = Field(gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    target_price: float | None = Field(default=None, gt=0)
    broker: str | None = Field(default=None, max_length=100)
    sector: str | None = Field(default=None, max_length=100)


class HoldingOut(APIModel):
    id: uuid.UUID
    symbol: str
    quantity: float
    avg_buy_price: float
    stop_loss: float | None
    target_price: float | None
    broker: str | None
    sector: str | None
    current_ltp: float | None
    one_day_change_pct: float | None
    last_updated: datetime | None
    created_at: datetime


class HoldingExitIn(APIModel):
    quantity: float = Field(gt=0)
    exit_price: float = Field(gt=0)


class HoldingExitOut(APIModel):
    id: uuid.UUID
    symbol: str
    quantity: float
    avg_buy_price: float
    exit_price: float
    cost_basis: float
    proceeds: float
    realized_pnl: float
    broker: str | None
    exited_at: datetime


TradeSide = Literal["long", "short"]


class TradeIn(APIModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: TradeSide
    entry_date: date
    entry_quantity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    broker: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class TradeExitIn(APIModel):
    quantity: float = Field(gt=0)
    exit_price: float = Field(gt=0)
    exit_date: date
    notes: str | None = Field(default=None, max_length=2000)


class TradeExitOut(APIModel):
    id: uuid.UUID
    quantity: float
    exit_price: float
    exit_date: date
    realized_pnl: float


class TradeOut(APIModel):
    id: uuid.UUID
    symbol: str
    side: TradeSide
    entry_date: date
    entry_quantity: float
    entry_price: float
    broker: str | None
    notes: str | None
    current_ltp: float | None
    last_updated: datetime | None
    remaining_quantity: float
    status: Literal["open", "closed"]
    realized_pnl: float
    unrealized_pnl: float | None
    total_pnl: float | None
    exits: list[TradeExitOut]


class TradebookSummaryOut(APIModel):
    trade_count: int
    open_count: int
    closed_count: int
    realized_pnl: float
    unrealized_pnl: float | None
    total_pnl: float | None
    unpriced_open_count: int


class TradebookOut(APIModel):
    summary: TradebookSummaryOut
    trades: list[TradeOut]


class PriceOut(APIModel):
    symbol: str
    ltp: float
    one_day_change_pct: float | None = None
    last_updated: datetime


class AlertOut(APIModel):
    id: uuid.UUID
    holding_id: uuid.UUID | None = None
    watchlist_item_id: uuid.UUID | None = None
    watchlist_level_id: uuid.UUID | None = None
    symbol: str
    kind: str
    price: float
    message: str | None
    dismissed: bool
    created_at: datetime


class SummaryOut(APIModel):
    portfolio_value: float
    invested: float
    total_pnl: float
    total_pnl_pct: float
    holding_count: int
    active_alert_count: int
    gainers: int
    losers: int
    realized_pnl: float
    realized_pnl_pct: float
    realized_cost_basis: float
    realized_proceeds: float
    closed_trade_count: int


class SnapshotOut(APIModel):
    summary: SummaryOut
    holdings: list[HoldingOut]
    alerts: list[AlertOut]
    realized_exits: list[HoldingExitOut]


class ImportRowError(BaseModel):
    row: int
    message: str


class ImportResult(BaseModel):
    created: int
    errors: list[ImportRowError]


class HoldingsImportIn(BaseModel):
    csv: str


WatchlistLevelKind = Literal["entry", "target", "stop-loss", "invalidation"]


class WatchlistLevelIn(APIModel):
    kind: WatchlistLevelKind
    label: str | None = Field(default=None, max_length=100)
    lower_price: FiniteFloat = Field(gt=0)
    upper_price: FiniteFloat | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_range(self):
        if self.upper_price is not None and self.upper_price < self.lower_price:
            raise ValueError("Upper price must be greater than or equal to lower price")
        return self


class WatchlistIn(APIModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )
    symbol: str = Field(min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=5000)
    levels: list[WatchlistLevelIn] = Field(default_factory=list, max_length=50)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Symbol must be text")
        normalized = value.strip().upper()
        if not normalized or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&._-" for character in normalized):
            raise ValueError("Symbol contains unsupported characters")
        return normalized


class WatchlistLevelOut(APIModel):
    id: uuid.UUID
    kind: WatchlistLevelKind
    label: str | None
    lower_price: float
    upper_price: float | None
    sort_order: int
    condition_met: bool
    created_at: datetime


class WatchlistOut(APIModel):
    id: uuid.UUID
    symbol: str
    notes: str | None
    current_ltp: float | None
    last_updated: datetime | None
    created_at: datetime
    updated_at: datetime
    levels: list[WatchlistLevelOut]


class APIKeyCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(ord(character) < 32 for character in normalized):
            raise ValueError("Name must contain printable text")
        return normalized


class APIKeyOut(APIModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class APIKeyCreatedOut(APIKeyOut):
    key: str


class AnalysisRunOut(APIModel):
    id: uuid.UUID
    kind: str
    holding_id: uuid.UUID | None
    status: str
    stage: str | None
    provider: str
    model_name: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class StartedRunOut(APIModel):
    run_id: uuid.UUID


class FairValueRange(BaseModel):
    low: float | None = None
    base: float | None = None
    high: float | None = None


class RecommendationOut(APIModel):
    id: uuid.UUID
    run_id: uuid.UUID
    holding_id: uuid.UUID | None
    kind: str
    symbol: str
    rating: str
    action: str
    confidence: int | None
    scores: dict | None
    portfolio_weight: float | None
    thesis_status: str | None
    summary: str
    why: str | None
    bull_case: str | None
    base_case: str | None
    bear_case: str | None
    key_reasons: list[str]
    key_risks: list[str]
    buy_conditions: list[str]
    reduce_conditions: list[str]
    exit_conditions: list[str]
    support_levels: list[float]
    resistance_levels: list[float]
    fair_value_range: FairValueRange | None
    evidence_ids: list[str]
    evidence: list[dict] | None
    data_quality: str
    quality_flags: list[str]
    health_score: int | None
    positives: list[str]
    concerns: list[str]
    priority_note: str | None
    analysis_timestamps: dict | None
    created_at: datetime


class LatestAnalysisRunInfo(APIModel):
    provider: str
    model_name: str | None = None
    completed_at: datetime | None = None
    created_at: datetime


class LatestPortfolioAnalysisOut(APIModel):
    portfolio: RecommendationOut | None
    holdings: list[RecommendationOut]
    last_run: LatestAnalysisRunInfo | None = None


class ChatMessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    context: str = Field(pattern="^(holding|portfolio)$")
    holdingId: str | None = None
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessageIn] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    reply: str
    provider: str
    modelName: str | None = None


class InvestmentProfileIn(APIModel):
    investment_style: str | None = Field(default=None, max_length=30)
    risk_tolerance: str | None = Field(default=None, max_length=20)
    investment_horizon: str | None = Field(default=None, max_length=30)
    max_single_stock_weight: float | None = Field(default=None, ge=0, le=100)
    max_sector_weight: float | None = Field(default=None, ge=0, le=100)
    warn_single_stock_weight: float | None = Field(default=None, ge=0, le=100)
    warn_sector_weight: float | None = Field(default=None, ge=0, le=100)


class InvestmentProfileOut(APIModel):
    investment_style: str
    risk_tolerance: str
    investment_horizon: str
    max_single_stock_weight: float
    max_sector_weight: float
    warn_single_stock_weight: float
    warn_sector_weight: float
    updated_at: datetime
