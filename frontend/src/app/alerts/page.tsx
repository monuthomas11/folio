"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { AlertsStrip } from "@/components/dashboard/alerts-strip";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { PortfolioAlert } from "@/lib/types";
import styles from "./page.module.css";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<PortfolioAlert[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAlerts(true);
      setAlerts(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDismiss = useCallback(async (id: string) => {
    await api.dismissAlert(id);
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const activeAlertCount = alerts.filter((a) => !a.dismissed).length;
  const dismissedAlerts = alerts.filter((a) => a.dismissed);

  return (
    <AppShell activeAlertCount={activeAlertCount}>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.overline}>
            <span className={styles.overlineDot} aria-hidden />
            Notifications
          </div>
          <h1 className={styles.pageTitle}>Alerts</h1>
          <p className={styles.pageSubtitle}>
            Stop-loss and target notifications — dismissed ones are archived below
          </p>
        </div>
      </header>

      {loading ? (
        <div className={styles.skeletonBlock}>
          <Skeleton width="5rem" height="1.2rem" />
          <Skeleton height="4.5rem" radius="var(--radius-lg)" />
        </div>
      ) : (
        <>
          <AlertsStrip alerts={alerts} onDismiss={handleDismiss} />

          {activeAlertCount === 0 && dismissedAlerts.length === 0 && (
            <div className={styles.empty}>
              <p className={styles.emptyTitle}>No alerts yet</p>
              <p className={styles.emptyBody}>
                Set a stop-loss and target on any holding &mdash; we&apos;ll flag the moment a price crosses one.
              </p>
            </div>
          )}

          {dismissedAlerts.length > 0 && (
            <section className={styles.archive}>
              <div className={styles.archiveHeader}>
                <h2 className={styles.archiveTitle}>Dismissed</h2>
                <span className={styles.archiveCount}>{dismissedAlerts.length}</span>
              </div>
              <ul className={styles.archiveList}>
                {dismissedAlerts.map((alert) => {
                  const isRisk = alert.kind === "sl-hit" || alert.kind === "stop-loss-hit" || alert.kind === "invalidation-hit";
                  const label = alert.kind === "entry-reached"
                    ? "Entry reached"
                    : alert.kind === "target-reached" || alert.kind === "target-hit"
                      ? "Target reached"
                      : alert.kind === "invalidation-hit"
                        ? "Invalidation hit"
                        : "Stop-loss hit";
                  return (
                    <li key={alert.id} className={styles.archiveItem}>
                      <div>
                        <Link className={styles.archiveSymbol} href={alert.watchlistItemId ? "/watchlist" : alert.holdingId ? `/holdings/${alert.holdingId}` : "/alerts"}>{alert.symbol}</Link>
                        <span className={`${styles.archiveKind} ${isRisk ? styles.kindSl : styles.kindTarget}`}>
                          {label}
                        </span>
                      </div>
                      <span className={styles.archiveMeta}>
                        {formatDate(alert.createdAt)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </>
      )}
    </AppShell>
  );
}
