from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ... import models
from ..fundamentals.base import FundamentalsProvider, FundamentalsSnapshot
from ..fundamentals.yfinance_provider import YFinanceFundamentalsProvider
from ..llm.base import LLMProvider, LLMProviderError
from ..llm.registry import get_llm_provider
from ..market_data.base import MarketDataProvider, OHLCV
from ..market_data.yfinance_provider import YFinanceMarketDataProvider
from ..technicals.indicators import build_technical_snapshot
from .evidence import build_evidence_pack
from .prompts import get_system_prompt, render_agent_prompt

TERMINAL_STATUSES = {"COMPLETED", "PARTIAL_COMPLETION", "FAILED"}

MARKET_DATA: MarketDataProvider = YFinanceMarketDataProvider()
FUNDAMENTALS: FundamentalsProvider = YFinanceFundamentalsProvider()
PROVIDER_FACTORY = get_llm_provider

FUNDAMENTAL_RATING_GROUPS = {"BUY", "HOLD", "REDUCE", "EXIT"}
FUNDAMENTAL_ACTIONS = {
    "BUY_ON_DIPS",
    "BUY_ACCUMULATE",
    "HOLD_WAIT_FOR_TRIGGER",
    "HOLD_ADD_ON_CONFIRMATION",
    "HOLD_MONITOR",
    "REDUCE_ON_STRENGTH",
    "REDUCE_TO_LIMIT",
    "TRIM_LOSERS",
    "EXIT_POSITION",
    "EXIT_ON_BREACH",
}
THESIS_STATUSES = {"VALID", "STRENGTHENING", "WEAKENING", "INVALIDATED", "UNKNOWN"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StageError(Exception):
    pass


class _RunContext:
    def __init__(
        self,
        session_factory,
        run_id: uuid.UUID,
        provider: LLMProvider,
    ):
        self.session_factory = session_factory
        self.run_id = run_id
        self.provider = provider

    def _with_run(self, action) -> None:
        with self.session_factory() as session:
            run = session.get(models.AnalysisRun, self.run_id)
            if run is None:
                return
            action(session, run)
            session.commit()

    def set_stage(self, stage: str) -> None:
        def _apply(session: Session, run: models.AnalysisRun) -> None:
            run.status = "RUNNING"
            run.stage = stage

        self._with_run(_apply)

    def finish(self, status: str, error_message: str | None = None) -> None:
        def _apply(session: Session, run: models.AnalysisRun) -> None:
            run.status = status
            run.stage = None
            run.error_message = error_message
            run.completed_at = _now()

        self._with_run(_apply)

    async def run_agent(
        self, agent: str, evidence_pack: dict, extra: dict | None = None
    ) -> dict:
        prompt = render_agent_prompt(agent, evidence_pack, extra)
        try:
            return await self.provider.generate_json(get_system_prompt(), prompt)
        except LLMProviderError as exc:
            raise StageError(f"{agent} agent failed: {exc}") from exc


def _gather_symbol_data(
    symbol: str,
) -> tuple[list[OHLCV], FundamentalsSnapshot | None]:
    try:
        bars = MARKET_DATA.get_ohlcv(symbol)
    except Exception:
        bars = []
    try:
        fund = FUNDAMENTALS.get_snapshot(symbol)
    except Exception:
        fund = None
    return bars, fund


async def _refresh_holding_ltp(session: Session, holding: models.Holding) -> None:
    try:
        ltp = await asyncio.to_thread(MARKET_DATA.get_ltp, holding.symbol)
    except Exception:
        return
    holding.current_ltp = ltp
    holding.last_updated = _now()
    session.commit()


def _persist_recommendation(
    session: Session,
    run: models.AnalysisRun,
    holding: models.Holding | None,
    kind: str,
    symbol: str,
    output: dict,
    quality_flags: list[str],
    analysis_timestamps: dict,
    evidence_items: list | None = None,
    portfolio_weight: float | None = None,
) -> models.Recommendation:
    scores = output.get("scores")
    if not isinstance(scores, dict):
        scores = None
    fair = output.get("fair_value_range")
    if not isinstance(fair, dict):
        fair = None

    recommendation_values = {
        "run_id": run.id,
        "user_id": run.user_id,
        "holding_id": holding.id if holding else None,
        "kind": kind,
        "symbol": symbol,
        "rating": str(output.get("rating") or "HOLD"),
        "action": str(output.get("action") or "HOLD_MONITOR"),
        "confidence": output.get("confidence"),
        "scores": scores,
        "portfolio_weight": portfolio_weight,
        "thesis_status": output.get("thesis_status"),
        "summary": str(output.get("summary") or ""),
        "why": output.get("why"),
        "bull_case": output.get("bull_case"),
        "base_case": output.get("base_case"),
        "bear_case": output.get("bear_case"),
        "key_reasons": _str_list(output.get("key_reasons")),
        "key_risks": _str_list(output.get("key_risks")),
        "buy_conditions": _str_list(output.get("buy_conditions")),
        "reduce_conditions": _str_list(output.get("reduce_conditions")),
        "exit_conditions": _str_list(output.get("exit_conditions")),
        "support_levels": _float_list(output.get("support_levels")),
        "resistance_levels": _float_list(output.get("resistance_levels")),
        "fair_value_range": fair,
        "evidence_ids": _str_list(output.get("evidence_ids")),
        "evidence": evidence_items,
        "data_quality": str(output.get("_data_quality") or "MODERATE"),
        "quality_flags": _str_list(output.get("_quality_flags") or quality_flags),
        "health_score": output.get("health_score"),
        "positives": _str_list(output.get("positives")),
        "concerns": _str_list(output.get("concerns")),
        "priority_note": output.get("priority"),
        "analysis_timestamps": analysis_timestamps,
    }

    query = select(models.Recommendation).where(
        models.Recommendation.user_id == run.user_id,
        models.Recommendation.kind == kind,
    )
    if holding is None:
        query = query.where(models.Recommendation.holding_id.is_(None))
    else:
        query = query.where(models.Recommendation.holding_id == holding.id)
    existing = session.scalars(
        query.order_by(
            models.Recommendation.created_at.desc(),
            models.Recommendation.id.desc(),
        )
    ).all()

    if existing:
        rec = existing[0]
        for stale in existing[1:]:
            session.delete(stale)
        for field, value in recommendation_values.items():
            setattr(rec, field, value)
    else:
        rec = models.Recommendation(**recommendation_values)
        session.add(rec)
    session.commit()
    return rec


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if v is not None and str(v).strip()]


