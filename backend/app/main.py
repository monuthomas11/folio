from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from . import models, schemas
from .config import settings
from .database import Base, engine, get_db
from .routers import alerts, analysis, auth, holdings, integrations, watchlist
from .security import get_current_user


def _migrate_sqlite() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing:
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_cols:
                    continue
                col_type = column.type.compile(engine.dialect)
                conn.execute(
                    text(
                        f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}"
                    )
                )


def _migrate_postgres() -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE holdings ADD COLUMN IF NOT EXISTS "
                "one_day_change_pct NUMERIC(8, 4)"
            )
        )


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()
    _migrate_postgres()

    app = FastAPI(
        title="Folio API",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_origin,
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.url.path.startswith("/api/v1/"):
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    too_large = int(content_length) > settings.external_api_max_body_bytes
                except ValueError:
                    too_large = True
                if too_large:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body is too large"},
                    )
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/v1/"):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response

    app.include_router(auth.router)
    app.include_router(holdings.router)
    app.include_router(alerts.router)
    app.include_router(watchlist.router)
    app.include_router(integrations.router)
    app.include_router(analysis.router)
    app.include_router(analysis.profile_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/dashboard", response_model=schemas.SnapshotOut)
    def dashboard(
        user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        holdings = db.scalars(
            select(models.Holding)
            .where(models.Holding.user_id == user.id)
            .order_by(models.Holding.created_at.desc())
        ).all()
        active_alerts = db.scalars(
            select(models.Alert).where(
                models.Alert.user_id == user.id,
                models.Alert.dismissed.is_(False),
            )
        ).all()
        active_watchlist_alerts = db.scalars(
            select(models.WatchlistAlert).where(
                models.WatchlistAlert.user_id == user.id,
                models.WatchlistAlert.dismissed.is_(False),
            )
        ).all()

        portfolio_value = 0.0
        invested = 0.0
        holding_count = len(holdings)
        gainers = 0
        losers = 0
        for h in holdings:
            if h.current_ltp is None:
                continue
            value = float(h.quantity) * float(h.current_ltp)
            cost = float(h.quantity) * float(h.avg_buy_price)
            portfolio_value += value
            invested += cost
            if value >= cost:
                gainers += 1
            else:
                losers += 1

        total_pnl = portfolio_value - invested
        total_pnl_pct = (total_pnl / invested * 100) if invested > 0 else 0.0

        return schemas.SnapshotOut(
            summary=schemas.SummaryOut(
                portfolio_value=round(portfolio_value, 2),
                invested=round(invested, 2),
                total_pnl=round(total_pnl, 2),
                total_pnl_pct=round(total_pnl_pct, 2),
                holding_count=holding_count,
                active_alert_count=len(active_alerts) + len(active_watchlist_alerts),
                gainers=gainers,
                losers=losers,
            ),
            holdings=holdings,
            alerts=sorted(
                [*active_alerts, *active_watchlist_alerts],
                key=lambda alert: alert.created_at,
                reverse=True,
            ),
        )

    return app


app = create_app()
