import type { Holding } from "./types";

export interface HoldingStats {
  invested: number;
  currentValue: number;
  pnl: number;
  pnlPct: number;
  status: "healthy" | "near-sl" | "sl-hit" | "target-hit";
}

export function holdingStats(h: Holding): HoldingStats {
  const invested = h.quantity * h.avgBuyPrice;
  const currentValue = h.currentLtp != null ? h.quantity * h.currentLtp : invested;
  const pnl = currentValue - invested;
  const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;

  let status: HoldingStats["status"] = "healthy";
  if (h.currentLtp != null) {
    if (h.targetPrice != null && h.currentLtp >= h.targetPrice) {
      status = "target-hit";
    } else if (h.stopLoss != null && h.currentLtp <= h.stopLoss) {
      status = "sl-hit";
    } else if (h.stopLoss != null && h.currentLtp <= h.stopLoss * 1.03) {
      status = "near-sl";
    }
  }

  return { invested, currentValue, pnl, pnlPct, status };
}