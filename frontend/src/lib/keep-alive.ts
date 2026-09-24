"use client";

import { useEffect } from "react";
import { api } from "./api";

const DEFAULT_TIMEOUT_MINUTES = 60;
const HEARTBEAT_INTERVAL_MS = 10 * 60 * 1000;

function parseTimeoutMinutes(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : DEFAULT_TIMEOUT_MINUTES;
}

const HEARTBEAT_TIMEOUT_MS =
  parseTimeoutMinutes(process.env.NEXT_PUBLIC_HEARTBEAT_TIMEOUT_MINUTES) * 60 * 1000;

export function useKeepAlive(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;

    let lastActivityAt = Date.now();
    let heartbeatActive = true;
    let requestInFlight = false;

    const sendHeartbeat = async () => {
      if (
        !heartbeatActive ||
        requestInFlight ||
        document.visibilityState !== "visible"
      ) {
        return;
      }

      if (Date.now() - lastActivityAt >= HEARTBEAT_TIMEOUT_MS) {
        heartbeatActive = false;
        return;
      }

      requestInFlight = true;
      try {
        await api.health();
      } catch {
        return;
      } finally {
        requestInFlight = false;
      }
    };

    const markActivity = () => {
      const now = Date.now();
      const timedOut = now - lastActivityAt >= HEARTBEAT_TIMEOUT_MS;
      lastActivityAt = now;
      heartbeatActive = true;
      if (timedOut) void sendHeartbeat();
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") markActivity();
    };

    window.addEventListener("pointerdown", markActivity, { passive: true });
    window.addEventListener("keydown", markActivity);
    window.addEventListener("scroll", markActivity, { passive: true });
    window.addEventListener("touchstart", markActivity, { passive: true });
    document.addEventListener("visibilitychange", handleVisibilityChange);

    const intervalId = window.setInterval(() => {
      void sendHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("pointerdown", markActivity);
      window.removeEventListener("keydown", markActivity);
      window.removeEventListener("scroll", markActivity);
      window.removeEventListener("touchstart", markActivity);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enabled]);
}
