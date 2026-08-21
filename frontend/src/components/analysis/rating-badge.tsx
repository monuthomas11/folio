import type { AnalysisRating } from "@/lib/types";
import styles from "./rating-badge.module.css";

const RATING_META: Record<AnalysisRating, { tone: string; label: string }> = {
  BUY: { tone: styles.buy, label: "BUY" },
  HOLD: { tone: styles.hold, label: "HOLD" },
  REDUCE: { tone: styles.reduce, label: "REDUCE" },
  EXIT: { tone: styles.exit, label: "EXIT" },
};

export function RatingBadge({
  rating,
  size = "md",
}: {
  rating: AnalysisRating;
  size?: "sm" | "md";
}) {
  const meta = RATING_META[rating] ?? { tone: styles.hold, label: rating };
  return (
    <span
      className={`${styles.badge} ${meta.tone} ${size === "sm" ? styles.sm : ""}`}
    >
      {meta.label}
    </span>
  );
}