def _float_list(value: object) -> list[float]:
    result: list[float] = []
    if not isinstance(value, list):
        return result
    for v in value:
        try:
            result.append(float(v))
        except (TypeError, ValueError):
            continue
    return result


async def _analyze_single_holding(
    ctx: _RunContext,
    session: Session,
    run: models.AnalysisRun,
    holding: models.Holding,
    holdings: list[models.Holding],
    profile: models.InvestmentProfile,
) -> models.Recommendation:
    ctx.set_stage("FETCHING_MARKET_DATA")
    await _refresh_holding_ltp(session, holding)
    bars, fund = await asyncio.to_thread(_gather_symbol_data, holding.symbol)

    ctx.set_stage("PROCESSING_TECHNICALS")
    tech = build_technical_snapshot(holding.symbol, bars)

    ctx.set_stage("BUILDING_EVIDENCE")
    pack, builder, quality = build_evidence_pack(holding, holdings, tech, fund, profile)
    gates = quality.gates
    quality_grade = quality.grade
    pack_with_quality = dict(pack)
    pack_with_quality["evidence_pack_quality_grade"] = quality_grade

    ctx.set_stage("ANALYZING_STOCK")
    fundamental_out = await ctx.run_agent("fundamental", pack_with_quality)
    technical_out = await ctx.run_agent("technical", pack_with_quality)

    ctx.set_stage("PORTFOLIO_CONTEXT")
    portfolio_out = await ctx.run_agent("portfolio", pack_with_quality)

    ctx.set_stage("FINAL_RECONCILIATION")
    committee_out = await ctx.run_agent(
        "committee",
        pack_with_quality,
        extra={
            "mode": "holding",
            "agent_outputs": {
                "fundamental": fundamental_out,
                "technical": technical_out,
                "portfolio": portfolio_out,
            },
        },
    )

    rating = str(committee_out.get("rating") or "HOLD").upper()
    if rating not in FUNDAMENTAL_RATING_GROUPS:
        rating = "HOLD"
    action = str(committee_out.get("action") or "HOLD_MONITOR").upper()
    if action not in FUNDAMENTAL_ACTIONS:
        action = "HOLD_MONITOR"
    thesis = str(committee_out.get("thesis_status") or "UNKNOWN").upper()
    if thesis not in THESIS_STATUSES:
        thesis = "UNKNOWN"

    committee_out["rating"] = rating
    committee_out["action"] = action
    committee_out["thesis_status"] = thesis
    committee_out["_data_quality"] = quality_grade
    committee_out["_quality_flags"] = gates

    now = _now().isoformat()
    return _persist_recommendation(
        session,
        run,
        holding,
        "holding",
        holding.symbol,
        committee_out,
        gates,
        {
            "generated_at": now,
            "market_data_through": now,
            "note": "LTP and fundamentals observed via yfinance at generation time.",
        },
        [item.model_dump() for item in builder.items],
        pack.get("position", {}).get("portfolio_weight_pct"),
    )


