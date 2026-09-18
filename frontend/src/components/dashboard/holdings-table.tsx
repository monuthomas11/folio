"use client";

import Link from "next/link";
import type { AnalysisRating, Holding } from "@/lib/types";
import { holdingStats } from "@/lib/holdings";
import { formatINRFractionless, formatPrice, formatQuantity, formatSigned, parseBackendDate } from "@/lib/format";
import { StatusPill } from "@/components/ui/status-pill";
import { Button } from "@/components/ui/button";
import { IconCheck, IconPencil, IconRefresh, IconTrash } from "@/components/icons";
import styles from "./holdings-table.module.css";

interface HoldingsTableProps {
  holdings: Holding[];
  refreshingSymbols: Set<string>;
  onRefreshRow: (symbol: string) => void;
  onEdit?: (holding: Holding) => void;
  onDelete?: (holding: Holding) => void;
  onExit?: (holding: Holding) => void;
  removingIds?: Set<string>;
  exitingIds?: Set<string>;
  lastUpdated: string | null;
  aiRatings?: Record<string, AnalysisRating>;
}

const STATUS_META: Record<
  string,
  { tone: "healthy" | "warn" | "danger" | "gain"; label: string }
> = {
  healthy: { tone: "healthy", label: "Healthy" },
  "near-sl": { tone: "warn", label: "Near SL" },
  "sl-hit": { tone: "danger", label: "SL hit" },
  "target-hit": { tone: "gain", label: "Target hit" },
};

const AI_TONES: Record<AnalysisRating, "gain" | "healthy" | "warn" | "danger"> = {
  BUY: "gain",
  HOLD: "healthy",
  REDUCE: "warn",
  EXIT: "danger",
};

function PnLCell({ pnl, pnlPct }: { pnl: number; pnlPct: number }) {
  const gain = pnl >= 0;
  return (
    <div className={gain ? styles.pnlGain : styles.pnlLoss}>
      <span className="num">{formatINRFractionless(pnl)}</span>
      <span className={styles.pnlPct}>{formatSigned(pnlPct)}</span>
    </div>
  );
}

function DayChangeCell({ value }: { value: number | null }) {
  if (value == null) {
    return <span className={styles.pending}>—</span>;
  }
  const tone = value > 0 ? styles.changeGain : value < 0 ? styles.changeLoss : styles.changeFlat;
  const arrow = value > 0 ? "↑ " : value < 0 ? "↓ " : "";
  return <span className={tone}>{arrow}{formatSigned(value)}</span>;
}

