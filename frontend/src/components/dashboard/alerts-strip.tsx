"use client";

import type { PortfolioAlert } from "@/lib/types";
import { parseBackendDate } from "@/lib/format";
import {
  IconArrowDown,
  IconArrowUp,
  IconClose,
  IconTrendDown,
  IconTrendUp,
} from "@/components/icons";
import styles from "./alerts-strip.module.css";

interface AlertsStripProps {
  alerts: PortfolioAlert[];
  onDismiss: (id: string) => void;
  compact?: boolean;
}

export function AlertsStrip({ alerts, onDismiss, compact }: AlertsStripProps) {
  const active = alerts.filter((a) => !a.dismissed);
  if (active.length === 0) return null;

  const className = `${styles.strip} ${compact ? styles.compact : ""}`;

  return (
    <div className={className}>
      <div className={styles.header}>
        <h2 className={styles.heading}>Alerts</h2>
        <span className={styles.count}>{active.length}</span>
      </div>
      <ul className={styles.list}>
        {active.map((alert) => {
          const isSl = alert.kind === "sl-hit";
          const Icon = isSl ? IconTrendDown : IconTrendUp;
          const Arrow = isSl ? IconArrowDown : IconArrowUp;
          const tone = isSl ? styles.sl : styles.target;
          return (
            <li key={alert.id} className={`${styles.alert} ${tone}`}>
              <span className={styles.iconWrap}>
                <Icon width={16} height={16} />
              </span>
              <div className={styles.body}>
                <p className={styles.message}>
                  <strong>{alert.symbol}</strong>{" "}
                  {isSl
                    ? `hit its stop-loss at`
                    : `reached its target at`}{" "}
                  <span className={`num ${styles.price}`}>
                    ₹{alert.price.toFixed(2)}
                  </span>
                </p>
                <span className={styles.meta}>
                  Triggered{" "}
                  {new Intl.DateTimeFormat("en-IN", {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  }).format(parseBackendDate(alert.createdAt))}
                </span>
              </div>
              <span className={styles.arrow}>
                <Arrow width={15} height={15} />
              </span>
              <button
                type="button"
                className={styles.dismiss}
                onClick={() => onDismiss(alert.id)}
                aria-label={`Dismiss alert for ${alert.symbol}`}
              >
                <IconClose width={14} height={14} />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}