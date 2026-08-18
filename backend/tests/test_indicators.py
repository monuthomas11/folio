from datetime import date, timedelta

from app.services.market_data.base import OHLCV
from app.services.technicals.indicators import (
    atr,
    build_technical_snapshot,
    drawdown_from_52w_high,
    ema,
    macd,
    rsi,
    sma,
    support_resistance,
)


def test_sma():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert sma(values, 3) == [None, None, 2.0, 3.0, 4.0]


def test_ema_span_one_matches_values():
    values = [1.0, 2.0, 3.0, 4.0]
    assert ema(values, 1) == values


def test_ema_constant_series_stays_constant():
    values = [5.0] * 10
    result = ema(values, 3)
    assert result[-1] == 5.0


def test_rsi_increasing_series_is_100():
    assert rsi([float(i) for i in range(1, 40)]) == 100.0


def test_rsi_decreasing_series_is_0():
    assert rsi([float(i) for i in range(40, 1, -1)]) == 0.0


def test_rsi_constant_series_is_100():
    assert rsi([5.0] * 40) == 100.0


def test_rsi_known_series():
    closes = [10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0]
    assert round(rsi(closes, period=3), 2) == 59.13


def test_rsi_wilder_classic_series():
    closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84]
    closes += [46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41]
    closes += [46.22, 45.64, 46.21, 46.25, 45.71, 46.45, 45.78, 45.35, 44.03]
    closes += [44.18, 44.22, 44.57, 43.42, 42.66, 43.13]
    assert round(rsi(closes), 2) == 37.79


def test_macd_constant_series_is_zero():
    closes = [10.0] * 60
    line, signal, hist = macd(closes)
    assert line == 0.0
    assert signal == 0.0
    assert hist == 0.0


def test_macd_too_short_returns_none():
    assert macd([1.0, 2.0, 3.0]) == (None, None, None)


def _bars(closes, high_low_gap=0.0):
    bars = []
    start = date(2024, 1, 1)
    for i, close in enumerate(closes):
        high = close + high_low_gap
        low = close - high_low_gap
        bars.append(
            OHLCV(
                date=start + timedelta(days=i),
                open=close,
                high=high,
                low=low,
                close=close,
                volume=1000.0,
            )
        )
    return bars


def test_atr_constant_range():
    bars = _bars([100.0 + i * 0.1 for i in range(30)], high_low_gap=1.0)
    assert atr(bars) == 2.0


def test_atr_short_series_returns_none():
    assert atr(_bars([100.0] * 5)) is None


def test_support_resistance_basic():
    bars = []
    start = date(2024, 1, 1)
    for i in range(100):
        close = 100.0 + (i % 10)
        bars.append(
            OHLCV(
                date=start + timedelta(days=i),
                open=close,
                high=close + 5.0,
                low=close - 5.0,
                close=close,
                volume=1000.0,
            )
        )
    supports, resistances = support_resistance(bars)
    assert isinstance(supports, list)
    assert isinstance(resistances, list)


def test_drawdown():
    assert drawdown_from_52w_high([100.0, 50.0]) == -50.0
    assert drawdown_from_52w_high([100.0, 120.0]) == 0.0
    assert drawdown_from_52w_high([]) is None


def test_technical_snapshot_insufficient_data():
    snap = build_technical_snapshot("TEST", _bars([100.0] * 30))
    assert snap.insufficient_data is True
    assert snap.overall_trend_score is None


def test_technical_snapshot_full():
    closes = [100.0 + i * 0.5 for i in range(120)]
    snap = build_technical_snapshot("TEST", _bars(closes))
    assert snap.insufficient_data is False
    assert snap.overall_trend_score is not None
    assert snap.overall_trend_score > 50
    assert snap.short_term_trend == "BULL"
    assert snap.rsi14 is not None
    assert snap.atr14 is not None