export function HoldingsTable({
  holdings,
  refreshingSymbols,
  onRefreshRow,
  onEdit,
  onDelete,
  onExit,
  removingIds,
  exitingIds,
  lastUpdated,
  aiRatings,
}: HoldingsTableProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.tableHead}>
        <h2 className={styles.title}>Holdings</h2>
        <div className={styles.tableHeadRight}>
          {lastUpdated && (
            <span className={styles.updated}>
              Updated{" "}
              {new Intl.DateTimeFormat("en-IN", {
                hour: "numeric",
                minute: "2-digit",
                hour12: true,
              }).format(parseBackendDate(lastUpdated))}
            </span>
          )}
          <span className={styles.rowCount}>
            {holdings.length} {holdings.length === 1 ? "position" : "positions"}
          </span>
        </div>
      </div>

      <div className={styles.desktop}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.thSymbol}>
                Symbol
              </th>
              <th scope="col" className={styles.numHeader}>
                Qty
              </th>
              <th scope="col" className={styles.numHeader}>
                Avg price
              </th>
              <th scope="col" className={styles.numHeader}>
                LTP
              </th>
              <th scope="col" className={styles.numHeader}>
                1D change
              </th>
              <th scope="col" className={styles.numHeader}>
                SL
              </th>
              <th scope="col" className={styles.numHeader}>
                Target
              </th>
              <th scope="col" className={styles.numHeader}>
                Invested
              </th>
              <th scope="col" className={styles.numHeader}>
                Current value
              </th>
              <th scope="col" className={styles.numHeader}>
                P/L
              </th>
              <th scope="col">Status</th>
              <th scope="col">AI</th>
              <th scope="col" className={styles.actionHeader}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => {
              const s = holdingStats(h);
              const meta = STATUS_META[s.status];
              const refreshing = refreshingSymbols.has(h.symbol);
              const removing = removingIds?.has(h.id) ?? false;
              const exiting = exitingIds?.has(h.id) ?? false;
              return (
                <tr key={h.id}>
                  <td>
                    <div className={styles.symbolCell}>
                      <Link href={`/holdings/${h.id}`} className={styles.symbolLink}>
                        {h.symbol}
                      </Link>
                      {h.broker && <span className={styles.broker}>{h.broker}</span>}
                    </div>
                  </td>
                  <td className="num numeric">{formatQuantity(h.quantity)}</td>
                  <td className="num numeric">{formatPrice(h.avgBuyPrice)}</td>
                  <td className="num numeric">
                    <span className={h.currentLtp != null ? styles.ltp : styles.pending}>
                      {h.currentLtp != null ? formatPrice(h.currentLtp) : "—"}
                    </span>
                  </td>
                  <td className="num numeric"><DayChangeCell value={h.oneDayChangePct} /></td>
                  <td className="num numeric">{h.stopLoss != null ? formatPrice(h.stopLoss) : "—"}</td>
                  <td className="num numeric">{h.targetPrice != null ? formatPrice(h.targetPrice) : "—"}</td>
                  <td className="num numeric">{formatINRFractionless(s.invested)}</td>
                  <td className="num numeric">{formatINRFractionless(s.currentValue)}</td>
                  <td className="numeric">
                    <PnLCell pnl={s.pnl} pnlPct={s.pnlPct} />
                  </td>
                  <td>
                    <StatusPill tone={meta.tone} label={meta.label}>
                      {meta.label}
                    </StatusPill>
                  </td>
                  <td>
                    {aiRatings?.[h.symbol] ? (
                      <Link href={`/holdings/${h.id}`} className={styles.aiLink}>
                        <StatusPill tone={AI_TONES[aiRatings[h.symbol]]}>
                          {aiRatings[h.symbol]}
                        </StatusPill>
                      </Link>
                    ) : (
                      <span className={styles.aiNone}>—</span>
                    )}
                  </td>
                  <td className={styles.actionCell}>
                    <div className={styles.actions}>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={styles.iconAction}
                        onClick={() => onEdit?.(h)}
                        aria-label={`Edit ${h.symbol}`}
                        title="Edit holding"
                      >
                        <IconPencil width={14} height={14} />
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={styles.iconAction}
                        onClick={() => onRefreshRow(h.symbol)}
                        loading={refreshing}
                        disabled={h.currentLtp == null && !refreshing}
                        aria-label={`Fetch latest price for ${h.symbol}`}
                        title="Fetch price"
                      >
                        {!refreshing && <IconRefresh width={14} height={14} />}
                        {refreshing ? "Fetching" : "Fetch"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={styles.removeAction}
                        onClick={() => onExit?.(h)}
                        loading={exiting}
                        disabled={exiting || removing}
                        aria-label={`Exit ${h.symbol}`}
                        title="Record an exit"
                      >
                        {!exiting && <IconCheck width={14} height={14} />}
                        {exiting ? "Exiting" : "Exit"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={styles.removeAction}
                        onClick={() => onDelete?.(h)}
                        loading={removing}
                        disabled={removing}
                        aria-label={`Remove ${h.symbol}`}
                        title="Remove holding"
                      >
                        {!removing && <IconTrash width={14} height={14} />}
                        {removing ? "Removing" : "Remove"}
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className={styles.mobile}>
        {holdings.map((h) => {
          const s = holdingStats(h);
          const meta = STATUS_META[s.status];
          const refreshing = refreshingSymbols.has(h.symbol);
          const removing = removingIds?.has(h.id) ?? false;
          const exiting = exitingIds?.has(h.id) ?? false;
          return (
            <article key={h.id} className={styles.card}>
              <header className={styles.cardHeader}>
                <div>
                  <Link href={`/holdings/${h.id}`} className={styles.symbolLink}>
                    {h.symbol}
                  </Link>
                  {h.broker && <span className={styles.broker}>{h.broker}</span>}
                </div>
                <StatusPill tone={meta.tone} label={meta.label}>
                  {meta.label}
                </StatusPill>
              </header>
              <dl className={styles.cardGrid}>
                <div>
                  <dt>Qty</dt>
                  <dd className="num">{formatQuantity(h.quantity)}</dd>
                </div>
                <div>
                  <dt>Avg</dt>
                  <dd className="num">{formatPrice(h.avgBuyPrice)}</dd>
                </div>
                <div>
                  <dt>LTP</dt>
                  <dd className="num">
                    <span className={h.currentLtp != null ? styles.ltp : styles.pending}>
                      {h.currentLtp != null ? formatPrice(h.currentLtp) : "—"}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>1D change</dt>
                  <dd className="num"><DayChangeCell value={h.oneDayChangePct} /></dd>
                </div>
                <div>
                  <dt>SL / Target</dt>
                  <dd className="num">
                    {h.stopLoss != null ? formatPrice(h.stopLoss) : "—"} /{" "}
                    {h.targetPrice != null ? formatPrice(h.targetPrice) : "—"}
                  </dd>
                </div>
                <div>
                  <dt>Current value</dt>
                  <dd className="num">{formatINRFractionless(s.currentValue)}</dd>
                </div>
                <div>
                  <dt>P/L</dt>
                  <dd>
                    <PnLCell pnl={s.pnl} pnlPct={s.pnlPct} />
                  </dd>
                </div>
              </dl>
              <div className={styles.cardFooter}>
                <div className={styles.actions}>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onRefreshRow(h.symbol)}
                    loading={refreshing}
                    disabled={h.currentLtp == null && !refreshing}
                  >
                    {!refreshing && <IconRefresh width={14} height={14} />}
                    {refreshing ? "Fetching" : "Fetch price"}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onEdit?.(h)}
                  >
                    <IconPencil width={14} height={14} />
                    Edit
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    className={styles.exitAction}
                    onClick={() => onExit?.(h)}
                    loading={exiting}
                    disabled={exiting || removing}
                  >
                    {!exiting && <IconCheck width={14} height={14} />}
                    {exiting ? "Exiting" : "Exit holding"}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    className={styles.removeAction}
                    onClick={() => onDelete?.(h)}
                    loading={removing}
                    disabled={removing}
                    aria-label={`Remove ${h.symbol}`}
                    title="Remove holding"
                  >
                    {!removing && <IconTrash width={14} height={14} />}
                    {removing ? "Removing" : "Remove"}
                  </Button>
                  <Link
                    href={`/holdings/${h.id}`}
                    className={`${styles.aiLink} ${styles.viewLink}`}
                  >
                    {aiRatings?.[h.symbol] ? "View analysis" : "View"}
                  </Link>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
