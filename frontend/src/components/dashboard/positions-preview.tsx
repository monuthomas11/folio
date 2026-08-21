import Link from "next/link";
import { holdingStats } from "@/lib/holdings";
import { formatINRFractionless, formatPrice, formatSigned } from "@/lib/format";
import { IconArrowRight } from "@/components/icons";
import type { Holding } from "@/lib/types";
import styles from "./positions-preview.module.css";

interface PositionsPreviewProps {
  holdings: Holding[];
}

export function PositionsPreview({ holdings }: PositionsPreviewProps) {
  if (holdings.length === 0) return null;

  const rows = holdings
    .map((h) => ({ holding: h, stats: holdingStats(h) }))
    .sort((a, b) => b.stats.currentValue - a.stats.currentValue)
    .slice(0, 5);

  return (
    <section className={styles.wrap}>
      <div className={styles.header}>
        <h2 className={styles.title}>Largest positions</h2>
        <Link href="/portfolio" className={styles.seeAll}>
          View all
          <IconArrowRight width={14} height={14} />
        </Link>
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Symbol</th>
              <th scope="col" className="num numeric">
                Qty
              </th>
              <th scope="col" className="num numeric">
                LTP
              </th>
              <th scope="col" className="num numeric">
                Value
              </th>
              <th scope="col" className="num numeric">
                P/L
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ holding, stats }) => {
              const gain = stats.pnl >= 0;
              return (
                <tr key={holding.id}>
                  <td>
                    <span className={styles.symbol}>{holding.symbol}</span>
                    {holding.broker && (
                      <span className={styles.broker}>{holding.broker}</span>
                    )}
                  </td>
                  <td className="num numeric">
                    {holding.quantity.toLocaleString("en-IN")}
                  </td>
                  <td className="num numeric">
                    {holding.currentLtp != null
                      ? formatPrice(holding.currentLtp)
                      : "—"}
                  </td>
                  <td className="num numeric">
                    {formatINRFractionless(stats.currentValue)}
                  </td>
                  <td className="num numeric">
                    <span className={gain ? styles.gain : styles.loss}>
                      {formatSigned(stats.pnlPct)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
