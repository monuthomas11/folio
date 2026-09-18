"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { AlertsStrip } from "@/components/dashboard/alerts-strip";
import { TopMovers } from "@/components/dashboard/top-movers";
import { SectorAllocation } from "@/components/dashboard/sector-allocation";
import { StatusBreakdown } from "@/components/dashboard/status-breakdown";
import { PositionsPreview } from "@/components/dashboard/positions-preview";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { IconPlus, IconRefresh, IconTrendDown, IconTrendUp } from "@/components/icons";
import { api } from "@/lib/api";
import { holdingStats } from "@/lib/holdings";
import { formatDate, formatINRFractionless, formatSigned, formatSignedINR } from "@/lib/format";
import type { Holding, PortfolioAlert, PortfolioSummary } from "@/lib/types";
import styles from "./page.module.css";

export default function DashboardPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [alerts, setAlerts] = useState<PortfolioAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await api.getSnapshot();
      setSummary(data.summary);
      setHoldings(data.holdings);
      setAlerts(data.alerts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load your portfolio.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRefreshAll = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      await api.refreshAll();
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Price refresh failed.");
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  const handleDismiss = useCallback(async (id: string) => {
    await api.dismissAlert(id);
    setAlerts((prev) => prev.filter((a) => a.id !== id));
    setSummary((prev) =>
      prev ? { ...prev, activeAlertCount: Math.max(0, prev.activeAlertCount - 1) } : prev,
    );
  }, []);

  const gainersLosers = useMemo(() => {
    let gainers = 0;
    let losers = 0;
    for (const h of holdings) {
      if (holdingStats(h).pnl >= 0) gainers += 1;
      else losers += 1;
    }
    return { gainers, losers };
  }, [holdings]);

  const activeAlerts = alerts.filter((a) => !a.dismissed).length;

  return (
    <AppShell activeAlertCount={activeAlerts}>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.overline}>
            <span className={styles.overlineDot} aria-hidden />
            Portfolio overview
          </div>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <p className={styles.pageSubtitle}>
            Your portfolio at a glance — {formatDate(new Date().toISOString())}
          </p>
        </div>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            onClick={handleRefreshAll}
            loading={refreshing}
            disabled={loading || holdings.length === 0}
          >
            {!refreshing && <IconRefresh width={15} height={15} />}
            {refreshing ? "Refreshing" : "Refresh prices"}
          </Button>
          <Button asChild variant="primary" className={styles.newBtn}>
            <Link href="/portfolio">Add holding</Link>
          </Button>
        </div>
      </header>

      {error && (
        <div className={styles.error} role="alert">
          <span>{error}</span>
          <button type="button" className={styles.retry} onClick={() => void load()}>
            Retry
          </button>
        </div>
      )}

      <section className={styles.kpiRow} aria-label="Portfolio summary">
        <KpiCard
          label="Portfolio value"
          value={summary ? formatINRFractionless(summary.portfolioValue) : "—"}
          sub={
            summary && summary.holdingCount > 0
              ? `${summary.holdingCount} positions`
              : "No holdings yet"
          }
          loading={loading}
        />
        <KpiCard
          label="Invested"
          value={summary ? formatINRFractionless(summary.invested) : "—"}
          sub={summary ? "Total capital deployed" : undefined}
          loading={loading}
        />
        <KpiCard
          label="Total P/L"
          value={summary ? formatINRFractionless(summary.totalPnl) : "—"}
          sub={
            summary
              ? `${formatSigned(summary.totalPnlPct)} overall return`
              : undefined
          }
          accent={summary ? (summary.totalPnl >= 0 ? "gain" : "loss") : "default"}
          loading={loading}
        />
        <KpiCard
          label="In profit"
          value={
            loading
              ? "—"
              : holdings.length > 0
                ? `${Math.round((gainersLosers.gainers / holdings.length) * 100)}%`
                : "0%"
          }
          sub={
            <span className={styles.breadth}>
              <IconTrendUp width={13} height={13} />
              {gainersLosers.gainers} up
              <span className={styles.breadthSep} aria-hidden>
                ·
              </span>
              <IconTrendDown width={13} height={13} />
              {gainersLosers.losers} down
            </span>
          }
          loading={loading}
        />
        <KpiCard
          label="Realized P/L"
          value={summary ? formatSignedINR(summary.realizedPnl) : "—"}
          sub={
            summary
              ? summary.closedTradeCount > 0
                ? `${summary.closedTradeCount} recorded ${summary.closedTradeCount === 1 ? "exit" : "exits"}`
                : "No exits recorded"
              : undefined
          }
          accent={summary ? (summary.realizedPnl >= 0 ? "gain" : "loss") : "default"}
          loading={loading}
        />
      </section>

      {loading ? (
        <section className={styles.skeletonBlock} aria-label="Loading alerts">
          <Skeleton width="7rem" height="1.2rem" />
          <Skeleton height="4.5rem" radius="var(--radius-lg)" />
        </section>
      ) : (
        <AlertsStrip alerts={alerts} onDismiss={handleDismiss} compact />
      )}

      {loading ? (
        <section className={styles.tableSkeleton} aria-label="Loading insights">
          <Skeleton width="8rem" height="1.2rem" />
          <div className={styles.gridRowSkeleton}>
            <Skeleton height="14rem" radius="var(--radius-lg)" />
            <Skeleton height="14rem" radius="var(--radius-lg)" />
          </div>
        </section>
      ) : holdings.length === 0 ? (
        <EmptyState onAdd="/portfolio" />
      ) : (
        <section className={styles.insights} aria-label="Portfolio insights">
          <div className={styles.insightsTop}>
            <div className={styles.panel}>
              <TopMovers holdings={holdings} />
            </div>
            <div className={styles.panel}>
              <SectorAllocation holdings={holdings} />
            </div>
          </div>
          <div className={styles.insightsBottom}>
            <div className={styles.panel}>
              <StatusBreakdown holdings={holdings} />
            </div>
            <div className={styles.panelWide}>
              <PositionsPreview holdings={holdings} />
            </div>
          </div>
        </section>
      )}
    </AppShell>
  );
}

function EmptyState({ onAdd }: { onAdd: string }) {
  return (
    <div className={styles.empty}>
      <div className={styles.emptyIcon} aria-hidden>
        <IconPlus width={20} height={20} />
      </div>
      <h2 className={styles.emptyTitle}>Your portfolio is empty</h2>
      <p className={styles.emptyBody}>
        Add your first holding to start tracking prices, stop-losses, and targets.
      </p>
      <Button asChild variant="primary">
        <Link href={onAdd}>Add your first holding</Link>
      </Button>
    </div>
  );
}
