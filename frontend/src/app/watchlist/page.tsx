"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { WatchlistForm } from "@/components/watchlist/watchlist-form";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { IconActivity, IconArrowRight, IconPencil, IconRefresh, IconTrash } from "@/components/icons";
import { api } from "@/lib/api";
import { formatPrice, formatTime } from "@/lib/format";
import type { PortfolioAlert, WatchlistInput, WatchlistItem, WatchlistLevelKind } from "@/lib/types";
import styles from "./page.module.css";

const KIND_META: Record<WatchlistLevelKind, { label: string; className: string }> = {
  entry: { label: "Entry", className: styles.entry },
  target: { label: "Target", className: styles.target },
  "stop-loss": { label: "Stop-loss", className: styles.stopLoss },
  invalidation: { label: "Invalidation", className: styles.invalidation },
};

function levelValue(lower: number, upper: number | null) {
  return upper == null ? formatPrice(lower) : `${formatPrice(lower)} – ${formatPrice(upper)}`;
}

function prefill(item: WatchlistItem) {
  const stopLoss = item.levels.filter((level) => level.kind === "stop-loss" && level.upperPrice == null);
  const targets = item.levels.filter((level) => level.kind === "target" && level.upperPrice == null);
  const params = new URLSearchParams({ symbol: item.symbol });
  if (stopLoss.length === 1) params.set("stopLoss", String(stopLoss[0].lowerPrice));
  if (targets.length === 1) params.set("targetPrice", String(targets[0].lowerPrice));
  return `/portfolio?${params.toString()}`;
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [alerts, setAlerts] = useState<PortfolioAlert[]>([]);
  const [editing, setEditing] = useState<WatchlistItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshingSymbols, setRefreshingSymbols] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const [watchlist, currentAlerts] = await Promise.all([api.getWatchlist(), api.getAlerts()]);
      setItems(watchlist);
      setAlerts(currentAlerts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t load your watchlist.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const save = useCallback(async (input: WatchlistInput) => { await api.addWatchlistItem(input); await load(true); }, [load]);
  const update = useCallback(async (id: string, input: WatchlistInput) => { await api.updateWatchlistItem(id, input); setEditing(null); await load(true); }, [load]);

  const refreshAll = async () => {
    setRefreshing(true);
    try { setItems(await api.refreshWatchlist()); await load(true); }
    catch (err) { setError(err instanceof Error ? err.message : "Price refresh failed."); }
    finally { setRefreshing(false); }
  };

  const refreshSymbol = async (symbol: string) => {
    setRefreshingSymbols((prev) => new Set(prev).add(symbol));
    try { await api.refreshWatchlistSymbol(symbol); await load(true); }
    catch (err) { setError(err instanceof Error ? err.message : "Price refresh failed."); }
    finally { setRefreshingSymbols((prev) => { const next = new Set(prev); next.delete(symbol); return next; }); }
  };

  const remove = async (item: WatchlistItem) => {
    if (!window.confirm(`Remove ${item.symbol} from your watchlist? Its saved alerts will also be removed.`)) return;
    try { await api.deleteWatchlistItem(item.id); if (editing?.id === item.id) setEditing(null); await load(true); }
    catch (err) { setError(err instanceof Error ? err.message : "Couldn’t remove the watchlist item."); }
  };

  const activeAlerts = alerts.filter((alert) => !alert.dismissed).length;
  const alertSymbols = useMemo(() => new Set(alerts.filter((alert) => alert.watchlistItemId).map((alert) => alert.watchlistItemId)), [alerts]);

  return (
    <AppShell activeAlertCount={activeAlerts}>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.overline}><span className={styles.overlineDot} aria-hidden />Before you buy</div>
          <h1 className={styles.pageTitle}>Watchlist</h1>
          <p className={styles.pageSubtitle}>Track ideas, entry zones, and the levels that matter.</p>
        </div>
        <Button variant="secondary" onClick={() => void refreshAll()} loading={refreshing} disabled={loading || items.length === 0}>
          {!refreshing && <IconRefresh width={15} height={15} />}{refreshing ? "Refreshing" : "Refresh prices"}
        </Button>
      </header>

      {error && <div className={styles.error} role="alert"><span>{error}</span><button type="button" className={styles.retry} onClick={() => void load()}>Retry</button></div>}
      <WatchlistForm editing={editing} onAdded={save} onUpdated={update} onCancel={() => setEditing(null)} />

      {loading ? <div className={styles.skeleton}><Skeleton width="7rem" height="1.2rem" /><Skeleton height="18rem" radius="var(--radius-lg)" /></div> : items.length === 0 ? (
        <div className={styles.empty}><h2>No watchlist ideas yet</h2><p>Add a symbol and give yourself a price level to watch.</p></div>
      ) : (
        <section className={styles.list} aria-label="Watchlist items">
          <div className={styles.listHeader}><h2>Watched symbols</h2><span>{items.length} {items.length === 1 ? "idea" : "ideas"}</span></div>
          {items.map((item) => {
            const itemAlerts = alerts.filter((alert) => alert.watchlistItemId === item.id && !alert.dismissed);
            const refreshingItem = refreshingSymbols.has(item.symbol);
            return <article key={item.id} className={`${styles.card} ${alertSymbols.has(item.id) ? styles.cardAlert : ""}`}>
              <div className={styles.cardTop}>
                <div><h3 className={styles.symbol}>{item.symbol}</h3><p className={styles.updated}>{item.lastUpdated ? `Updated ${formatTime(item.lastUpdated)}` : "Awaiting first price refresh"}</p></div>
                <div className={`${styles.priceBlock} ${item.currentLtp == null ? styles.pricePending : ""}`} aria-label={`Current LTP for ${item.symbol}`}>
                  <div className={styles.priceHead}>
                    <span className={styles.priceIcon}><IconActivity width={13} height={13} /></span>
                    <span className={styles.priceLabel}>Current LTP</span>
                  </div>
                  <strong className={`num ${styles.priceValue}`}>{item.currentLtp == null ? "—" : formatPrice(item.currentLtp)}</strong>
                </div>
                <div className={styles.cardActions}>
                  <Button variant="ghost" size="sm" onClick={() => setEditing(item)}><IconPencil width={14} height={14} />Edit</Button>
                  <Button variant="ghost" size="sm" onClick={() => void refreshSymbol(item.symbol)} loading={refreshingItem}>{!refreshingItem && <IconRefresh width={14} height={14} />}{refreshingItem ? "Fetching" : "Fetch"}</Button>
                  <Button variant="ghost" size="sm" className={styles.delete} onClick={() => void remove(item)}><IconTrash width={14} height={14} />Remove</Button>
                </div>
              </div>
              {item.notes && <p className={styles.notes}>{item.notes}</p>}
              <div className={styles.levels}>
                {item.levels.length === 0 ? <span className={styles.noLevelText}>No levels configured.</span> : item.levels.map((level) => { const meta = KIND_META[level.kind]; return <div className={styles.level} key={level.id}><span className={`${styles.kind} ${meta.className}`}>{meta.label}</span><span className={styles.levelName}>{level.label || "Price level"}</span><span className="num">{levelValue(level.lowerPrice, level.upperPrice)}</span><span className={`${styles.condition} ${level.conditionMet ? styles.triggered : ""}`}>{level.conditionMet ? "Triggered" : "Watching"}</span></div>; })}
              </div>
              {itemAlerts.length > 0 && <div className={styles.alertNote}>{itemAlerts.some((alert) => alert.kind === "entry-reached") ? "Entry zone reached" : `${itemAlerts.length} active ${itemAlerts.length === 1 ? "alert" : "alerts"}`} · refresh to reassess levels</div>}
              <Link className={styles.portfolioLink} href={prefill(item)}>Add to portfolio <IconArrowRight width={14} height={14} /></Link>
            </article>;
          })}
        </section>
      )}
    </AppShell>
  );
}
