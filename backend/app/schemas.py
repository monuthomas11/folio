import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    last_updated: datetime | None
    created_at: datetime


class PriceOut(APIModel):
    symbol: str
    ltp: float
    last_updated: datetime


class AlertOut(APIModel):
    id: uuid.UUID
    holding_id: uuid.UUID
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


class SnapshotOut(BaseModel):
    summary: SummaryOut
    holdings: list[HoldingOut]
    alerts: list[AlertOut]


class ImportRowError(BaseModel):
    row: int
    message: str


class ImportResult(BaseModel):
    created: int
    errors: list[ImportRowError]


class HoldingsImportIn(BaseModel):
    csv: str


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


class LatestPortfolioAnalysisOut(BaseModel):
    portfolio: RecommendationOut | None
    holdings: list[RecommendationOut]


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
