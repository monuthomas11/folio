"use client";

import Link from "next/link";
import type { PortfolioAlert } from "@/lib/types";
import { parseBackendDate } from "@/lib/format";
import { IconArrowDown, IconArrowUp, IconClose, IconTrendDown, IconTrendUp } from "@/components/icons";
import styles from "./alerts-strip.module.css";

interface AlertsStripProps {
  alerts: PortfolioAlert[];
  onDismiss: (id: string) => void;
  compact?: boolean;
}

function alertLabel(kind: PortfolioAlert["kind"]): string {
  if (kind === "entry-reached") return "reached an entry level";
  if (kind === "invalidation-hit") return "hit an invalidation level";
  if (kind === "stop-loss-hit" || kind === "sl-hit") return "hit its stop-loss";
  if (kind === "target-reached") return "reached a target";
  return "reached its target";
}

export function AlertsStrip({ alerts, onDismiss, compact }: AlertsStripProps) {
  const active = alerts.filter((alert) => !alert.dismissed);
  if (active.length === 0) return null;

  return (
    <div className={`${styles.strip} ${compact ? styles.compact : ""}`}>
      <div className={styles.header}><h2 className={styles.heading}>Alerts</h2><span className={styles.count}>{active.length}</span></div>
      <ul className={styles.list}>
        {active.map((alert) => {
          const isRisk = alert.kind === "sl-hit" || alert.kind === "stop-loss-hit" || alert.kind === "invalidation-hit";
          const Icon = isRisk ? IconTrendDown : IconTrendUp;
          const Arrow = isRisk ? IconArrowDown : IconArrowUp;
          const destination = alert.watchlistItemId ? "/watchlist" : alert.holdingId ? `/holdings/${alert.holdingId}` : "/alerts";
          return (
            <li key={alert.id} className={`${styles.alert} ${isRisk ? styles.sl : styles.target}`}>
              <span className={styles.iconWrap}><Icon width={16} height={16} /></span>
              <div className={styles.body}>
                <p className={styles.message}><Link href={destination}><strong>{alert.symbol}</strong></Link>{" "}{alertLabel(alert.kind)} at <span className={`num ${styles.price}`}>₹{alert.price.toFixed(2)}</span></p>
                <span className={styles.meta}>Triggered {new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit", hour12: true }).format(parseBackendDate(alert.createdAt))}</span>
              </div>
              <Link href={destination} className={styles.arrow} aria-label={`Open ${alert.symbol}`}><Arrow width={15} height={15} /></Link>
              <button type="button" className={styles.dismiss} onClick={() => onDismiss(alert.id)} aria-label={`Dismiss alert for ${alert.symbol}`}><IconClose width={14} height={14} /></button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
