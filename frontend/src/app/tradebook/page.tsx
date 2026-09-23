"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { IconArrowDown, IconArrowUp, IconClose, IconPencil, IconPlus, IconRefresh, IconTrash } from "@/components/icons";
import { api } from "@/lib/api";
import { formatDate, formatPrice, formatQuantity, formatSignedINR } from "@/lib/format";
import type { Trade, TradeExitInput, TradeInput, TradeSide, TradebookSummary } from "@/lib/types";
import styles from "./page.module.css";

const today = () => new Date().toISOString().slice(0, 10);

const EMPTY_TRADE: TradeInput = {
  symbol: "",
  side: "long",
  entryDate: today(),
  entryQuantity: 0,
  entryPrice: 0,
  broker: null,
  notes: null,
};

function pnlClass(value: number | null) {
  if (value == null) return styles.pending;
  return value >= 0 ? styles.gain : styles.loss;
}

function PnlValue({ value }: { value: number | null }) {
  return <span className={`num ${pnlClass(value)}`}>{value == null ? "—" : formatSignedINR(value)}</span>;
}

interface TradeFormProps {
  editing: Trade | null;
  onSaved: (input: TradeInput, id?: string) => Promise<void>;
  onCancel: () => void;
}

function TradeForm({ editing, onSaved, onCancel }: TradeFormProps) {
  const [open, setOpen] = useState(Boolean(editing));
  const [form, setForm] = useState<TradeInput>(EMPTY_TRADE);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (editing) {
      setForm({
        symbol: editing.symbol,
        side: editing.side,
        entryDate: editing.entryDate,
        entryQuantity: editing.entryQuantity,
        entryPrice: editing.entryPrice,
        broker: editing.broker,
        notes: editing.notes,
      });
      setOpen(true);
      setError(null);
    }
  }, [editing]);

  const setField = <K extends keyof TradeInput>(key: K, value: TradeInput[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const close = () => {
    setOpen(false);
    setForm(EMPTY_TRADE);
    setError(null);
    onCancel();
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.symbol.trim()) return setError("Symbol is required.");
    if (!form.entryDate) return setError("Entry date is required.");
    if (form.entryQuantity <= 0 || form.entryPrice <= 0) return setError("Quantity and entry price must be greater than zero.");
    setSaving(true);
    setError(null);
    try {
      await onSaved(form, editing?.id);
      close();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t save the trade.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return <Button onClick={() => setOpen(true)}><IconPlus width={15} height={15} /> Add trade</Button>;
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <div className={styles.formHeader}>
        <div>
          <h2>{editing ? `Edit ${form.symbol}` : "Record a trade"}</h2>
          <p>Entry details stay fixed once an exit is recorded.</p>
        </div>
        <button type="button" className={styles.closeButton} onClick={close} aria-label="Close trade form"><IconClose width={17} height={17} /></button>
      </div>
      <div className={styles.formGrid}>
        <label><span>Side</span><select value={form.side} onChange={(event) => setField("side", event.target.value as TradeSide)}><option value="long">Long · buy then sell</option><option value="short">Short · sell then cover</option></select></label>
        <label><span>Symbol</span><input value={form.symbol} onChange={(event) => setField("symbol", event.target.value.toUpperCase())} placeholder="RELIANCE" required /></label>
        <label><span>Entry date</span><input type="date" value={form.entryDate} onChange={(event) => setField("entryDate", event.target.value)} required /></label>
        <label><span>Quantity</span><input type="number" min="0.001" step="0.001" value={form.entryQuantity || ""} onChange={(event) => setField("entryQuantity", Number(event.target.value))} required /></label>
        <label><span>Entry price (₹)</span><input type="number" min="0.01" step="0.01" value={form.entryPrice || ""} onChange={(event) => setField("entryPrice", Number(event.target.value))} required /></label>
        <label><span>Broker</span><input value={form.broker ?? ""} onChange={(event) => setField("broker", event.target.value || null)} placeholder="Zerodha, Groww…" /></label>
        <label className={styles.notesField}><span>Notes</span><textarea value={form.notes ?? ""} onChange={(event) => setField("notes", event.target.value || null)} placeholder="Optional setup or context" rows={2} /></label>
      </div>
      {error && <p className={styles.formError} role="alert">{error}</p>}
      <div className={styles.formActions}><Button type="button" variant="ghost" onClick={close}>Cancel</Button><Button type="submit" loading={saving}>{editing ? "Save changes" : "Add trade"}</Button></div>
    </form>
  );
}

interface ExitDialogProps {
  trade: Trade;
  onClose: () => void;
  onSubmit: (input: TradeExitInput) => Promise<void>;
}

function ExitDialog({ trade, onClose, onSubmit }: ExitDialogProps) {
  const [quantity, setQuantity] = useState(String(trade.remainingQuantity));
  const [price, setPrice] = useState(trade.currentLtp == null ? "" : String(trade.currentLtp));
  const [exitDate, setExitDate] = useState(today());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const estimated = Number(quantity) > 0 && Number(price) > 0
    ? (trade.side === "long" ? Number(price) - trade.entryPrice : trade.entryPrice - Number(price)) * Number(quantity)
    : null;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape" && !saving) onClose(); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [onClose, saving]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numericQuantity = Number(quantity);
    const numericPrice = Number(price);
    if (!Number.isFinite(numericQuantity) || numericQuantity <= 0 || numericQuantity > trade.remainingQuantity) return setError(`Quantity must be between 0 and ${formatQuantity(trade.remainingQuantity)}.`);
    if (!Number.isFinite(numericPrice) || numericPrice <= 0) return setError("Enter the exit price.");
    if (!exitDate || exitDate < trade.entryDate) return setError("Exit date cannot be before entry date.");
    setSaving(true);
    setError(null);
    try { await onSubmit({ quantity: numericQuantity, exitPrice: numericPrice, exitDate }); }
    catch (err) { setError(err instanceof Error ? err.message : "Couldn’t record the exit."); setSaving(false); }
  }

  return (
    <div className={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && !saving && onClose()}>
      <section className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="exit-title">
        <div className={styles.formHeader}><div><p className={styles.dialogLabel}>{trade.side === "long" ? "Sell position" : "Cover position"}</p><h2 id="exit-title">Exit {trade.symbol}</h2><p>Record an exit lot. This locks the trade’s entry details.</p></div><button type="button" className={styles.closeButton} onClick={onClose} disabled={saving} aria-label="Close exit dialog"><IconClose width={17} height={17} /></button></div>
        <div className={styles.positionNote}><span>{formatQuantity(trade.remainingQuantity)} shares remain open</span><strong>Entry {formatPrice(trade.entryPrice)} · {formatDate(trade.entryDate)}</strong></div>
        <form className={styles.exitForm} onSubmit={submit}>
          <div className={styles.formGrid}><label><span>Quantity</span><input autoFocus type="number" min="0.001" max={trade.remainingQuantity} step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label><label><span>{trade.side === "long" ? "Exit price" : "Cover price"}</span><input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} /></label><label><span>Exit date</span><input type="date" min={trade.entryDate} value={exitDate} onChange={(event) => setExitDate(event.target.value)} /></label></div>
          {estimated != null && <div className={`${styles.estimate} ${estimated >= 0 ? styles.estimateGain : styles.estimateLoss}`}><span>Estimated realized P/L</span><strong>{formatSignedINR(estimated)}</strong></div>}
          {error && <p className={styles.formError} role="alert">{error}</p>}
          <div className={styles.formActions}><Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button><Button type="submit" loading={saving}>Record exit</Button></div>
        </form>
      </section>
    </div>
  );
}