def _get_or_create_profile(
    session: Session, user_id: uuid.UUID
) -> models.InvestmentProfile:
    profile = session.get(models.InvestmentProfile, user_id)
    if profile is None:
        profile = models.InvestmentProfile(user_id=user_id)
        session.add(profile)
        session.commit()
    return profile


async def run_holding_analysis(
    session_factory, run_id: uuid.UUID, holding_id: uuid.UUID
) -> None:
    try:
        provider = PROVIDER_FACTORY()
    except Exception as exc:
        with session_factory() as session:
            run = session.get(models.AnalysisRun, run_id)
            if run is not None:
                run.status = "FAILED"
                run.stage = None
                run.error_message = f"LLM provider misconfigured: {exc}"
                run.completed_at = _now()
                session.commit()
        return
    ctx = _RunContext(session_factory, run_id, provider)

    with session_factory() as session:
        run = session.get(models.AnalysisRun, run_id)
        if run is None:
            return
        if run.kind != "holding":
            run.status = "FAILED"
            run.stage = None
            run.error_message = "Invalid analysis run kind"
            run.completed_at = _now()
            session.commit()
            return
        holding = session.get(models.Holding, holding_id)
        if holding is None or holding.user_id != run.user_id:
            ctx.finish("FAILED", "Holding not found for analysis run")
            return
        profile = _get_or_create_profile(session, run.user_id)
        holdings = list(
            session.scalars(
                select(models.Holding).where(models.Holding.user_id == run.user_id)
            ).all()
        )
        run.status = "RUNNING"
        run.started_at = _now()
        session.commit()

    try:
        with session_factory() as session:
            run = session.get(models.AnalysisRun, run_id)
            holding = session.get(models.Holding, holding_id)
            profile = _get_or_create_profile(session, run.user_id)
            holdings = list(
                session.scalars(
                    select(models.Holding).where(models.Holding.user_id == run.user_id)
                ).all()
            )
            await _analyze_single_holding(ctx, session, run, holding, holdings, profile)
        ctx.finish("COMPLETED")
    except StageError as exc:
        ctx.finish("FAILED", str(exc))
    except Exception as exc:
        ctx.finish("FAILED", f"Analysis failed: {exc}")


