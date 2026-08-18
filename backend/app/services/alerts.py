from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


def evaluate_and_create_alerts(db: Session, holding: models.Holding) -> None:
    if holding.current_ltp is None:
        return

    if holding.stop_loss is not None and holding.current_ltp <= holding.stop_loss:
        _create_alert_if_absent(db, holding, "sl-hit")

    if holding.target_price is not None and holding.current_ltp >= holding.target_price:
        _create_alert_if_absent(db, holding, "target-hit")


def _create_alert_if_absent(
    db: Session, holding: models.Holding, kind: str
) -> None:
    exists = db.scalar(
        select(models.Alert).where(
            models.Alert.holding_id == holding.id,
            models.Alert.kind == kind,
            models.Alert.dismissed.is_(False),
        )
    )
    if exists is not None:
        return

    if kind == "sl-hit":
        message = (
            f"{holding.symbol} hit its stop-loss at "
            f"{holding.current_ltp:.2f} (SL {holding.stop_loss:.2f})"
        )
    else:
        message = (
            f"{holding.symbol} reached its target at "
            f"{holding.current_ltp:.2f} (target {holding.target_price:.2f})"
        )

    db.add(
        models.Alert(
            user_id=holding.user_id,
            holding_id=holding.id,
            symbol=holding.symbol,
            kind=kind,
            price=holding.current_ltp,
            message=message,
        )
    )