"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { AnalyzeButton } from "@/components/analysis/analyze-button";
import { RatingBadge } from "@/components/analysis/rating-badge";
import { StatusPill } from "@/components/ui/status-pill";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDate, formatTime } from "@/lib/format";
import type {
  LatestAnalysisRunInfo,
  LatestPortfolioAnalysis,
  Recommendation,
} from "@/lib/types";
import styles from "./page.module.css";

const DATA_QUALITY_TONES: Record<string, "healthy" | "warn" | "gain" | "danger" | "neutral"> = {
  EXCELLENT: "gain",
  GOOD: "healthy",
  MODERATE: "warn",
  POOR: "danger",
};

function healthTone(score: number | null): "gain" | "healthy" | "warn" | "danger" {
  if (score == null) return "healthy";
  if (score >= 80) return "gain";
  if (score >= 60) return "healthy";
  if (score >= 40) return "warn";
  return "danger";
}

function HealthScore({ score }: { score: number | null }) {
  const tone = healthTone(score);
  const hint =
    score == null
      ? "Not available"
      : score >= 80
        ? "Strong"
        : score >= 60
          ? "Adequate"
          : score >= 40
            ? "Needs attention"
            : "Urgent review";
  return (
    <section className={`${styles.healthCard} ${styles[tone]}`}>
      <div className={styles.healthInfo}>
        <span className={styles.healthLabel}>Portfolio health score</span>
        <span className={styles.healthHint}>{hint}</span>
      </div>
      <div className={styles.healthScore}>
        <span className={`num ${styles.healthValue}`}>{score != null ? score : "—"}</span>
        {score != null && <span className={styles.healthUnit}>/ 100</span>}
      </div>
    </section>
  );
}

function providerLabel(run: LatestAnalysisRunInfo | null): string | null {
  if (!run) return null;
  if (run.provider === "mock") return "Mock analysis";
  const model = run.modelName ? ` (${run.modelName})` : "";
  return `${run.provider} AI${model}`;
}

function isMock(run: LatestAnalysisRunInfo | null): boolean {
  return run?.provider === "mock";
}

