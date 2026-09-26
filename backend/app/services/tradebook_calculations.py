from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .. import models

ZERO = Decimal("0")
MONEY = Decimal("0.01")
CHARGE_FIELDS = (
    "brokerage",
    "stt_ctt",
    "exchange_transaction",
    "sebi",
    "gst",
    "stamp_duty",
    "ipft",
    "other",
)


def decimal_value(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def zero_if_none(value: object | None) -> Decimal:
    return decimal_value(value) or ZERO


def money(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def number(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def is_fno(trade: models.Trade) -> bool:
    return (trade.asset_class or "equity") == "fno"


def entry_units(trade: models.Trade) -> Decimal:
    if is_fno(trade):
        return Decimal(trade.entry_lots or 0) * Decimal(trade.lot_size or 0)
    return zero_if_none(trade.entry_quantity)


def exit_units(trade: models.Trade, item: models.TradeExit) -> Decimal:
    if is_fno(trade) and item.exit_lots is not None:
        return Decimal(item.exit_lots) * Decimal(trade.lot_size or 0)
    return zero_if_none(item.quantity)


def exited_units(trade: models.Trade) -> Decimal:
    return sum((exit_units(trade, item) for item in trade.exits), ZERO)


def remaining_units(trade: models.Trade) -> Decimal:
    return max(ZERO, entry_units(trade) - exited_units(trade))


def signed_pnl(trade: models.Trade, entry: Decimal, exit: Decimal, units: Decimal) -> Decimal:
    delta = exit - entry
    return delta * units if trade.side == "long" else -delta * units


def charge_complete(charge: models.TradeCharge | None) -> bool:
    return charge is not None and all(
        decimal_value(getattr(charge, field)) is not None for field in CHARGE_FIELDS
    )


def charge_total(charge: models.TradeCharge | None) -> Decimal | None:
    if not charge_complete(charge):
        return None
    return sum((zero_if_none(getattr(charge, field)) for field in CHARGE_FIELDS), ZERO)


def charge_out(charge: models.TradeCharge | None) -> dict | None:
    if charge is None:
        return None
    total = charge_total(charge)
    return {
        "id": charge.id,
        "leg_type": charge.leg_type,
        "brokerage": number(decimal_value(charge.brokerage)),
        "stt_ctt": number(decimal_value(charge.stt_ctt)),
        "exchange_transaction": number(decimal_value(charge.exchange_transaction)),
        "sebi": number(decimal_value(charge.sebi)),
        "gst": number(decimal_value(charge.gst)),
        "stamp_duty": number(decimal_value(charge.stamp_duty)),
        "ipft": number(decimal_value(charge.ipft)),
        "other": number(decimal_value(charge.other)),
        "contract_note_ref": charge.contract_note_ref,
        "total": money(total),
        "complete": charge_complete(charge),
    }


def entry_charge(trade: models.Trade) -> models.TradeCharge | None:
    for charge in trade.charges:
        if charge.leg_type == "entry" and charge.trade_exit_id is None:
            return charge
    return None


@dataclass
class TradeCalculation:
    row: dict
    gross_realized: Decimal
    gross_unrealized: Decimal | None
    gross_total: Decimal | None
    net_realized: Decimal | None
    net_unrealized: Decimal | None
    net_total: Decimal | None
    total_charges: Decimal | None
    open_exposure: Decimal | None
    charges_complete: bool
    status: str


def calculate_trade(trade: models.Trade) -> TradeCalculation:
    entry_price = zero_if_none(trade.entry_price)
    units = entry_units(trade)
    exited = exited_units(trade)
    remaining = remaining_units(trade)
    entry_cost = entry_price * units
    entry_charge_record = entry_charge(trade)
    entry_costs = charge_total(entry_charge_record)
    is_legacy_equity = not is_fno(trade) and entry_charge_record is None and not trade.charges
    gross_realized = ZERO
    exit_charge_total = ZERO
    exits_complete = True
    exit_rows: list[dict] = []

    for item in trade.exits:
        quantity = exit_units(trade, item)
        exit_price = zero_if_none(item.exit_price)
        gross = signed_pnl(trade, entry_price, exit_price, quantity)
        charge = item.charges[0] if item.charges else None
        charges = charge_total(charge)
        allocated_entry_charge = (
            entry_costs * quantity / units
            if entry_costs is not None and units > ZERO
            else ZERO if is_legacy_equity else None
        )
        if charges is None:
            exits_complete = False
        else:
            exit_charge_total += charges
        gross_realized += gross
        exit_rows.append(
            {
                "id": item.id,
                "quantity": number(quantity),
                "exit_lots": item.exit_lots,
                "exit_price": number(exit_price),
                "exit_date": item.exit_date,
                "exit_at": item.exit_at,
                "exit_reason": item.exit_reason,
                "exit_order_id": item.exit_order_id,
                "exit_contract_note_ref": item.exit_contract_note_ref,
                "notes": item.notes,
                "realized_pnl": money(gross),
                "gross_realized_pnl": money(gross),
                "net_realized_pnl": money(gross - allocated_entry_charge - charges)
                if allocated_entry_charge is not None and charges is not None
                else money(gross) if is_legacy_equity
                else None,
                "charges": charge_out(charge),
            }
        )

    gross_unrealized: Decimal | None = None
    if remaining > ZERO and trade.current_ltp is not None:
        gross_unrealized = signed_pnl(
            trade, entry_price, zero_if_none(trade.current_ltp), remaining
        )
    gross_total = (
        gross_realized + gross_unrealized
        if gross_unrealized is not None
        else None
    )

    charges_complete = (
        is_legacy_equity
        or (entry_costs is not None and exits_complete)
    )
    allocated_entry_exited = (
        entry_costs * exited / units if entry_costs is not None and units > ZERO else ZERO
    )
    allocated_entry_remaining = (
        entry_costs * remaining / units if entry_costs is not None and units > ZERO else ZERO
    )
    known_exit_costs = exit_charge_total if exits_complete else None

    if is_legacy_equity:
        net_realized = gross_realized
        net_unrealized = gross_unrealized
    elif entry_costs is not None and known_exit_costs is not None:
        net_realized = gross_realized - allocated_entry_exited - known_exit_costs
        net_unrealized = (
            gross_unrealized - allocated_entry_remaining
            if gross_unrealized is not None
            else None
        )
    else:
        net_realized = None
        net_unrealized = None

    net_total = (
        net_realized + net_unrealized
        if net_realized is not None and net_unrealized is not None
        else (net_realized if remaining == ZERO and net_realized is not None else None)
    )
    total_charges = (
        (entry_costs or ZERO) + (known_exit_costs or ZERO)
        if charges_complete
        else None
    )
    capital_basis = None
    if is_fno(trade):
        if trade.instrument_type == "future":
            capital_basis = decimal_value(trade.margin_used)
        else:
            capital_basis = entry_cost + (entry_costs or ZERO)
    else:
        capital_basis = entry_cost
    open_exposure = (
        zero_if_none(trade.current_ltp) * remaining
        if remaining > ZERO and trade.current_ltp is not None
        else ZERO if remaining == ZERO
        else None
    )

    remaining_lots = None
    if is_fno(trade):
        remaining_lots = int(remaining / Decimal(trade.lot_size or 1))

    row = {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "asset_class": trade.asset_class or "equity",
        "instrument_type": trade.instrument_type or "equity",
        "exchange": trade.exchange,
        "underlying_type": trade.underlying_type,
        "underlying_symbol": trade.underlying_symbol,
        "contract_symbol": trade.contract_symbol,
        "expiry_date": trade.expiry_date,
        "strike_price": number(decimal_value(trade.strike_price)),
        "tick_size": number(decimal_value(trade.tick_size)),
        "option_type": trade.option_type,
        "lot_size": trade.lot_size,
        "entry_lots": trade.entry_lots,
        "remaining_lots": remaining_lots,
        "entry_at": trade.entry_at,
        "entry_order_id": trade.entry_order_id,
        "entry_contract_note_ref": trade.entry_contract_note_ref,
        "strategy": trade.strategy,
        "thesis": trade.thesis,
        "settlement_type": trade.settlement_type,
        "product_type": trade.product_type,
        "margin_used": money(decimal_value(trade.margin_used)),
        "entry_date": trade.entry_date,
        "entry_quantity": number(units),
        "entry_price": number(entry_price),
        "broker": trade.broker,
        "notes": trade.notes,
        "current_ltp": number(decimal_value(trade.current_ltp)),
        "mark_source": trade.mark_source,
        "last_updated": trade.last_updated,
        "remaining_quantity": number(remaining),
        "gross_entry_value": money(entry_cost),
        "gross_realized_pnl": money(gross_realized),
        "gross_unrealized_pnl": money(gross_unrealized),
        "gross_total_pnl": money(gross_total),
        "net_realized_pnl": money(net_realized),
        "net_unrealized_pnl": money(net_unrealized),
        "net_total_pnl": money(net_total),
        "entry_charges": money(entry_costs),
        "entry_charge": charge_out(entry_charge_record),
        "exit_charges": money(known_exit_costs),
        "total_charges": money(total_charges),
        "charges_complete": charges_complete,
        "capital_basis": money(capital_basis),
        "open_exposure": money(open_exposure),
        "status": "closed" if remaining == ZERO else "open",
        "realized_pnl": money(gross_realized),
        "unrealized_pnl": money(gross_unrealized),
        "total_pnl": money(gross_total),
        "exits": exit_rows,
    }
    return TradeCalculation(
        row=row,
        gross_realized=gross_realized,
        gross_unrealized=gross_unrealized,
        gross_total=gross_total,
        net_realized=net_realized,
        net_unrealized=net_unrealized,
        net_total=net_total,
        total_charges=total_charges,
        open_exposure=open_exposure,
        charges_complete=charges_complete,
        status=row["status"],
    )


def calculate_summary(calculations: list[TradeCalculation]) -> dict:
    gross_realized = sum((item.gross_realized for item in calculations), ZERO)
    priced_open = [
        item for item in calculations if item.status == "open" and item.gross_unrealized is not None
    ]
    open_items = [item for item in calculations if item.status == "open"]
    gross_unrealized = (
        sum((item.gross_unrealized for item in priced_open if item.gross_unrealized is not None), ZERO)
        if priced_open
        else None
    )
    gross_total = (
        gross_realized + gross_unrealized
        if len(priced_open) == len(open_items) and gross_unrealized is not None
        else (gross_realized if not open_items else None)
    )
    net_realized_values = [item.net_realized for item in calculations]
    net_unrealized_values = [
        item.net_unrealized for item in priced_open
    ]
    net_realized = (
        sum((item for item in net_realized_values if item is not None), ZERO)
        if all(item is not None for item in net_realized_values)
        else None
    )
    net_unrealized = (
        sum((item for item in net_unrealized_values if item is not None), ZERO)
        if len(net_unrealized_values) == len(priced_open) and priced_open
        else None
    )
    net_total = (
        net_realized + net_unrealized
        if net_realized is not None and len(priced_open) == len(open_items) and net_unrealized is not None
        else (net_realized if net_realized is not None and not open_items else None)
    )
    complete_charges = [item for item in calculations if item.charges_complete]
    total_charges = (
        sum((item.total_charges or ZERO for item in complete_charges), ZERO)
        if len(complete_charges) == len(calculations)
        else None
    )
    open_exposures = [item.open_exposure for item in open_items]
    open_exposure = (
        sum((value for value in open_exposures if value is not None), ZERO)
        if all(value is not None for value in open_exposures)
        else None
    )
    closed = [item for item in calculations if item.status == "closed"]
    win_rate = None
    if closed and all(item.net_total is not None for item in closed):
        wins = sum(1 for item in closed if item.net_total is not None and item.net_total > ZERO)
        win_rate = Decimal(wins) / Decimal(len(closed)) * Decimal("100")
    return {
        "trade_count": len(calculations),
        "open_count": len(open_items),
        "closed_count": len(closed),
        "realized_pnl": money(gross_realized),
        "unrealized_pnl": money(gross_unrealized),
        "total_pnl": money(gross_total),
        "unpriced_open_count": len(open_items) - len(priced_open),
        "gross_realized_pnl": money(gross_realized),
        "gross_unrealized_pnl": money(gross_unrealized),
        "gross_total_pnl": money(gross_total),
        "net_realized_pnl": money(net_realized),
        "net_unrealized_pnl": money(net_unrealized),
        "net_total_pnl": money(net_total),
        "total_charges": money(total_charges),
        "open_exposure": money(open_exposure),
        "incomplete_charge_count": sum(1 for item in calculations if not item.charges_complete),
        "win_rate": money(win_rate),
    }
