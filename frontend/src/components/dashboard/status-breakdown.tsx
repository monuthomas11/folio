import { holdingStats } from "@/lib/holdings";
import { IconActivity } from "@/components/icons";
import type { Holding } from "@/lib/types";
import styles from "./status-breakdown.module.css";

interface StatusBreakdownProps {
  holdings: Holding[];
}

export function StatusBreakdown({ holdings }: StatusBreakdownProps) {
  let healthy = 0;
  let nearSl = 0;
  let slHit = 0;
  let targetHit = 0;
  let noLtp = 0;

  for (const h of holdings) {
    if (h.currentLtp == null) {
      noLtp += 1;
      continue;
    }
    const s = holdingStats(h).status;
    if (s === "healthy") healthy += 1;
    else if (s === "near-sl") nearSl += 1;
    else if (s === "sl-hit") slHit += 1;
    else if (s === "target-hit") targetHit += 1;
  }

  const total = holdings.length || 1;

  const bars: { label: string; count: number; tone: string }[] = [
    { label: "Target hit", count: targetHit, tone: styles.gain },
    { label: "Healthy", count: healthy, tone: styles.healthy },
    { label: "Near SL", count: nearSl, tone: styles.warn },
    { label: "SL hit", count: slHit, tone: styles.danger },
    { label: "No price", count: noLtp, tone: styles.muted },
  ];

  return (
    <section className={styles.wrap}>
      <div className={styles.header}>
        <IconActivity width={15} height={15} />
        <h2 className={styles.title}>Position health</h2>
      </div>
      <div className={styles.bars}>
        {bars.map(
          (b) =>
            b.count > 0 && (
              <div key={b.label} className={styles.barRow}>
                <div className={styles.barMeta}>
                  <span className={styles.barLabel}>{b.label}</span>
                  <span className={`num ${styles.barCount}`}>{b.count}</span>
                </div>
                <div className={styles.track}>
                  <div
                    className={`${styles.fill} ${b.tone}`}
                    style={{
                      width: `${(b.count / total) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ),
        )}
      </div>
    </section>
  );
}
