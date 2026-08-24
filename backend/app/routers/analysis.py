import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import SessionLocal, get_db
from ..security import get_current_user
from ..services.analysis.orchestrator import (
    run_holding_analysis,
    run_portfolio_analysis,
)
from ..services.analysis.chat import (
    build_holding_chat_context,
    build_portfolio_chat_context,
    render_chat_prompt,
)
from ..services.llm.base import LLMProviderError
from ..services.llm.registry import get_llm_provider

router = APIRouter(prefix="/analysis", tags=["analysis"])
profile_router = APIRouter(prefix="/profile", tags=["profile"])


def _coerce_uuid(value: str, detail: str = "Not found") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


def _get_owned_holding(
    db: Session, user: models.User, holding_id: str
) -> models.Holding:
    holding = db.scalar(
        select(models.Holding).where(
            models.Holding.id == _coerce_uuid(holding_id),
            models.Holding.user_id == user.id,
        )
    )
    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )
    return holding


def _get_owned_run(db: Session, user: models.User, run_id: str) -> models.AnalysisRun:
    run = db.scalar(
        select(models.AnalysisRun).where(
            models.AnalysisRun.id == _coerce_uuid(run_id),
            models.AnalysisRun.user_id == user.id,
        )
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found",
        )
    return run


def _guard_new_run(db: Session, user: models.User, kind: str) -> None:
    active = db.scalar(
        select(models.AnalysisRun).where(
            models.AnalysisRun.user_id == user.id,
            models.AnalysisRun.status.in_(["CREATED", "RUNNING"]),
        )
    )
    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An analysis is already in progress for this account",
        )

    last = db.scalar(
        select(models.AnalysisRun)
        .where(
            models.AnalysisRun.user_id == user.id,
            models.AnalysisRun.kind == kind,
            models.AnalysisRun.status.in_(["COMPLETED", "PARTIAL_COMPLETION"]),
        )
        .order_by(models.AnalysisRun.completed_at.desc())
        .limit(1)
    )
    if last is not None and last.completed_at is not None:
        completed_at = last.completed_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - completed_at).total_seconds()
        if elapsed < settings.analysis_min_interval_seconds:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Please wait {int(settings.analysis_min_interval_seconds)} seconds "
                    "between analyses of the same kind"
                ),
            )


def _provider_meta() -> tuple[str, str | None]:
    try:
        provider = get_llm_provider()
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM provider misconfigured: {exc}",
        )
    return provider.provider_id, provider.model_name or None


@router.post("/chat", response_model=schemas.ChatResponse)
async def ask_ai_chat(
    payload: schemas.ChatRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        provider = get_llm_provider()
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM provider misconfigured: {exc}",
        )

    history = [
        {"role": m.role, "content": m.content} for m in payload.history
    ]

    if payload.context == "holding":
        if not payload.holdingId:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="holdingId is required when context is holding",
            )
        holding = _get_owned_holding(db, user, payload.holdingId)
        rec = db.scalar(
            select(models.Recommendation)
            .where(
                models.Recommendation.user_id == user.id,
                models.Recommendation.holding_id == holding.id,
                models.Recommendation.kind == "holding",
            )
            .order_by(models.Recommendation.created_at.desc())
            .limit(1)
        )
        if rec is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analysis available for this holding yet",
            )
        holdings = list(
            db.scalars(
                select(models.Holding).where(models.Holding.user_id == user.id)
            ).all()
        )
        profile = db.get(models.InvestmentProfile, user.id)
        if profile is None:
            profile = models.InvestmentProfile(user_id=user.id)
        context = await asyncio.to_thread(
            build_holding_chat_context, holding, rec, holdings, profile
        )
    else:
        portfolio_rec = db.scalar(
            select(models.Recommendation)
            .where(
                models.Recommendation.user_id == user.id,
                models.Recommendation.kind == "portfolio",
            )
            .order_by(models.Recommendation.created_at.desc())
            .limit(1)
        )
        holding_recs = db.scalars(
            select(models.Recommendation)
            .where(
                models.Recommendation.user_id == user.id,
                models.Recommendation.kind == "holding",
            )
            .order_by(models.Recommendation.created_at.desc())
        ).all()
        latest_by_symbol: dict[str, models.Recommendation] = {}
        for rec in holding_recs:
            latest_by_symbol.setdefault(rec.symbol, rec)
        if portfolio_rec is None and not latest_by_symbol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No portfolio analysis available yet",
            )
        holdings = list(
            db.scalars(
                select(models.Holding).where(models.Holding.user_id == user.id)
            ).all()
        )
        profile = db.get(models.InvestmentProfile, user.id)
        if profile is None:
            profile = models.InvestmentProfile(user_id=user.id)
        context = await asyncio.to_thread(
            build_portfolio_chat_context,
            portfolio_rec,
            list(latest_by_symbol.values()),
            holdings,
            profile,
        )

    prompt = render_chat_prompt(context, history, payload.message)
    try:
        reply = await provider.generate_text(
            system="You are Folio's financial chat assistant.",
            user=prompt,
            temperature=0.4,
            max_tokens=1024,
            json_mode=False,
        )
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chat request failed: {exc}",
        )

    return schemas.ChatResponse(
        reply=reply,
        provider=provider.provider_id,
        modelName=provider.model_name or None,
    )


