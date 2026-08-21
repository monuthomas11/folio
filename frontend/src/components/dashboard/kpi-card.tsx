import type { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { IconArrowUp, IconArrowDown } from "@/components/icons";
import styles from "./kpi-card.module.css";

export interface KpiCardProps {
  label: string;
  value: string;
  sub?: ReactNode;
  accent?: "default" | "gain" | "loss";
  loading?: boolean;
}

export function KpiCard({ label, value, sub, accent = "default", loading }: KpiCardProps) {
  const showTrend = !loading && (accent === "gain" || accent === "loss");
  const Trend = accent === "gain" ? IconArrowUp : IconArrowDown;
  return (
    <div className={`${styles.card} ${styles[accent]}`}>
      <span className={styles.label}>
        {label}
        <span className={styles.marker} aria-hidden />
      </span>
      {loading ? (
        <Skeleton width="9rem" height="2rem" radius="var(--radius-md)" className={styles.skel} />
      ) : (
        <span className={`${styles.value} num`}>
          {value}
          {showTrend && (
            <span className={`${styles.trend} ${accent === "gain" ? styles.trendUp : styles.trendDown}`}>
              <Trend width={13} height={13} />
            </span>
          )}
        </span>
      )}
      {loading ? (
        <Skeleton width="6rem" height="0.9rem" />
      ) : (
        sub && <div className={styles.sub}>{sub}</div>
      )}
    </div>
  );
}