function TradeRow({ trade, onEdit, onDelete, onExit }: { trade: Trade; onEdit: (trade: Trade) => void; onDelete: (trade: Trade) => void; onExit: (trade: Trade) => void }) {
  const isLong = trade.side === "long";
  return (
    <article className={styles.tradeCard}>
      <div className={styles.tradeTop}>
        <div className={styles.identity}><div className={styles.symbolLine}><strong>{trade.symbol}</strong><span className={`${styles.side} ${isLong ? styles.long : styles.short}`}>{isLong ? <IconArrowUp width={12} height={12} /> : <IconArrowDown width={12} height={12} />}{isLong ? "Long" : "Short"}</span><span className={`${styles.status} ${trade.status === "closed" ? styles.closed : styles.open}`}>{trade.status}</span></div><span className={styles.meta}>{formatDate(trade.entryDate)} · {formatQuantity(trade.entryQuantity)} shares at {formatPrice(trade.entryPrice)}{trade.broker ? ` · ${trade.broker}` : ""}</span></div>
        <div className={styles.actions}><Button variant="ghost" size="sm" onClick={() => onExit(trade)} disabled={trade.status === "closed"}>Exit</Button>{trade.exits.length === 0 && <><Button variant="ghost" size="sm" onClick={() => onEdit(trade)}><IconPencil width={14} height={14} />Edit</Button><Button variant="ghost" size="sm" className={styles.delete} onClick={() => onDelete(trade)}><IconTrash width={14} height={14} />Remove</Button></>}</div>
      </div>
      <div className={styles.metrics}>
        <div><span>Remaining</span><strong className="num">{trade.status === "closed" ? "Closed" : formatQuantity(trade.remainingQuantity)}</strong></div>
        <div><span>LTP</span><strong className="num">{trade.currentLtp == null ? "—" : formatPrice(trade.currentLtp)}</strong></div>
        <div><span>Realized P/L</span><strong><PnlValue value={trade.realizedPnl} /></strong></div>
        <div><span>Unrealized P/L</span><strong><PnlValue value={trade.unrealizedPnl} /></strong></div>
        <div><span>Total P/L</span><strong><PnlValue value={trade.totalPnl} /></strong></div>
      </div>
      {trade.notes && <p className={styles.notes}>{trade.notes}</p>}
      {trade.exits.length > 0 && <details className={styles.exitHistory}><summary>{trade.exits.length} exit {trade.exits.length === 1 ? "lot" : "lots"}</summary><div className={styles.exitList}>{trade.exits.map((exit) => <div className={styles.exitRow} key={exit.id}><span>{formatDate(exit.exitDate)} · {formatQuantity(exit.quantity)} shares at {formatPrice(exit.exitPrice)}</span><PnlValue value={exit.realizedPnl} /></div>)}</div></details>}
    </article>
  );
}