async def run_portfolio_analysis(
    session_factory, run_id: uuid.UUID
) -> None:
    try:
        provider = PROVIDER_FACTORY()
    except Exception as exc:
        with session_factory() as session:
            run = session.get(models.AnalysisRun, run_id)
            if run is not None:
                run.status = "FAILED"
                run.stage = None
                run.error_message = f"LLM provider misconfigured: {exc}"
                run.completed_at = _now()
                session.commit()
        return
    ctx = _RunContext(session_factory, run_id, provider)

    with session_factory() as session:
        run = session.get(models.AnalysisRun, run_id)
        if run is None:
            return
        if run.kind != "portfolio":
            run.status = "FAILED"
            run.stage = None
            run.error_message = "Invalid analysis run kind"
            run.completed_at = _now()
            session.commit()
            return
        holdings = list(
            session.scalars(
                select(models.Holding).where(models.Holding.user_id == run.user_id)
            ).all()
        )
        if not holdings:
            ctx.finish("FAILED", "No holdings to analyze")
            return
        profile = _get_or_create_profile(session, run.user_id)
        run.status = "RUNNING"
        run.started_at = _now()
        session.commit()

    errors: list[str] = []
    rating_map: dict[str, dict] = {}
    try:
        with session_factory() as session:
            run = session.get(models.AnalysisRun, run_id)
            holdings = list(
                session.scalars(
                    select(models.Holding).where(models.Holding.user_id == run.user_id)
                ).all()
            )
            profile = _get_or_create_profile(session, run.user_id)
            for holding in holdings:
                try:
                    rec = await _analyze_single_holding(
                        ctx, session, run, holding, holdings, profile
                    )
                    rating_map[holding.symbol] = {
                        "rating": rec.rating,
                        "action": rec.action,
                        "confidence": rec.confidence,
                    }
                except Exception as exc:
                    errors.append(f"{holding.symbol}: {exc}")

            ctx.set_stage("FINAL_RECONCILIATION")
            portfolio_pack, portfolio_quality = _build_portfolio_pack(
                holdings, profile, rating_map
            )
            try:
                committee_out = await ctx.run_agent(
                    "committee", portfolio_pack, extra={"mode": "portfolio"}
                )
            except StageError as exc:
                errors.append(f"portfolio summary: {exc}")
                committee_out = {
                    "health_score": None,
                    "positives": [],
                    "concerns": [str(e) for e in errors],
                    "priority": "Portfolio analysis incomplete; review individual results.",
                    "summary": "Portfolio-level summary could not be generated.",
                }

            now = _now().isoformat()
            _persist_recommendation(
                session,
                run,
                None,
                "portfolio",
                "PORTFOLIO",
                {**committee_out, "rating": "HOLD", "action": "HOLD_MONITOR"},
                portfolio_quality["gates"],
                {
                    "generated_at": now,
                    "market_data_through": now,
                    "note": "LTP and fundamentals observed via yfinance at generation time.",
                },
            )
    except Exception as exc:
        ctx.finish("FAILED", f"Portfolio analysis failed: {exc}")
        return

    if errors:
        ctx.finish("PARTIAL_COMPLETION", "; ".join(errors)[:2000])
    else:
        ctx.finish("COMPLETED")


def _build_portfolio_pack(
    holdings: list[models.Holding],
    profile: models.InvestmentProfile,
    rating_map: dict[str, dict],
) -> tuple[dict, dict]:
    total_value = 0.0
    values: dict[str, float] = {}
    for h in holdings:
        value = (
            float(h.quantity) * float(h.current_ltp) if h.current_ltp is not None else 0.0
        )
        total_value += value
        values[h.symbol] = value

    stock_rows = []
    gates: set[str] = set()
    for h in holdings:
        weight = values[h.symbol] / total_value * 100.0 if total_value else 0.0
        verdict = rating_map.get(h.symbol, {})
        stock_rows.append(
            {
                "symbol": h.symbol,
                "weight_pct": round(weight, 2),
                "rating": verdict.get("rating"),
                "action": verdict.get("action"),
                "confidence": verdict.get("confidence"),
            }
        )
        if weight >= float(profile.max_single_stock_weight):
            gates.add("PORTFOLIO_CONCENTRATION")

    quality = {
        "score": None,
        "grade": "MODERATE",
        "gates": sorted(gates),
    }
    pack = {
        "mode": "portfolio",
        "investment_profile": {
            "investment_style": profile.investment_style,
            "risk_tolerance": profile.risk_tolerance,
            "investment_horizon": profile.investment_horizon,
            "max_single_stock_weight_pct": float(profile.max_single_stock_weight),
            "max_sector_weight_pct": float(profile.max_sector_weight),
        },
        "portfolio_summary": {
            "total_value": round(total_value, 2),
            "holding_count": len(holdings),
            "positions": stock_rows,
        },
    }
    return pack, quality
