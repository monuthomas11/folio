from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .. import models


def _is_triggered(level: models.WatchlistLevel, ltp: float) -> bool:
    if level.upper_price is not None:
        return float(level.lower_price) <= ltp <= float(level.upper_price)
    if level.kind == "target":
        return ltp >= float(level.lower_price)
    return ltp <= float(level.lower_price)


def _alert_kind(level: models.WatchlistLevel) -> str:
    return {
        "entry": "entry-reached",
        "target": "target-reached",
        "stop-loss": "stop-loss-hit",
        "invalidation": "invalidation-hit",
    }[level.kind]


def _level_text(level: models.WatchlistLevel) -> str:
    if level.upper_price is None:
        return f"₹{float(level.lower_price):.2f}"
    return f"₹{float(level.lower_price):.2f}–₹{float(level.upper_price):.2f}"


def evaluate_watchlist_item(db: Session, item: models.WatchlistItem) -> None:
    if item.current_ltp is None:
        return
    ltp = float(item.current_ltp)
    for level in item.levels:
        triggered = _is_triggered(level, ltp)
        if triggered and not level.condition_met:
            verb = {
                "entry": "reached an entry level",
                "target": "reached a target",
                "stop-loss": "hit a stop-loss",
                "invalidation": "hit an invalidation level",
            }[level.kind]
            db.add(
                models.WatchlistAlert(
                    user_id=item.user_id,
                    watchlist_item_id=item.id,
                    watchlist_level_id=level.id,
                    symbol=item.symbol,
                    kind=_alert_kind(level),
                    price=item.current_ltp,
                    message=f"{item.symbol} {verb} at ₹{ltp:.2f} ({_level_text(level)})",
                )
            )
        level.condition_met = triggered


def update_watchlist_items(
    db: Session,
    items: list[models.WatchlistItem],
    prices: dict[str, float],
    updated_at: datetime | None = None,
) -> None:
    timestamp = updated_at or datetime.now(timezone.utc)
    for item in items:
        price = prices.get(item.symbol)
        if price is None:
            continue
        item.current_ltp = price
        item.last_updated = timestamp
        evaluate_watchlist_item(db, item)
