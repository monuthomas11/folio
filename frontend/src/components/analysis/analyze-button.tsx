"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, api, pollRun, type RunStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { IconRefresh } from "@/components/icons";
import type { AnalysisRun, AnalysisRunDetail } from "@/lib/types";
import styles from "./analyze-button.module.css";

interface AnalyzeButtonProps {
  kind: "holding" | "portfolio";
  holdingId?: string;
  disabled?: boolean;
  onComplete: (run: AnalysisRunDetail) => void;
  onError?: (message: string) => void;
  onCancelled?: () => void;
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

function stuckAge(createdAt: string): string {
  const diffMs = Date.now() - new Date(createdAt).getTime();
  if (!Number.isFinite(diffMs) || diffMs < 0) return "";
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function isAlreadyInProgress(err: unknown): boolean {
  return (
    err instanceof ApiError &&
    err.status === 409 &&
    err.message.toLowerCase().includes("already in progress")
  );
}

export function AnalyzeButton({
  kind,
  holdingId,
  disabled,
  onComplete,
  onError,
  onCancelled,
}: AnalyzeButtonProps) {
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [stuck, setStuck] = useState<AnalysisRun | null>(null);
  const [checkingStuck, setCheckingStuck] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const busy = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      setCheckingStuck(true);
      try {
        const active = await api.getActiveRun();
        if (mounted && active && (active.status === "CREATED" || active.status === "RUNNING")) {
          setStuck(active);
        }
      } catch {
        /* ignore: 401 redirects globally, offline shows on next action */
      } finally {
        if (mounted) setCheckingStuck(false);
      }
    };
    void check();
    return () => {
      mounted = false;
      busy.current = false;
      abortRef.current?.abort();
    };
  }, []);

  const refreshStuck = async () => {
    setCheckingStuck(true);
    try {
      const active = await api.getActiveRun();
      setStuck(
        active && (active.status === "CREATED" || active.status === "RUNNING") ? active : null,
      );
      return active;
    } catch {
      return null;
    } finally {
      setCheckingStuck(false);
    }
  };

  const handleClick = async () => {
    if (busy.current) return;
    busy.current = true;
    setRunning(true);
    setStuck(null);
    setStatus({ status: "CREATED", stage: null, errorMessage: null });
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const started =
        kind === "holding"
          ? await api.startHoldingAnalysis(holdingId!)
          : await api.startPortfolioAnalysis();
      const detail = await pollRun(started.runId, setStatus, 1800000, 2000, controller.signal);
      onComplete(detail);
    } catch (err) {
      if (controller.signal.aborted) {
        onCancelled?.();
        return;
      }
      if (isAlreadyInProgress(err)) {
        const active = await refreshStuck();
        onError?.(
          active
            ? "An analysis is already in progress for this account. Cancel the stuck run to retry."
            : err instanceof Error
              ? err.message
              : "Analysis failed to start.",
        );
        return;
      }
      onError?.(err instanceof Error ? err.message : "Analysis failed to start.");
    } finally {
      busy.current = false;
      abortRef.current = null;
      setRunning(false);
      setStatus(null);
    }
  };

  const handleCancelRunning = async () => {
    abortRef.current?.abort();
    setCancelling(true);
    try {
      await api.cancelActiveRun();
    } catch {
      /* abort already stops polling; server cleanup is best-effort here */
    } finally {
      setCancelling(false);
    }
  };

  const handleCancelStuck = async () => {
    setCancelling(true);
    try {
      await api.cancelActiveRun();
      const active = await api.getActiveRun().catch(() => null);
      if (!active) {
        setStuck(null);
        onCancelled?.();
      } else {
        setStuck(active);
        onError?.("The previous run is still active. Try cancelling again.");
      }
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Could not cancel the stuck analysis.");
    } finally {
      setCancelling(false);
    }
  };

  if (stuck && !running) {
    return (
      <div className={styles.wrap}>
        <div className={styles.stuck} role="alert">
          <span className={styles.stuckText}>
            Analysis stuck ({stageLabel(stuck.stage)} · started {stuckAge(stuck.createdAt)}). Cancel
            it to run a new analysis.
          </span>
          <span className={styles.stuckActions}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void handleCancelStuck()}
              loading={cancelling}
              disabled={checkingStuck}
            >
              Cancel stuck run
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void refreshStuck()}
              disabled={cancelling || checkingStuck}
            >
              {checkingStuck ? "Checking…" : "Check again"}
            </Button>
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <Button onClick={() => void handleClick()} disabled={disabled || running || checkingStuck}>
        {running ? <IconRefresh width={15} height={15} /> : null}
        {running ? "Analyzing…" : "Analyze"}
      </Button>
      {running && (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void handleCancelRunning()}
          loading={cancelling}
        >
          Cancel
        </Button>
      )}
      {running && status && (
        <span className={styles.progress} role="status">
          {stageLabel(status.stage)}
        </span>
      )}
    </div>
  );
}
