"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { HoldingsTable } from "@/components/dashboard/holdings-table";
import { AddHoldingForm } from "@/components/portfolio/add-holding-form";
import { ImportExport } from "@/components/portfolio/import-export";
import { ExitHoldingDialog } from "@/components/portfolio/exit-holding-dialog";
import { RealizedTrades } from "@/components/portfolio/realized-trades";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { AnalysisRating, Holding, HoldingExit, HoldingsInput, PortfolioAlert, PortfolioSummary } from "@/lib/types";
import styles from "./page.module.css";

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [alerts, setAlerts] = useState<PortfolioAlert[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [realizedExits, setRealizedExits] = useState<HoldingExit[]>([]);
  const [aiRatings, setAiRatings] = useState<Record<string, AnalysisRating>>({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [refreshingSymbols, setRefreshingSymbols] = useState<Set<string>>(new Set());
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());
  const [exitingIds, setExitingIds] = useState<Set<string>>(new Set());
  const [exitTarget, setExitTarget] = useState<Holding | null>(null);
  const [exitError, setExitError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Holding | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await api.getSnapshot();
      setSummary(data.summary);
      setHoldings(data.holdings);
      setAlerts(data.alerts);
      setRealizedExits(data.realizedExits);
      setLastUpdated(
        data.holdings
          .map((h) => h.lastUpdated)
          .filter(Boolean)
          .sort()
          .at(-1) ?? null,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load your portfolio.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    api
      .getLatestPortfolioAnalysis()
      .then((latest) => {
        if (!latest) return;
        const map: Record<string, AnalysisRating> = {};
        for (const rec of latest.holdings) map[rec.symbol] = rec.rating;
        setAiRatings(map);
      })
      .catch(() => {
        // Analysis availability is optional on this page.
      });
  }, []);

  const handleAdded = useCallback(
    async (input: HoldingsInput) => {
      await api.addHolding(input);
      await load();
    },
    [load],
  );

  const handleUpdated = useCallback(
    async (id: string, input: HoldingsInput) => {
      await api.updateHolding(id, input);
      setEditing(null);
      await load();
    },
    [load],
  );

  const handleDelete = useCallback(
    async (holding: Holding) => {
      if (
        !window.confirm(
          `Remove ${holding.symbol} from your portfolio? Its saved alerts will also be removed.`,
        )
      ) {
        return;
      }
      setError(null);
      setRemovingIds((prev) => new Set(prev).add(holding.id));
      try {
        await api.deleteHolding(holding.id);
        if (editing?.id === holding.id) setEditing(null);
        await load(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Couldn't remove the holding.");
      } finally {
        setRemovingIds((prev) => {
          const next = new Set(prev);
          next.delete(holding.id);
          return next;
        });
      }
    },
    [load, editing],
  );

  const handleRefreshRow = useCallback(
    async (symbol: string) => {
      setRefreshingSymbols((prev) => new Set(prev).add(symbol));
      try {
        await api.refreshSymbol(symbol);
        await load();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Price refresh failed.");
      } finally {
        setRefreshingSymbols((prev) => {
          const next = new Set(prev);
          next.delete(symbol);
          return next;
        });
      }
    },
    [load],
  );

  const handleExit = useCallback((holding: Holding) => {
    setExitError(null);
    setExitTarget(holding);
  }, []);

  const handleExitSubmit = useCallback(
    async (input: { quantity: number; exitPrice: number }) => {
      if (!exitTarget) return;
      setExitError(null);
      setExitingIds((prev) => new Set(prev).add(exitTarget.id));
      try {
        await api.exitHolding(exitTarget.id, input);
        setExitTarget(null);
        await load(true);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Couldn't record the exit.";
        setExitError(message);
        throw err;
      } finally {
        setExitingIds((prev) => {
          const next = new Set(prev);
          next.delete(exitTarget.id);
          return next;
        });
      }
    },
    [exitTarget, load],
  );

  const activeAlerts = alerts.filter((a) => !a.dismissed).length;

  return (
    <AppShell activeAlertCount={activeAlerts}>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.overline}>
            <span className={styles.overlineDot} aria-hidden />
            Holdings
          </div>
          <h1 className={styles.pageTitle}>Portfolio</h1>
          <p className={styles.pageSubtitle}>Your holdings, prices, and levels</p>
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

      <AddHoldingForm
        onAdded={handleAdded}
        onUpdated={handleUpdated}
        editing={editing}
        onCancelEdit={() => setEditing(null)}
      />

      <div className={styles.transferBar}>
        <ImportExport
          disabled={holdings.length === 0}
          onImported={load}
          onError={(message) => setError(message)}
        />
      </div>

      {summary && <RealizedTrades summary={summary} exits={realizedExits} />}

      <section className={styles.tableSection}>
        {loading ? (
          <div className={styles.skeletonBlock}>
            <Skeleton width="6rem" height="1.2rem" />
            <Skeleton height="18rem" radius="var(--radius-lg)" />
          </div>
        ) : holdings.length === 0 ? (
          <div className={styles.emptyCard}>
            <p className={styles.emptyText}>
              No holdings yet. Add your first position above.
            </p>
          </div>
        ) : (
          <HoldingsTable
            holdings={holdings}
            refreshingSymbols={refreshingSymbols}
            onRefreshRow={handleRefreshRow}
            onEdit={setEditing}
            onDelete={handleDelete}
            onExit={handleExit}
            removingIds={removingIds}
            exitingIds={exitingIds}
            lastUpdated={lastUpdated}
            aiRatings={aiRatings}
          />
        )}
      </section>

      {exitTarget && (
        <ExitHoldingDialog
          holding={exitTarget}
          onClose={() => !exitingIds.has(exitTarget.id) && setExitTarget(null)}
          onSubmit={handleExitSubmit}
          error={exitError}
        />
      )}
    </AppShell>
  );
}
