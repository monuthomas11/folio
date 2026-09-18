import { formatINRFractionless, formatPrice, formatQuantity, formatSigned, formatSignedINR, parseBackendDate } from "@/lib/format";
import type { HoldingExit, PortfolioSummary } from "@/lib/types";
import styles from "./realized-trades.module.css";

interface RealizedTradesProps {
  summary: PortfolioSummary;
  exits: HoldingExit[];
}

export function RealizedTrades({ summary, exits }: RealizedTradesProps) {
  return (
    <section className={styles.panel} aria-labelledby="realized-trades-title">
      <div className={styles.header}>
        <div>
          <h2 id="realized-trades-title">Realized P/L</h2>
          <p>Recorded exits across your portfolio</p>
        </div>
        <div className={summary.realizedPnl >= 0 ? styles.totalGain : styles.totalLoss}>
          <strong>{formatSignedINR(summary.realizedPnl)}</strong>
          <span>{formatSigned(summary.realizedPnlPct)} return</span>
        </div>
      </div>

      {exits.length === 0 ? (
        <p className={styles.empty}>No exits recorded yet. Closed positions will appear here.</p>
      ) : (
        <div className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Exited</th>
                <th>Qty</th>
                <th>Exit price</th>
                <th>Cost basis</th>
                <th>Realized P/L</th>
              </tr>
            </thead>
            <tbody>
              {exits.map((exit) => (
                <tr key={exit.id}>
                  <td>
                    <strong>{exit.symbol}</strong>
                    {exit.broker && <span>{exit.broker}</span>}
                  </td>
                  <td>{new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(parseBackendDate(exit.exitedAt))}</td>
                  <td className="num">{formatQuantity(exit.quantity)}</td>
                  <td className="num">{formatPrice(exit.exitPrice)}</td>
                  <td className="num">{formatINRFractionless(exit.costBasis)}</td>
                  <td className={`num ${exit.realizedPnl >= 0 ? styles.gain : styles.loss}`}>
                    {formatSignedINR(exit.realizedPnl)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
