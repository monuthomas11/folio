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
AssetClass = Literal["equity", "fno"]
InstrumentType = Literal["equity", "future", "option"]
Exchange = Literal["NSE", "BSE"]
UnderlyingType = Literal["index", "stock"]
OptionType = Literal["CE", "PE"]


class TradeChargesIn(APIModel):
    brokerage: float | None = Field(default=None, ge=0)
    stt_ctt: float | None = Field(default=None, ge=0)
    exchange_transaction: float | None = Field(default=None, ge=0)
    sebi: float | None = Field(default=None, ge=0)
    gst: float | None = Field(default=None, ge=0)
    stamp_duty: float | None = Field(default=None, ge=0)
    ipft: float | None = Field(default=None, ge=0)
    other: float | None = Field(default=None, ge=0)
    contract_note_ref: str | None = Field(default=None, max_length=100)


class TradeChargesOut(TradeChargesIn):
    id: uuid.UUID
    leg_type: Literal["entry", "exit"]
    total: float | None
    complete: bool


class TradeIn(APIModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: TradeSide
    asset_class: AssetClass = "equity"
    instrument_type: InstrumentType = "equity"
    exchange: Exchange | None = None
    underlying_type: UnderlyingType | None = None
    underlying_symbol: str | None = Field(default=None, max_length=40)
    contract_symbol: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None
    strike_price: float | None = Field(default=None, gt=0)
    tick_size: float | None = Field(default=None, gt=0)
    option_type: OptionType | None = None
    lot_size: int | None = Field(default=None, gt=0)
    entry_lots: int | None = Field(default=None, gt=0)
    product_type: str | None = Field(default=None, max_length=20)
    entry_at: datetime | None = None
    entry_order_id: str | None = Field(default=None, max_length=100)
    entry_contract_note_ref: str | None = Field(default=None, max_length=100)
    strategy: str | None = Field(default=None, max_length=100)
    thesis: str | None = Field(default=None, max_length=4000)
    settlement_type: str | None = Field(default=None, max_length=20)
    margin_used: float | None = Field(default=None, ge=0)
    entry_date: date
    entry_quantity: float | None = Field(default=None, gt=0)
    entry_price: float = Field(gt=0)
    broker: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    entry_charges: TradeChargesIn | None = None

    @model_validator(mode="after")
    def validate_trade_shape(self):
        if self.asset_class == "equity":
            if self.instrument_type != "equity":
                raise ValueError("Equity trades must use the equity instrument type")
            if self.entry_quantity is None:
                raise ValueError("Equity trades require entry quantity")
            return self

        if self.side != "long":
            raise ValueError("F&O currently supports long trades only")
        if self.expiry_date is not None and self.expiry_date < self.entry_date:
            raise ValueError("Expiry date cannot be before entry date")
        if self.instrument_type not in {"future", "option"}:
            raise ValueError("F&O trades must be futures or options")
        required = {
            "exchange": self.exchange,
            "underlying_type": self.underlying_type,
            "underlying_symbol": self.underlying_symbol,
            "contract_symbol": self.contract_symbol,
            "expiry_date": self.expiry_date,
            "tick_size": self.tick_size,
            "lot_size": self.lot_size,
            "entry_lots": self.entry_lots,
        }
        if any(value in (None, "") for value in required.values()):
            raise ValueError("F&O trades require exchange, underlying, contract, expiry, lot size, and lots")
        if self.instrument_type == "option":
            if self.strike_price is None or self.option_type is None:
                raise ValueError("Options require strike price and option type")
        elif self.strike_price is not None or self.option_type is not None:
            raise ValueError("Futures cannot have strike price or option type")
        if self.entry_quantity is not None:
            expected = self.entry_lots * self.lot_size
            if self.entry_quantity != expected:
                raise ValueError("F&O quantity must equal lots multiplied by lot size")
        return self


class TradeExitIn(APIModel):
    quantity: float | None = Field(default=None, gt=0)
    exit_lots: int | None = Field(default=None, gt=0)
    exit_price: float = Field(gt=0)
    exit_date: date
    exit_at: datetime | None = None
    exit_reason: str | None = Field(default=None, max_length=30)
    exit_order_id: str | None = Field(default=None, max_length=100)
    exit_contract_note_ref: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    charges: TradeChargesIn | None = None


class TradeMarkIn(APIModel):
    ltp: float = Field(gt=0)
    source: Literal["manual", "exchange"] = "manual"


class TradeExitChargesIn(TradeChargesIn):
    pass


class TradeExitOut(APIModel):
    id: uuid.UUID
    quantity: float
    exit_lots: int | None
    exit_price: float
    exit_date: date
    exit_at: datetime | None
    exit_reason: str | None
    exit_order_id: str | None
    exit_contract_note_ref: str | None
    notes: str | None
    realized_pnl: float
    gross_realized_pnl: float
    net_realized_pnl: float | None
    charges: TradeChargesOut | None


class TradeOut(APIModel):
    id: uuid.UUID
    symbol: str
    side: TradeSide
    asset_class: AssetClass
    instrument_type: InstrumentType
    exchange: Exchange | None
    underlying_type: UnderlyingType | None
    underlying_symbol: str | None
    contract_symbol: str | None
    expiry_date: date | None
    strike_price: float | None
    tick_size: float | None
    option_type: OptionType | None
    lot_size: int | None
    entry_lots: int | None
    remaining_lots: int | None
    entry_at: datetime | None
    entry_order_id: str | None
    entry_contract_note_ref: str | None
    strategy: str | None
    thesis: str | None
    settlement_type: str | None
    product_type: str | None
    margin_used: float | None
    entry_date: date
    entry_quantity: float
    entry_price: float
    broker: str | None
    notes: str | None
    current_ltp: float | None
    mark_source: str | None
    last_updated: datetime | None
    remaining_quantity: float
    gross_entry_value: float
    gross_realized_pnl: float
    gross_unrealized_pnl: float | None
    gross_total_pnl: float | None
    net_realized_pnl: float | None
    net_unrealized_pnl: float | None
    net_total_pnl: float | None
    entry_charges: float | None
    entry_charge: TradeChargesOut | None
    exit_charges: float | None
    total_charges: float | None
    charges_complete: bool
    capital_basis: float | None
    open_exposure: float | None
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
    gross_realized_pnl: float
    gross_unrealized_pnl: float | None
    gross_total_pnl: float | None
    net_realized_pnl: float | None
    net_unrealized_pnl: float | None
    net_total_pnl: float | None
    total_charges: float | None
    open_exposure: float | None
    incomplete_charge_count: int
    win_rate: float | None


class TradeQuoteErrorOut(APIModel):
    trade_id: uuid.UUID
    symbol: str
    message: str


class TradebookOut(APIModel):
    summary: TradebookSummaryOut
    trades: list[TradeOut]
    quote_errors: list[TradeQuoteErrorOut] = []


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