export default function TradebookPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [summary, setSummary] = useState<TradebookSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Trade | null>(null);
  const [exitTarget, setExitTarget] = useState<Trade | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try { const data = await api.getTradebook(); setTrades(data.trades); setSummary(data.summary); }
    catch (err) { setError(err instanceof Error ? err.message : "Couldn’t load the Tradebook."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const saveTrade = useCallback(async (input: TradeInput, id?: string) => { if (id) await api.updateTrade(id, input); else await api.addTrade(input); await load(true); }, [load]);
  const removeTrade = useCallback(async (trade: Trade) => { if (!window.confirm(`Remove ${trade.symbol} from the Tradebook?`)) return; try { await api.deleteTrade(trade.id); await load(true); } catch (err) { setError(err instanceof Error ? err.message : "Couldn’t remove the trade."); } }, [load]);
  const recordExit = useCallback(async (input: TradeExitInput) => { if (!exitTarget) return; await api.exitTrade(exitTarget.id, input); setExitTarget(null); await load(true); }, [exitTarget, load]);
  const refresh = async () => { setRefreshing(true); setError(null); try { const data = await api.refreshTradebook(); setTrades(data.trades); setSummary(data.summary); } catch (err) { setError(err instanceof Error ? err.message : "Price refresh failed."); } finally { setRefreshing(false); } };
  const active = useMemo(() => trades.filter((trade) => trade.status === "open").length, [trades]);

  return (
    <AppShell>
      <header className={styles.pageHeader}><div><h1 className={styles.pageTitle}>Tradebook</h1><p className={styles.pageSubtitle}>A clear record of every long and short trade you have taken.</p></div><div className={styles.headerActions}><Button variant="secondary" onClick={() => void refresh()} loading={refreshing} disabled={loading || active === 0}><IconRefresh width={15} height={15} />{refreshing ? "Refreshing" : "Refresh prices"}</Button><TradeForm editing={editing} onSaved={saveTrade} onCancel={() => setEditing(null)} /></div></header>
      {error && <div className={styles.error} role="alert"><span>{error}</span><button type="button" onClick={() => void load()}>Retry</button></div>}
      {summary && <section className={styles.summary} aria-label="Tradebook summary"><div><span>Realized P/L</span><strong><PnlValue value={summary.realizedPnl} /></strong></div><div><span>Unrealized P/L</span><strong><PnlValue value={summary.unrealizedPnl} /></strong></div><div><span>Total P/L</span><strong><PnlValue value={summary.totalPnl} /></strong></div><div><span>Trades</span><strong>{summary.tradeCount}</strong><small>{summary.openCount} open · {summary.closedCount} closed</small></div></section>}
      {summary?.unpricedOpenCount ? <p className={styles.pendingNote}>Refresh prices to complete P/L for {summary.unpricedOpenCount} open {summary.unpricedOpenCount === 1 ? "trade" : "trades"}.</p> : null}
      {loading ? <div className={styles.skeleton}><Skeleton width="9rem" height="1.2rem" /><Skeleton height="15rem" radius="var(--radius-lg)" /></div> : trades.length === 0 ? <div className={styles.empty}><h2>Your Tradebook is empty</h2><p>Record your first long or short equity trade to start tracking realized and unrealized P/L.</p><TradeForm editing={editing} onSaved={saveTrade} onCancel={() => setEditing(null)} /></div> : <section className={styles.list} aria-label="Trade history"><div className={styles.listHeader}><h2>All trades</h2><span>{trades.length} {trades.length === 1 ? "trade" : "trades"}</span></div>{trades.map((trade) => <TradeRow key={trade.id} trade={trade} onEdit={setEditing} onDelete={removeTrade} onExit={setExitTarget} />)}</section>}
      {exitTarget && <ExitDialog trade={exitTarget} onClose={() => setExitTarget(null)} onSubmit={recordExit} />}
    </AppShell>
  );
}