function ListBlock({ title, items, tone }: { title: string; items: string[]; tone?: string }) {
  if (!items.length) return null;
  return (
    <section className={styles.card}>
      <header className={styles.cardHead}>
        <h2 className={styles.cardTitle}>{title}</h2>
        <span className={styles.countBadge}>{items.length}</span>
      </header>
      <ul className={styles.list}>
        {items.map((item, i) => (
          <li key={i} className={tone ? `${styles.listItem} ${styles[tone]}` : styles.listItem}>
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function PortfolioView({ data }: { data: LatestPortfolioAnalysis }) {
  const portfolio = data.portfolio;
  const generatedAt = portfolio?.analysisTimestamps?.generatedAt;
  const lastRun = data.lastRun;
  const lastRunAt = lastRun?.completedAt ?? lastRun?.createdAt;
  const provider = providerLabel(lastRun);

  return (
    <div className={styles.wrap}>
      {portfolio && <HealthScore score={portfolio.healthScore} />}

      {portfolio?.priorityNote && (
        <section className={styles.priority}>
          <span className={styles.priorityLabel}>Priority</span>
          <p className={styles.priorityText}>{portfolio.priorityNote}</p>
        </section>
      )}

      <div className={styles.grid}>
        <ListBlock title="Positives" items={portfolio?.positives ?? []} tone="positive" />
        <ListBlock title="Concerns" items={portfolio?.concerns ?? []} tone="concern" />
      </div>

      {data.holdings.length > 0 && (
        <section className={styles.actionsSection}>
          <div className={styles.sectionHead}>
            <h2 className={styles.sectionTitle}>Per-stock actions</h2>
            <span className={styles.rowCount}>
              {data.holdings.length} {data.holdings.length === 1 ? "stock" : "stocks"}
            </span>
          </div>
          <div className={styles.tableScroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col" className={styles.thSymbol}>
                    Symbol
                  </th>
                  <th scope="col" className={styles.numHeader}>
                    Weight
                  </th>
                  <th scope="col">Rating</th>
                  <th scope="col">Action</th>
                  <th scope="col" className={styles.numHeader}>
                    Confidence
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.holdings.map((rec: Recommendation) => (
                  <tr key={rec.holdingId ?? rec.id}>
                    <td>
                      {rec.holdingId ? (
                        <Link href={`/holdings/${rec.holdingId}`} className={styles.symbolLink}>
                          {rec.symbol}
                        </Link>
                      ) : (
                        <span className={styles.symbolLink}>{rec.symbol}</span>
                      )}
                    </td>
                    <td className={`num ${styles.numeric}`}>
                      {rec.portfolioWeight != null
                        ? `${rec.portfolioWeight}%`
                        : "—"}
                    </td>
                    <td>
                      <RatingBadge rating={rec.rating} size="sm" />
                    </td>
                    <td>
                      <span className={styles.action}>{rec.action.replace(/_/g, " ")}</span>
                    </td>
                    <td className={`num ${styles.numeric}`}>
                      {rec.confidence != null ? `${rec.confidence}/100` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className={styles.stockCards}>
            {data.holdings.map((rec: Recommendation) => (
              <article key={rec.holdingId ?? rec.id} className={styles.stockCard}>
                <header className={styles.stockHead}>
                  <span className={styles.stockSymbol}>{rec.symbol}</span>
                  <RatingBadge rating={rec.rating} size="sm" />
                </header>
                <dl className={styles.stockGrid}>
                  <div>
                    <dt>Weight</dt>
                    <dd className="num">
                      {rec.portfolioWeight != null
                        ? `${rec.portfolioWeight}%`
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>Confidence</dt>
                    <dd className="num">
                      {rec.confidence != null ? `${rec.confidence}/100` : "—"}
                    </dd>
                  </div>
                </dl>
                <div className={styles.stockFoot}>
                  <span className={styles.stockAction}>
                    {rec.action.replace(/_/g, " ")}
                  </span>
                  {rec.holdingId && (
                    <Link href={`/holdings/${rec.holdingId}`} className={styles.detailLink}>
                      View
                    </Link>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {portfolio && (
        <div className={styles.meta}>
          {lastRun && (
            <StatusPill tone={isMock(lastRun) ? "warn" : "gain"}>
              Last analyzed {lastRunAt ? `${formatDate(lastRunAt)} at ${formatTime(lastRunAt)}` : ""} · {provider}
            </StatusPill>
          )}
          {generatedAt && (
            <StatusPill tone="neutral">
              Generated {formatDate(generatedAt)} at {formatTime(generatedAt)}
            </StatusPill>
          )}
          <StatusPill tone={DATA_QUALITY_TONES[portfolio.dataQuality] ?? "neutral"}>
            Data quality: {portfolio.dataQuality.toLowerCase()}
          </StatusPill>
          {portfolio.qualityFlags.map((flag) => (
            <StatusPill key={flag} tone="warn">
              {flag.replace(/_/g, " ").toLowerCase()}
            </StatusPill>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AiPage() {
  const [data, setData] = useState<LatestPortfolioAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.getLatestPortfolioAnalysis());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load the analysis.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleComplete = useCallback(() => {
    void load();
  }, [load]);

  return (
    <AppShell>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.overline}>
            <span className={styles.overlineDot} aria-hidden />
            Analysis
          </div>
          <h1 className={styles.pageTitle}>AI Advisor</h1>
          <p className={styles.pageSubtitle}>
            Portfolio health and per-stock recommendations from fundamentals, technicals and your
            investment profile
          </p>
        </div>
        <AnalyzeButton
          kind="portfolio"
          onComplete={handleComplete}
          onError={(message) => setError(message)}
        />
      </header>

      {error && (
        <div className={styles.error} role="alert">
          <span>{error}</span>
          <button type="button" className={styles.retry} onClick={() => { setError(null); void load(); }}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className={styles.skeletonBlock}>
          <Skeleton width="6rem" height="1.2rem" />
          <Skeleton height="10rem" radius="var(--radius-lg)" />
          <Skeleton height="14rem" radius="var(--radius-lg)" />
        </div>
      ) : !data ? (
        <div className={styles.empty}>
          <div className={styles.emptyMark} aria-hidden />
          <p className={styles.emptyTitle}>No AI analysis yet</p>
          <p className={styles.emptyBody}>
            Add holdings and fetch prices, then run a portfolio analysis to see your health score,
            concentration flags and per-stock actions.
          </p>
        </div>
      ) : (
        <PortfolioView data={data} />
      )}

      <p className={styles.disclaimer}>
        AI analysis is decision-support, based on data as of the timestamps shown; not investment
        advice or a guarantee of returns.
      </p>
    </AppShell>
  );
}