"use client";

import { useState } from "react";
import type { EvidenceItem } from "@/lib/types";
import { parseBackendDate } from "@/lib/format";
import styles from "./evidence-panel.module.css";

const FRESHNESS_META: Record<string, string> = {
  FRESH: styles.fresh,
  RECENT: styles.recent,
  STALE: styles.stale,
  unknown: "",
};

function formatValue(item: EvidenceItem): string {
  const value = item.value;
  if (typeof value === "number") return String(value);
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function EvidencePanel({ items }: { items: EvidenceItem[] | null }) {
  const [open, setOpen] = useState(false);
  if (!items || items.length === 0) return null;

  return (
    <section className={styles.panel}>
      <button
        type="button"
        className={styles.toggle}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className={styles.toggleTitle}>
          Evidence used <span className={styles.count}>{items.length}</span>
        </span>
        <span className={styles.toggleHint}>{open ? "Hide" : "Show"}</span>
      </button>

      {open && (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item.id} className={styles.row}>
              <div className={styles.rowHead}>
                <span className={styles.id}>{item.id}</span>
                <span className={styles.label}>{item.label}</span>
                <span
                  className={`${styles.freshness} ${FRESHNESS_META[item.freshness] ?? ""}`}
                >
                  {item.freshness === "unknown" ? "age n/a" : item.freshness.toLowerCase()}
                </span>
              </div>
              <div className={styles.value}>{formatValue(item)}</div>
              <div className={styles.meta}>
                {item.unit && <span className={styles.unit}>{item.unit}</span>}
                <span className={styles.source}>{item.source}</span>
                {item.observedAt && (
                  <span className={styles.time}>
                    {parseBackendDate(item.observedAt).toLocaleString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </span>
                )}
                <span className={styles.confidence}>confidence: {item.confidence.toLowerCase()}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}