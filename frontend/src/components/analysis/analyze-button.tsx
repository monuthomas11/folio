"use client";

import { useEffect, useRef, useState } from "react";
import { api, pollRun, type RunStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { IconRefresh } from "@/components/icons";
import type { AnalysisRunDetail } from "@/lib/types";
import styles from "./analyze-button.module.css";

interface AnalyzeButtonProps {
  kind: "holding" | "portfolio";
  holdingId?: string;
  disabled?: boolean;
  onComplete: (run: AnalysisRunDetail) => void;
  onError?: (message: string) => void;
}

function stageLabel(stage: string | null): string {
  const labels: Record<string, string> = {
    FETCHING_MARKET_DATA: "Fetching market data…",
    FETCHING_FUNDAMENTALS: "Fetching fundamentals…",
    PROCESSING_TECHNICALS: "Computing technicals…",
    BUILDING_EVIDENCE: "Building evidence pack…",
    ANALYZING_STOCK: "Running stock analysis…",
    PORTFOLIO_CONTEXT: "Checking portfolio context…",
    FINAL_RECONCILIATION: "Final reconciliation…",
  };
  return labels[stage ?? ""] ?? "Analyzing…";
}

export function AnalyzeButton({
  kind,
  holdingId,
  disabled,
  onComplete,
  onError,
}: AnalyzeButtonProps) {
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<RunStatus | null>(null);
  const busy = useRef(false);

  useEffect(() => {
    return () => {
      busy.current = false;
    };
  }, []);

  const handleClick = async () => {
    if (busy.current) return;
    busy.current = true;
    setRunning(true);
    setStatus({ status: "CREATED", stage: null, errorMessage: null });
    try {
      const started =
        kind === "holding"
          ? await api.startHoldingAnalysis(holdingId!)
          : await api.startPortfolioAnalysis();
      const detail = await pollRun(started.runId, setStatus);
      onComplete(detail);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Analysis failed to start.");
    } finally {
      busy.current = false;
      setRunning(false);
      setStatus(null);
    }
  };

  return (
    <div className={styles.wrap}>
      <Button onClick={() => void handleClick()} disabled={disabled || running}>
        {running ? <IconRefresh width={15} height={15} /> : null}
        {running ? "Analyzing…" : "Analyze"}
      </Button>
      {running && status && (
        <span className={styles.progress} role="status">
          {stageLabel(status.stage)}
        </span>
      )}
    </div>
  );
}