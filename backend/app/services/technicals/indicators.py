from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from pydantic import BaseModel

from ..market_data.base import OHLCV

MIN_BARS = 60


def sma(values: Sequence[float], span: int) -> list[float | None]:
    out: list[float | None] = []
    window_sum = 0.0
    for i, v in enumerate(values):
        window_sum += v
        if i >= span:
            window_sum -= values[i - span]
        out.append(window_sum / span if i >= span - 1 else None)
    return out


def ema(values: Sequence[float], span: int) -> list[float | None]:
    out: list[float | None] = []
    if len(values) < span:
        return [None] * len(values)
    k = 2.0 / (span + 1.0)
    prev = sum(values[:span]) / span
    for i, v in enumerate(values):
        if i < span - 1:
            out.append(None)
        elif i == span - 1:
            out.append(prev)
        else:
            prev = v * k + prev * (1.0 - k)
            out.append(prev)
    return out


def rsi(closes: Sequence[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(
    closes: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float | None, float | None, float | None]:
    if len(closes) < slow + signal:
        return None, None, None
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line: list[float] = []
    offset = slow - fast
    for i in range(offset, len(closes)):
        f = fast_ema[i]
        s = slow_ema[i]
        if f is None or s is None:
            continue
        macd_line.append(f - s)
    if len(macd_line) < signal:
        return None, None, None
    signal_line = ema(macd_line, signal)
    latest = macd_line[-1]
    latest_signal = signal_line[-1]
    if latest_signal is None:
        return latest, None, None
    return latest, latest_signal, latest - latest_signal


def atr(bars: Sequence[OHLCV], period: int = 14) -> float | None:
    if len(bars) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(bars)):
        high = bars[i].high
        low = bars[i].low
        prev_close = bars[i - 1].close
        trs.append(
            max(high - low, abs(high - prev_close), abs(low - prev_close))
        )
    value = sum(trs[:period]) / period
    for tr in trs[period:]:
        value = (value * (period - 1) + tr) / period
    return value


def support_resistance(
    bars: Sequence[OHLCV], window: int = 20
) -> tuple[list[float], list[float]]:
    supports: list[float] = []
    resistances: list[float] = []
    lows = [b.low for b in bars]
    highs = [b.high for b in bars]
    start = max(window, len(bars) - 120)
    half = window // 2
    for i in range(start, len(bars)):
        lo_slice = lows[max(0, i - half) : i + half + 1]
        hi_slice = highs[max(0, i - half) : i + half + 1]
        if lows[i] <= min(lo_slice):
            supports.append(lows[i])
        if highs[i] >= max(hi_slice):
            resistances.append(highs[i])

    def dedupe(levels: list[float], tol: float = 0.01) -> list[float]:
        result: list[float] = []
        for level in sorted(levels):
            if not result or abs(level - result[-1]) / (result[-1] or 1.0) > tol:
                result.append(level)
        return result

    price = bars[-1].close if bars else 0.0
    supports = [round(s, 2) for s in dedupe(supports) if s < price]
    resistances = [round(r, 2) for r in dedupe(resistances) if r > price]
    return supports[-3:], resistances[-3:]


def drawdown_from_52w_high(closes: Sequence[float]) -> float | None:
    if not closes:
        return None
    high = max(closes)
    if high <= 0:
        return None
    return (closes[-1] - high) / high * 100.0


class TechnicalSnapshot(BaseModel):
    symbol: str
    bar_count: int = 0
    insufficient_data: bool = True
    close: float | None = None
    ema20: float | None = None
    ema50: float | None = None
    ema200: float | None = None
    rsi14: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    macd_direction: str | None = None
    atr14: float | None = None
    atr_pct: float | None = None
    support_levels: list[float] = []
    resistance_levels: list[float] = []
    high_52w: float | None = None
    low_52w: float | None = None
    distance_to_52w_high_pct: float | None = None
    distance_to_52w_low_pct: float | None = None
    volume_trend: float | None = None
    long_term_trend: str | None = None
    medium_term_trend: str | None = None
    short_term_trend: str | None = None
    momentum: str | None = None
    volatility: str | None = None
    overall_trend_score: int | None = None
    computed_at: datetime | None = None


def _trend(close: float | None, ref: float | None) -> str | None:
    if close is None or ref is None or ref == 0:
        return None
    diff_pct = (close - ref) / ref * 100.0
    if diff_pct > 1.0:
        return "BULL"
    if diff_pct < -1.0:
        return "BEAR"
    return "NEUTRAL"


def build_technical_snapshot(symbol: str, bars: Sequence[OHLCV]) -> TechnicalSnapshot:
    closes = [b.close for b in bars]
    n = len(closes)
    if n < MIN_BARS:
        return TechnicalSnapshot(symbol=symbol, bar_count=n)

    ema20 = ema(closes, 20)[-1]
    ema50 = ema(closes, 50)[-1]
    ema200 = ema(closes, 200)[-1] if n >= 200 else None
    rsi14 = rsi(closes)
    macd_line, macd_signal, histogram = macd(closes)
    macd_direction = None
    if histogram is not None:
        macd_direction = (
            "BULLISH" if histogram > 0 else ("BEARISH" if histogram < 0 else "FLAT")
        )
    atr14 = atr(bars)
    close = closes[-1]
    atr_pct = (atr14 / close * 100.0) if atr14 is not None and close > 0 else None
    supports, resistances = support_resistance(bars)
    high_52w = max(b.high for b in bars)
    low_52w = min(b.low for b in bars)
    dist_high = (close - high_52w) / high_52w * 100.0
    dist_low = (close - low_52w) / low_52w * 100.0

    volume_trend = None
    if n >= 80:
        recent = sum(b.volume for b in bars[-20:]) / 20.0
        prior = sum(b.volume for b in bars[-80:-20]) / 60.0
        if prior > 0:
            volume_trend = recent / prior

    long_term = _trend(close, ema200)
    medium_term = _trend(close, ema50)
    short_term = _trend(close, ema20)
    if long_term is None:
        long_term = _trend(ema50, ema200)

    if rsi14 is None:
        momentum = None
    elif rsi14 < 30:
        momentum = "OVERSOLD"
    elif rsi14 > 70:
        momentum = "OVERBOUGHT"
    else:
        momentum = "NEUTRAL"

    if atr_pct is None:
        volatility = None
    elif atr_pct < 1.5:
        volatility = "LOW"
    elif atr_pct < 3.0:
        volatility = "MODERATE"
    else:
        volatility = "HIGH"

    score = 50.0
    for trend, weight in (
        (long_term, 25.0),
        (medium_term, 15.0),
        (short_term, 10.0),
    ):
        if trend == "BULL":
            score += weight
        elif trend == "BEAR":
            score -= weight
    if macd_direction == "BULLISH":
        score += 10.0
    elif macd_direction == "BEARISH":
        score -= 10.0
    if rsi14 is not None:
        if rsi14 >= 55:
            score += 5.0
        elif rsi14 <= 45:
            score -= 5.0
    if atr_pct is not None and atr_pct >= 3.0:
        score -= 5.0
    overall = int(max(0, min(100, round(score))))

    return TechnicalSnapshot(
        symbol=symbol.strip().upper(),
        bar_count=n,
        insufficient_data=False,
        close=close,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi14=rsi14,
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=histogram,
        macd_direction=macd_direction,
        atr14=atr14,
        atr_pct=atr_pct,
        support_levels=supports,
        resistance_levels=resistances,
        high_52w=high_52w,
        low_52w=low_52w,
        distance_to_52w_high_pct=dist_high,
        distance_to_52w_low_pct=dist_low,
        volume_trend=volume_trend,
        long_term_trend=long_term,
        medium_term_trend=medium_term,
        short_term_trend=short_term,
        momentum=momentum,
        volatility=volatility,
        overall_trend_score=overall,
        computed_at=datetime.now(timezone.utc),
    )
