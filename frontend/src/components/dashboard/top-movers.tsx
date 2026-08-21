import { holdingStats } from "@/lib/holdings";
import { formatPrice, formatSigned } from "@/lib/format";
import { IconTrendUp, IconTrendDown } from "@/components/icons";
import type { Holding } from "@/lib/types";
import styles from "./top-movers.module.css";

interface TopMoversProps {
  holdings: Holding[];
}

export function TopMovers({ holdings }: TopMoversProps) {
  if (holdings.length === 0) return null;

  const computed = holdings
    .filter((h) => h.currentLtp != null)
    .map((h) => ({ holding: h, stats: holdingStats(h) }))
    .sort((a, b) => b.stats.pnlPct - a.stats.pnlPct);

  const gainers = computed.filter(({ stats }) => stats.pnlPct >= 0).slice(0, 3);
  const losers = computed.filter(({ stats }) => stats.pnlPct < 0).slice(-3).reverse();

  const showGainers = gainers.length > 0;
  const showLosers = losers.length > 0;

  if (!showGainers && !showLosers) return null;

  return (
    <section className={styles.wrap}>
      <div className={styles.header}>
        <h2 className={styles.title}>Top movers</h2>
      </div>
      <div className={styles.grids}>
        {showGainers && (
          <div className={styles.col}>
            <span className={styles.colLabel}>
              <IconTrendUp width={13} height={13} />
              Top gainers
            </span>
            <ul className={styles.list}>
              {gainers.map(({ holding, stats }) => (
                <li key={holding.id} className={styles.row}>
                  <div className={styles.symbolBlock}>
                    <span className={styles.symbol}>{holding.symbol}</span>
                    {holding.broker && (
                      <span className={styles.broker}>{holding.broker}</span>
                    )}
                  </div>
                  <div className={styles.numBlock}>
                    <span className={`num ${styles.change}`}>
                      {formatPrice(holding.currentLtp!)}
                    </span>
                    <span className={`num ${styles.gainPct}`}>
                      {formatSigned(stats.pnlPct)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
        {showLosers && (
          <div className={styles.col}>
            <span className={styles.colLabel}>
              <IconTrendDown width={13} height={13} />
              Top losers
            </span>
            <ul className={styles.list}>
              {losers.map(({ holding, stats }) => (
                <li key={holding.id} className={styles.row}>
                  <div className={styles.symbolBlock}>
                    <span className={styles.symbol}>{holding.symbol}</span>
                    {holding.broker && (
                      <span className={styles.broker}>{holding.broker}</span>
                    )}
                  </div>
                  <div className={styles.numBlock}>
                    <span className={`num ${styles.change}`}>
                      {formatPrice(holding.currentLtp!)}
                    </span>
                    <span className={`num ${styles.lossPct}`}>
                      {formatSigned(stats.pnlPct)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
