import { holdingStats } from "@/lib/holdings";
import { formatINRFractionless } from "@/lib/format";
import { IconPieChart } from "@/components/icons";
import type { Holding } from "@/lib/types";
import styles from "./sector-allocation.module.css";

interface SectorAllocationProps {
  holdings: Holding[];
}

const PALETTE = [
  "oklch(0.43 0.085 170)",
  "oklch(0.47 0.17 27)",
  "oklch(0.47 0.13 152)",
  "oklch(0.55 0.1 75)",
  "oklch(0.5 0.08 220)",
  "oklch(0.6 0.06 300)",
  "oklch(0.52 0.12 25)",
  "oklch(0.48 0.14 190)",
  "oklch(0.58 0.11 45)",
  "oklch(0.54 0.09 280)",
];

export function SectorAllocation({ holdings }: SectorAllocationProps) {
  const withLtp = holdings.filter((h) => h.currentLtp != null);
  if (withLtp.length === 0) return null;

  const map = new Map<string, number>();
  let total = 0;
  for (const h of withLtp) {
    const sector = h.sector?.trim() ? h.sector.trim() : "Unclassified";
    const value = holdingStats(h).currentValue;
    map.set(sector, (map.get(sector) ?? 0) + value);
    total += value;
  }

  const rows = Array.from(map.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([sector, value], i) => ({
      sector,
      value,
      pct: total > 0 ? (value / total) * 100 : 0,
      color: PALETTE[i % PALETTE.length],
    }));

  let acc = 0;
  const segments = rows.map((r) => {
    const start = acc;
    acc += r.pct;
    return `${r.color} ${start.toFixed(2)}% ${acc.toFixed(2)}%`;
  });

  return (
    <section className={styles.wrap}>
      <div className={styles.header}>
        <IconPieChart width={15} height={15} />
        <h2 className={styles.title}>Sector allocation</h2>
      </div>
      <div className={styles.body}>
        <div
          className={styles.donut}
          style={{
            background: `conic-gradient(${segments.join(", ")})`,
          }}
          role="img"
          aria-label={`Allocation across ${rows.length} sectors`}
        />
        <ul className={styles.legend}>
          {rows.map((r) => (
            <li key={r.sector} className={styles.legendRow}>
              <span
                className={styles.swatch}
                style={{ background: r.color }}
                aria-hidden
              />
              <span className={styles.sector}>{r.sector}</span>
              <span className={`num ${styles.pct}`}>{r.pct.toFixed(0)}%</span>
              <span className={`num ${styles.value}`}>
                {formatINRFractionless(r.value)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}