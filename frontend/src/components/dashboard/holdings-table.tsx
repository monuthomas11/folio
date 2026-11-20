"use client";

import Link from "next/link";
import { Fragment, useMemo, useState } from "react";
import type { AnalysisRating, Holding, HoldingsInput } from "@/lib/types";
import { holdingStats } from "@/lib/holdings";
import {
  formatINRFractionless,
  formatPrice,
  formatQuantity,
  formatShortDate,
  formatSigned,
  parseBackendDate,
} from "@/lib/format";
import { StatusPill } from "@/components/ui/status-pill";
import { Button } from "@/components/ui/button";
import { IconCheck, IconPencil, IconRefresh, IconTrash } from "@/components/icons";
import { HoldingInlineEdit } from "./holding-inline-edit";
import styles from "./holdings-table.module.css";

interface HoldingsTableProps {
  holdings: Holding[];
  refreshingSymbols: Set<string>;
  onRefreshRow: (symbol: string) => void;
  onEdit?: (holding: Holding) => void;
  onCancelEdit?: () => void;
  onSave?: (id: string, input: HoldingsInput) => Promise<void>;
  editingId?: string | null;
  onDelete?: (holding: Holding) => void;
  onExit?: (holding: Holding) => void;
  removingIds?: Set<string>;
  exitingIds?: Set<string>;
  lastUpdated: string | null;
  aiRatings?: Record<string, AnalysisRating>;
}

const COLUMN_COUNT = 12;
const PAGE_SIZE = 10;

type HoldingFilter = "all" | "profit" | "loss" | "near-sl" | "sl-hit" | "target-hit";

type SortKey =
  | "entryDate"
  | "ltp"
  | "avgPrice"
  | "invested"
  | "currentValue"
  | "pnl"
  | "pnlPct"
  | "dayChange"
  | "symbol";

type SortDir = "asc" | "desc";

interface TableRow {
  holding: Holding;
  stats: ReturnType<typeof holdingStats>;
}

const FILTER_OPTIONS: { value: HoldingFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "profit", label: "In profit" },
  { value: "loss", label: "In loss" },
  { value: "near-sl", label: "Near SL" },
  { value: "sl-hit", label: "SL hit" },
  { value: "target-hit", label: "Target hit" },
];

const FILTER_MATCHERS: Record<HoldingFilter, (row: TableRow) => boolean> = {
  all: () => true,
  profit: (row) => row.holding.currentLtp != null && row.stats.pnl > 0,
  loss: (row) => row.holding.currentLtp != null && row.stats.pnl < 0,
  "near-sl": (row) => row.stats.status === "near-sl",
  "sl-hit": (row) => row.stats.status === "sl-hit",
  "target-hit": (row) => row.stats.status === "target-hit",
};

const SORT_OPTIONS: { key: SortKey; label: string; defaultDir: SortDir }[] = [
  { key: "entryDate", label: "Entry date", defaultDir: "desc" },
  { key: "ltp", label: "LTP", defaultDir: "desc" },
  { key: "avgPrice", label: "Avg price", defaultDir: "desc" },
  { key: "invested", label: "Invested", defaultDir: "desc" },
  { key: "currentValue", label: "Current value", defaultDir: "desc" },
  { key: "pnl", label: "P/L", defaultDir: "desc" },
  { key: "pnlPct", label: "P/L %", defaultDir: "desc" },
  { key: "dayChange", label: "1D change", defaultDir: "desc" },
  { key: "symbol", label: "Symbol", defaultDir: "asc" },
];

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

function sortValue(row: TableRow, key: SortKey): number | string | null {
  switch (key) {
    case "symbol":
      return row.holding.symbol;
    case "ltp":
      return row.holding.currentLtp;
    case "avgPrice":
      return row.holding.avgBuyPrice;
    case "invested":
      return row.stats.invested;
    case "currentValue":
      return row.stats.currentValue;
    case "pnl":
      return row.holding.currentLtp == null ? null : row.stats.pnl;
    case "pnlPct":
      return row.holding.currentLtp == null ? null : row.stats.pnlPct;
    case "dayChange":
      return row.holding.oneDayChangePct;
    case "entryDate":
      return row.holding.createdAt ? parseBackendDate(row.holding.createdAt).getTime() : null;
  }
}

