"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { AnalyzeButton } from "@/components/analysis/analyze-button";
import { AskAi } from "@/components/analysis/ask-ai";
import { RatingBadge } from "@/components/analysis/rating-badge";
import { EvidencePanel } from "@/components/analysis/evidence-panel";
import { StatusPill } from "@/components/ui/status-pill";
import { Skeleton } from "@/components/ui/skeleton";
import {
  IconActivity,
  IconArrowUp,
  IconClose,
  IconShield,
  IconSparkles,
  IconTrendDown,
  IconTrendUp,
} from "@/components/icons";
import { api } from "@/lib/api";
import {
  formatDate,
  formatINRFractionless,
  formatPrice,
  formatQuantity,
  formatSigned,
  formatSignedINR,
  formatTime,
} from "@/lib/format";
import { holdingStats } from "@/lib/holdings";
import type { EvidenceItem, Holding, Recommendation } from "@/lib/types";
import styles from "./page.module.css";

const THESIS_TONES: Record<string, "healthy" | "warn" | "gain" | "danger" | "neutral"> = {
  VALID: "healthy",
  STRENGTHENING: "gain",
  WEAKENING: "warn",
  INVALIDATED: "danger",
  UNKNOWN: "neutral",
};

const DATA_QUALITY_TONES: Record<string, "healthy" | "warn" | "gain" | "danger" | "neutral"> = {
  EXCELLENT: "gain",
  GOOD: "healthy",
  MODERATE: "warn",
  POOR: "danger",
};

function ScoreBar({ label, value }: { label: string; value: number | null | undefined }) {
  if (value == null) return null;
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className={styles.scoreRow}>
      <span className={styles.scoreLabel}>{label}</span>
      <span className={styles.scoreTrack} aria-hidden>
        <span
          className={styles.scoreFill}
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className={`${styles.scoreValue} num`}>{value}/100</span>
    </div>
  );
}

type WatchTone = "pine" | "loss" | "gain" | "warn" | "danger";

const WATCH_SECTIONS: {
  title: string;
  items: (rec: Recommendation) => string[];
  tone: WatchTone;
  Icon: typeof IconSparkles;
}[] = [
  {
    title: "Key reasons",
    tone: "pine",
    Icon: IconSparkles,
    items: (rec) => rec.keyReasons,
  },
  {
    title: "Key risks",
    tone: "loss",
    Icon: IconShield,
    items: (rec) => rec.keyRisks,
  },
  {
    title: "Buy if",
    tone: "gain",
    Icon: IconArrowUp,
    items: (rec) => rec.buyConditions,
  },
  {
    title: "Reduce if",
    tone: "warn",
    Icon: IconTrendDown,
    items: (rec) => rec.reduceConditions,
  },
  {
    title: "Exit if",
    tone: "danger",
    Icon: IconClose,
    items: (rec) => rec.exitConditions,
  },
];