@router.post("/holding/{holding_id}", response_model=schemas.StartedRunOut, status_code=202)
def start_holding_analysis(
    holding_id: str,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = _get_owned_holding(db, user, holding_id)
    _guard_new_run(db, user, "holding")
    provider_id, model_name = _provider_meta()

    run = models.AnalysisRun(
        user_id=user.id,
        kind="holding",
        holding_id=holding.id,
        status="CREATED",
        provider=provider_id,
        model_name=model_name,
        prompt_version="v1",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(run_holding_analysis, SessionLocal, run.id, holding.id)
    return schemas.StartedRunOut(run_id=run.id)


@router.post("/portfolio", response_model=schemas.StartedRunOut, status_code=202)
def start_portfolio_analysis(
    background_tasks: BackgroundTasks,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _guard_new_run(db, user, "portfolio")
    provider_id, model_name = _provider_meta()

    run = models.AnalysisRun(
        user_id=user.id,
        kind="portfolio",
        status="CREATED",
        provider=provider_id,
        model_name=model_name,
        prompt_version="v1",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(run_portfolio_analysis, SessionLocal, run.id)
    return schemas.StartedRunOut(run_id=run.id)


@router.get("/{run_id}")
def get_run(
    run_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = _get_owned_run(db, user, run_id)
    rec_ids = db.scalars(
        select(models.Recommendation.id).where(models.Recommendation.run_id == run.id)
    ).all()
    return {
        **schemas.AnalysisRunOut.model_validate(run).model_dump(by_alias=True),
        "recommendationIds": [str(r) for r in rec_ids],
    }


@router.get("/latest/holding/{holding_id}", response_model=schemas.RecommendationOut)
def latest_holding_analysis(
    holding_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = _get_owned_holding(db, user, holding_id)
    rec = db.scalar(
        select(models.Recommendation)
        .where(
            models.Recommendation.user_id == user.id,
            models.Recommendation.holding_id == holding.id,
            models.Recommendation.kind == "holding",
        )
        .order_by(models.Recommendation.created_at.desc())
        .limit(1)
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis available for this holding yet",
        )
    return rec


@router.get("/latest/portfolio", response_model=schemas.LatestPortfolioAnalysisOut)
def latest_portfolio_analysis(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    portfolio_rec = db.scalar(
        select(models.Recommendation)
        .where(
            models.Recommendation.user_id == user.id,
            models.Recommendation.kind == "portfolio",
        )
        .order_by(models.Recommendation.created_at.desc())
        .limit(1)
    )

    holding_recs = db.scalars(
        select(models.Recommendation)
        .where(
            models.Recommendation.user_id == user.id,
            models.Recommendation.kind == "holding",
        )
        .order_by(models.Recommendation.created_at.desc())
    ).all()

    latest_by_symbol: dict[str, models.Recommendation] = {}
    for rec in holding_recs:
        latest_by_symbol.setdefault(rec.symbol, rec)

    if portfolio_rec is None and not latest_by_symbol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No portfolio analysis available yet",
        )

    last_run = db.scalar(
        select(models.AnalysisRun)
        .where(models.AnalysisRun.user_id == user.id)
        .order_by(models.AnalysisRun.created_at.desc())
        .limit(1)
    )
    return schemas.LatestPortfolioAnalysisOut(
        portfolio=portfolio_rec,
        holdings=list(latest_by_symbol.values()),
        last_run=last_run,
    )


@profile_router.get("", response_model=schemas.InvestmentProfileOut)
def get_profile(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(models.InvestmentProfile, user.id)
    if profile is None:
        profile = models.InvestmentProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@profile_router.put("", response_model=schemas.InvestmentProfileOut)
def update_profile(
    payload: schemas.InvestmentProfileIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(models.InvestmentProfile, user.id)
    if profile is None:
        profile = models.InvestmentProfile(user_id=user.id)
        db.add(profile)

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if value is not None:
            setattr(profile, key, value)
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