function sortRows(rows: TableRow[], key: SortKey, dir: SortDir): TableRow[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = sortValue(a, key);
    const bv = sortValue(b, key);
    if (av == null && bv == null) return a.holding.symbol.localeCompare(b.holding.symbol);
    if (av == null) return 1;
    if (bv == null) return -1;
    const diff =
      typeof av === "string" || typeof bv === "string"
        ? String(av).localeCompare(String(bv))
        : av - bv;
    return diff !== 0 ? diff * sign : a.holding.symbol.localeCompare(b.holding.symbol);
  });
}

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
  onCancelEdit,
  onSave,
  editingId,
  onDelete,
  onExit,
  removingIds,
  exitingIds,
  lastUpdated,
  aiRatings,
}: HoldingsTableProps) {
  const [filter, setFilter] = useState<HoldingFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("entryDate");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);

  const rows = useMemo(
    () => holdings.map((holding) => ({ holding, stats: holdingStats(holding) })),
    [holdings],
  );

  const filterCounts = useMemo(() => {
    const counts = {} as Record<HoldingFilter, number>;
    for (const option of FILTER_OPTIONS) {
      counts[option.value] = rows.filter(FILTER_MATCHERS[option.value]).length;
    }
    return counts;
  }, [rows]);

  const visible = useMemo(
    () => sortRows(rows.filter(FILTER_MATCHERS[filter]), sortKey, sortDir),
    [rows, filter, sortKey, sortDir],
  );

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const pageRows = visible.slice(pageStart, pageStart + PAGE_SIZE);
  const activeFilter = FILTER_OPTIONS.find((option) => option.value === filter);

  const applyFilter = (value: HoldingFilter) => {
    setFilter(value);
    setPage(1);
  };

  const applySort = (value: string) => {
    const option = SORT_OPTIONS.find((candidate) => candidate.key === value);
    if (!option) return;
    if (option.key !== sortKey) {
      setSortKey(option.key);
      setSortDir(option.defaultDir);
    }
    setPage(1);
  };

  const toggleSortDir = () => {
    setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    setPage(1);
  };

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
          <span className={styles.rowCount} aria-live="polite">
            {filter === "all"
              ? `${holdings.length} ${holdings.length === 1 ? "position" : "positions"}`
              : `${visible.length} of ${holdings.length}`}
          </span>
        </div>
      </div>

      <div className={styles.toolbar}>
        <div className={styles.filters} role="group" aria-label="Filter holdings">
          {FILTER_OPTIONS.map((option) => {
            const active = option.value === filter;
            return (
              <button
                key={option.value}
                type="button"
                className={active ? `${styles.filterChip} ${styles.filterActive}` : styles.filterChip}
                aria-pressed={active}
                onClick={() => applyFilter(option.value)}
              >
                {option.label}
                <span className={styles.filterCount}>{filterCounts[option.value]}</span>
              </button>
            );
          })}
        </div>

        <div className={styles.sortGroup}>
          <label className={styles.sortLabel} htmlFor="holdings-sort">
            Sort by
          </label>
          <select
            id="holdings-sort"
            className={styles.sortSelect}
            value={sortKey}
            onChange={(event) => applySort(event.target.value)}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            className={styles.sortDir}
            onClick={toggleSortDir}
            aria-label={
              sortDir === "asc"
                ? "Sorted ascending. Switch to descending"
                : "Sorted descending. Switch to ascending"
            }
            title={sortDir === "asc" ? "Ascending" : "Descending"}
          >
            {sortDir === "asc" ? "↑ Asc" : "↓ Desc"}
          </button>
        </div>
      </div>

      {pageRows.length === 0 ? (
        <div className={styles.empty}>
          <p className={styles.emptyText}>
            No holdings match the “{activeFilter?.label}” filter.
          </p>
          <Button variant="secondary" size="sm" onClick={() => applyFilter("all")}>
            Show all holdings
          </Button>
        </div>
      ) : (
        <>
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
                    Avg
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    LTP
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    1D %
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    Invested
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    Curr. Value
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    P/L
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    Added
                  </th>
                  <th scope="col">Status</th>
                  <th scope="col">AI</th>
                  <th scope="col" className={styles.actionHeader}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map(({ holding: h, stats: s }) => {
                  const meta = STATUS_META[s.status];
                  const refreshing = refreshingSymbols.has(h.symbol);
                  const removing = removingIds?.has(h.id) ?? false;
                  const exiting = exitingIds?.has(h.id) ?? false;
                  const isEditing = editingId === h.id;
                  return (
                    <Fragment key={h.id}>
                      <tr className={isEditing ? styles.rowEditing : undefined}>
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
                        <td className="num numeric">{formatINRFractionless(s.invested)}</td>
                        <td className="num numeric">{formatINRFractionless(s.currentValue)}</td>
                        <td className="numeric">
                          <PnLCell pnl={s.pnl} pnlPct={s.pnlPct} />
                        </td>
                        <td className="num numeric">
                          {h.createdAt ? formatShortDate(h.createdAt) : "—"}
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
                              className={`${styles.iconAction} ${styles.iconBtn}`}
                              onClick={() => onEdit?.(h)}
                              aria-label={`Edit ${h.symbol}`}
                              title="Edit holding"
                              aria-expanded={isEditing}
                            >
                              <IconPencil width={14} height={14} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className={`${styles.iconAction} ${styles.iconBtn}`}
                              onClick={() => onRefreshRow(h.symbol)}
                              loading={refreshing}
                              disabled={h.currentLtp == null && !refreshing}
                              aria-label={`Fetch latest price for ${h.symbol}`}
                              title="Fetch price"
                            >
                              {!refreshing && <IconRefresh width={14} height={14} />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className={`${styles.removeAction} ${styles.iconBtn}`}
                              onClick={() => onExit?.(h)}
                              loading={exiting}
                              disabled={exiting || removing}
                              aria-label={`Exit ${h.symbol}`}
                              title="Record an exit"
                            >
                              {!exiting && <IconCheck width={14} height={14} />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className={`${styles.removeAction} ${styles.iconBtn}`}
                              onClick={() => onDelete?.(h)}
                              loading={removing}
                              disabled={removing}
                              aria-label={`Remove ${h.symbol}`}
                              title="Remove holding"
                            >
                              {!removing && <IconTrash width={14} height={14} />}
                            </Button>
                          </div>
                        </td>
                      </tr>
                      {isEditing && onSave && (
                        <tr className={styles.editRow}>
                          <td colSpan={COLUMN_COUNT} className={styles.editCell}>
                            <HoldingInlineEdit
                              holding={h}
                              onSave={onSave}
                              onCancel={() => onCancelEdit?.()}
                            />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className={styles.mobile}>
            {pageRows.map(({ holding: h, stats: s }) => {
              const meta = STATUS_META[s.status];
              const refreshing = refreshingSymbols.has(h.symbol);
              const removing = removingIds?.has(h.id) ?? false;
              const exiting = exitingIds?.has(h.id) ?? false;
              const isEditing = editingId === h.id;
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
                  {isEditing && onSave ? (
                    <HoldingInlineEdit
                      holding={h}
                      onSave={onSave}
                      onCancel={() => onCancelEdit?.()}
                    />
                  ) : (
                    <>
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
                        <div>
                          <dt>Added</dt>
                          <dd className="num">
                            {h.createdAt ? formatShortDate(h.createdAt) : "—"}
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
                            aria-expanded={isEditing}
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
                    </>
                  )}
                </article>
              );
            })}
          </div>
        </>
      )}

      {visible.length > 0 && (
        <nav className={styles.pagination} aria-label="Holdings pagination">
          <span className={styles.pageInfo} aria-live="polite">
            Showing {pageStart + 1}–{pageStart + pageRows.length} of {visible.length}
          </span>
          {pageCount > 1 && (
            <div className={styles.pageControls}>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                ← Prev
              </Button>
              <span className={styles.pageStatus}>
                Page {currentPage} of {pageCount}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage(currentPage + 1)}
                disabled={currentPage === pageCount}
              >
                Next →
              </Button>
            </div>
          )}
        </nav>
      )}
    </div>
  );
}