function WatchCard({
  title,
  items,
  tone,
  Icon,
}: {
  title: string;
  items: string[];
  tone: WatchTone;
  Icon: typeof IconSparkles;
}) {
  if (!items.length) return null;
  return (
    <div className={`${styles.watchCard} ${styles[`watch_${tone}`]}`}>
      <div className={styles.watchHead}>
        <span className={styles.watchIcon} aria-hidden>
          <Icon width={14} height={14} />
        </span>
        <h3 className={styles.watchTitle}>{title}</h3>
      </div>
      <ul className={styles.watchList}>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function ScenarioCard({
  title,
  text,
  Icon,
  tone,
}: {
  title: string;
  text: string | null;
  Icon: typeof IconActivity;
  tone: "gain" | "pine" | "loss";
}) {
  if (!text) return null;
  return (
    <div className={`${styles.scenario} ${styles[`scenario_${tone}`]}`}>
      <div className={styles.scenarioHead}>
        <span className={styles.scenarioIcon} aria-hidden>
          <Icon width={14} height={14} />
        </span>
        <h3 className={styles.scenarioTitle}>{title}</h3>
      </div>
      <p className={styles.scenarioText}>{text}</p>
    </div>
  );
}

function FairValueLegend({
  low,
  base,
  high,
  ltp,
}: {
  low: number | null | undefined;
  base: number | null | undefined;
  high: number | null | undefined;
  ltp: number | null | undefined;
}) {
  return (
    <dl className={styles.fairLegend}>
      <div className={styles.fairLegendItem}>
        <dt>
          <span className={`${styles.fairSwatch} ${styles.fairSwatch_low}`} />
          Low
        </dt>
        <dd className="num">{low != null ? formatPrice(low) : "—"}</dd>
      </div>
      <div className={styles.fairLegendItem}>
        <dt>
          <span className={`${styles.fairSwatch} ${styles.fairSwatch_base}`} />
          Base
        </dt>
        <dd className="num">{base != null ? formatPrice(base) : "—"}</dd>
      </div>
      <div className={styles.fairLegendItem}>
        <dt>
          <span className={`${styles.fairSwatch} ${styles.fairSwatch_high}`} />
          High
        </dt>
        <dd className="num">{high != null ? formatPrice(high) : "—"}</dd>
      </div>
      {ltp != null && (
        <div className={`${styles.fairLegendItem} ${styles.fairLegendItem_current}`}>
          <dt>
            <span className={`${styles.fairSwatch} ${styles.fairSwatch_ltp}`} />
            Current LTP
          </dt>
          <dd className="num">{formatPrice(ltp)}</dd>
        </div>
      )}
    </dl>
  );
}

function FairValueRange({
  range,
  ltp,
}: {
  range: { low: number | null; base: number | null; high: number | null };
  ltp: number | null | undefined;
}) {
  const { low, base, high } = range;
  const values = [low, high, base, ltp].filter(
    (v): v is number => typeof v === "number"
  );
  if (!values.length) return null;

  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const span = Math.max(maxVal - minVal, 1);
  const pct = (v: number | null | undefined) =>
    v == null ? null : Math.max(0, Math.min(100, ((v - minVal) / span) * 100));

  const lowPct = pct(low);
  const basePct = pct(base);
  const highPct = pct(high);
  const ltpPct = pct(ltp);

  const baseClamped = basePct == null ? null : Math.max(0, Math.min(100, basePct));
  const lowClamped = lowPct == null ? null : Math.max(0, Math.min(100, lowPct));
  const highClamped = highPct == null ? null : Math.max(0, Math.min(100, highPct));
  const rangeLeft = lowClamped ?? 0;
  const rangeRight = highClamped ?? 100;
  const rangeWidth = Math.max(0, rangeRight - rangeLeft);

  return (
    <div className={styles.fair}>
      <div className={styles.fairTrack}>
        <div
          className={styles.fairFill}
          style={{ left: `${rangeLeft}%`, width: `${rangeWidth}%` }}
          aria-hidden
        />
        {lowClamped != null && (
          <span
            className={`${styles.fairTick} ${styles.fairTick_low}`}
            style={{ left: `${lowClamped}%` }}
            aria-hidden
          />
        )}
        {highClamped != null && (
          <span
            className={`${styles.fairTick} ${styles.fairTick_high}`}
            style={{ left: `${highClamped}%` }}
            aria-hidden
          />
        )}
        {baseClamped != null && (
          <span
            className={`${styles.fairTick} ${styles.fairTick_base}`}
            style={{ left: `${baseClamped}%` }}
            aria-hidden
          />
        )}
        {ltpPct != null && (
          <span
            className={`${styles.fairPin} ${styles.fairPin_ltp}`}
            style={{ left: `${Math.max(0, Math.min(100, ltpPct))}%` }}
            aria-hidden
          />
        )}
      </div>
      <div className={styles.fairScale}>
        {minVal === maxVal ? (
          <span className="num">{formatPrice(minVal)}</span>
        ) : (
          <>
            <span className="num">{formatPrice(minVal)}</span>
            <span className="num">{formatPrice(maxVal)}</span>
          </>
        )}
      </div>
    </div>
  );
}

function RecommendationView({
  rec,
  currentLtp,
}: {
  rec: Recommendation;
  currentLtp: number | null;
}) {
  const thesisTone = THESIS_TONES[rec.thesisStatus ?? ""] ?? "neutral";
  const qualityTone = DATA_QUALITY_TONES[rec.dataQuality] ?? "neutral";
  const generatedAt = rec.analysisTimestamps?.generatedAt;

  return (
    <div className={styles.recWrap}>
      <section className={styles.card}>
        <header className={styles.recHeader}>
          <div className={styles.recHeaderLeft}>
            <RatingBadge rating={rec.rating} />
            <span className={styles.actionLabel}>{rec.action.replace(/_/g, " ")}</span>
          </div>
          <span className={styles.generated}>
            {generatedAt ? `Generated ${formatDate(generatedAt)} at ${formatTime(generatedAt)}` : ""}
            {rec.analysisTimestamps?.note ? ` · ${rec.analysisTimestamps.note}` : ""}
          </span>
        </header>

        {rec.confidence != null && (
          <div className={styles.confidence}>
            <div className={styles.confidenceHead}>
              <span className={styles.confidenceLabel}>Analysis confidence</span>
              <span className={`num ${styles.confidenceValue}`}>{rec.confidence}/100</span>
            </div>
            <div className={styles.confidenceTrack} aria-hidden>
              <span className={styles.confidenceFill} style={{ width: `${rec.confidence}%` }} />
            </div>
          </div>
        )}

        <div className={styles.pills}>
          {rec.thesisStatus && (
            <StatusPill tone={thesisTone}>Thesis: {rec.thesisStatus.toLowerCase()}</StatusPill>
          )}
          <StatusPill tone={qualityTone}>Data quality: {rec.dataQuality.toLowerCase()}</StatusPill>
          {rec.qualityFlags.map((flag) => (
            <StatusPill key={flag} tone="warn">
              {flag.replace(/_/g, " ").toLowerCase()}
            </StatusPill>
          ))}
        </div>

        <p className={styles.summary}>{rec.summary}</p>

        {rec.scores && (
          <div className={styles.scores}>
            <ScoreBar label="Business quality" value={rec.scores.businessQuality} />
            <ScoreBar label="Fundamental" value={rec.scores.fundamental} />
            <ScoreBar label="Valuation" value={rec.scores.valuation} />
            <ScoreBar label="Technical" value={rec.scores.technical} />
            <ScoreBar label="Portfolio fit" value={rec.scores.portfolioFit} />
          </div>
        )}
      </section>

      {rec.why && (
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Why this recommendation</h2>
          <p className={styles.bodyText}>{rec.why}</p>
        </section>
      )}

      {(rec.bullCase || rec.baseCase || rec.bearCase) && (
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Scenarios</h2>
          <div className={styles.scenarios}>
            <ScenarioCard title="Bull case" text={rec.bullCase} Icon={IconTrendUp} tone="gain" />
            <ScenarioCard title="Base case" text={rec.baseCase} Icon={IconActivity} tone="pine" />
            <ScenarioCard title="Bear case" text={rec.bearCase} Icon={IconTrendDown} tone="loss" />
          </div>
        </section>
      )}

      <section className={`${styles.card} ${styles.watchCardOuter}`}>
        <header className={styles.watchHeader}>
          <h2 className={styles.cardTitle}>What to watch</h2>
          <p className={styles.watchHint}>
            Five signals that move the thesis — color shows the action direction
          </p>
        </header>
        <div className={styles.watchGrid}>
          {WATCH_SECTIONS.map(({ title, items, tone, Icon }) => (
            <WatchCard
              key={title}
              title={title}
              items={items(rec)}
              tone={tone}
              Icon={Icon}
            />
          ))}
        </div>
      </section>

      {rec.fairValueRange && (rec.fairValueRange.low != null || rec.fairValueRange.base != null || rec.fairValueRange.high != null) && (
        <section className={styles.card}>
          <header className={styles.fairHeader}>
            <div>
              <h2 className={styles.cardTitle}>Fair-value range</h2>
              <p className={styles.fairHint}>
                Where the model thinks the stock should trade
              </p>
            </div>
            <FairValueLegend low={rec.fairValueRange.low} base={rec.fairValueRange.base} high={rec.fairValueRange.high} ltp={currentLtp} />
          </header>
          <FairValueRange range={rec.fairValueRange} ltp={currentLtp} />
        </section>
      )}

      <EvidencePanel items={rec.evidence as EvidenceItem[] | null} />
    </div>
  );
}

export default function HoldingDetailPage() {
  const params = useParams<{ id: string }>();
  const holdingId = params.id;

  const [holding, setHolding] = useState<Holding | null>(null);
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!holdingId) return;
    setLoading(true);
    setError(null);
    try {
      const snapshot = await api.getSnapshot();
      const found = snapshot.holdings.find((h) => h.id === holdingId);
      if (!found) {
        setError("Holding not found.");
        return;
      }
      setHolding(found);
      setRec(await api.getLatestHoldingAnalysis(holdingId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load the holding.");
    } finally {
      setLoading(false);
    }
  }, [holdingId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleComplete = useCallback(() => {
    void load();
  }, [load]);

  if (loading && !holding) {
    return (
      <AppShell>
        <div className={styles.skeletonBlock}>
          <Skeleton width="8rem" height="1.5rem" />
          <Skeleton height="6rem" radius="var(--radius-lg)" />
          <Skeleton height="16rem" radius="var(--radius-lg)" />
        </div>
      </AppShell>
    );
  }

  if (!holding) {
    return (
      <AppShell>
        <div className={styles.errorCard}>
          <p>{error ?? "Holding not found."}</p>
          <Link href="/portfolio" className={styles.backLink}>
            Back to portfolio
          </Link>
        </div>
      </AppShell>
    );
  }

  const s = holdingStats(holding);
  const pnlGain = s.pnl >= 0;

  return (
    <AppShell>
      <header className={styles.pageHeader}>
        <div>
          <Link href="/portfolio" className={styles.crumb}>
            Portfolio /{" "}
          </Link>
          <h1 className={styles.pageTitle}>{holding.symbol}</h1>
          <p className={styles.pageSubtitle}>
            {[holding.sector, holding.broker].filter(Boolean).join(" · ") || "NSE listed"}
          </p>
        </div>
        <div className={styles.headerActions}>
          <AskAi
            context="holding"
            holdingId={holding.id}
            enabled={!!rec}
            label={`Ask about ${holding.symbol}`}
          />
          <AnalyzeButton
            kind="holding"
            holdingId={holding.id}
            disabled={!holding.currentLtp}
            onComplete={handleComplete}
            onError={(message) => setError(message)}
          />
        </div>
      </header>

      {error && (
        <div className={styles.error} role="alert">
          <span>{error}</span>
          <button type="button" className={styles.retry} onClick={() => { setError(null); void load(); }}>
            Retry
          </button>
        </div>
      )}

      <section className={styles.positionCard}>
        <div className={styles.positionGrid}>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>Quantity</span>
            <span className={`num ${styles.posValue}`}>{formatQuantity(holding.quantity)}</span>
          </div>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>Avg buy price</span>
            <span className={`num ${styles.posValue}`}>{formatPrice(holding.avgBuyPrice)}</span>
          </div>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>LTP</span>
            <span className={`num ${styles.posValue}`}>
              {holding.currentLtp != null ? formatPrice(holding.currentLtp) : "—"}
            </span>
          </div>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>Invested</span>
            <span className={`num ${styles.posValue}`}>{formatINRFractionless(s.invested)}</span>
          </div>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>Current value</span>
            <span className={`num ${styles.posValue}`}>{formatINRFractionless(s.currentValue)}</span>
          </div>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>P/L</span>
            <span className={`num ${styles.posValue} ${pnlGain ? styles.gainText : styles.lossText}`}>
              {formatSignedINR(s.pnl)} <span className={styles.posPct}>({formatSigned(s.pnlPct)})</span>
            </span>
          </div>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>Stop loss</span>
            <span className={`num ${styles.posValue}`}>
              {holding.stopLoss != null ? formatPrice(holding.stopLoss) : "—"}
            </span>
          </div>
          <div className={styles.posItem}>
            <span className={styles.posLabel}>Target</span>
            <span className={`num ${styles.posValue}`}>
              {holding.targetPrice != null ? formatPrice(holding.targetPrice) : "—"}
            </span>
          </div>
        </div>
      </section>

      {!rec && !loading && (
        <div className={styles.emptyRec}>
          <p className={styles.emptyRecTitle}>No AI analysis yet</p>
          <p className={styles.emptyRecBody}>
            Fetch a price, then hit <strong>Analyze</strong> to get a recommendation based on
            fundamentals, technicals and your portfolio context.
          </p>
        </div>
      )}

      {rec && <RecommendationView rec={rec} currentLtp={holding.currentLtp ?? null} />}

      <p className={styles.disclaimer}>
        AI analysis is decision-support, based on data as of the timestamps shown; not investment
        advice or a guarantee of returns.
      </p>
    </AppShell>
  );
}