import type { ReactNode } from "react";
import styles from "./status-pill.module.css";

export type StatusTone = "healthy" | "warn" | "danger" | "gain" | "neutral";

interface StatusPillProps {
  tone: StatusTone;
  children: ReactNode;
  label?: string;
}

export function StatusPill({ tone, children, label }: StatusPillProps) {
  return (
    <span
      className={`${styles.pill} ${styles[tone]}`}
      role={label ? "status" : undefined}
      aria-label={label}
    >
      <span className={styles.dot} aria-hidden />
      {children}
    </span>
  );
}