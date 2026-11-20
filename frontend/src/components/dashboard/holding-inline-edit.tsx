"use client";

import { useState, type FormEvent } from "react";
import type { Holding, HoldingsInput } from "@/lib/types";
import { Button } from "@/components/ui/button";
import styles from "./holding-inline-edit.module.css";

interface HoldingInlineEditProps {
  holding: Holding;
  onSave: (id: string, input: HoldingsInput) => Promise<void>;
  onCancel: () => void;
}

const BROKERS = ["Zerodha", "Groww", "Fyers"] as const;

function toInput(h: Holding): HoldingsInput {
  return {
    symbol: h.symbol,
    quantity: h.quantity,
    avgBuyPrice: h.avgBuyPrice,
    stopLoss: h.stopLoss,
    targetPrice: h.targetPrice,
    broker: h.broker,
    sector: h.sector,
  };
}

export function HoldingInlineEdit({ holding, onSave, onCancel }: HoldingInlineEditProps) {
  const [form, setForm] = useState<HoldingsInput>(() => toInput(holding));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setField = <K extends keyof HoldingsInput>(key: K, value: HoldingsInput[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!form.symbol.trim()) {
      setError("Symbol is required.");
      return;
    }
    if (form.quantity <= 0 || form.avgBuyPrice <= 0) {
      setError("Quantity and average buy price must be greater than zero.");
      return;
    }
    setSaving(true);
    try {
      await onSave(holding.id, form);
    } catch (err) {
      setError(
        err instanceof Error && err.message
          ? err.message
          : "Couldn't save the holding. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.header}>
        <span className={styles.title}>Edit {holding.symbol}</span>
        <span className={styles.hint}>
          Your records stay as entered — prices refresh on demand.
        </span>
      </div>

      <div className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.label}>Symbol</span>
          <input
            className={styles.input}
            type="text"
            autoCapitalize="characters"
            value={form.symbol}
            onChange={(e) => setField("symbol", e.target.value.toUpperCase())}
            autoFocus
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Quantity</span>
          <input
            className={styles.input}
            type="number"
            inputMode="decimal"
            min={0}
            step="any"
            value={form.quantity || ""}
            onChange={(e) => setField("quantity", Number(e.target.value))}
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Avg buy price (₹)</span>
          <input
            className={styles.input}
            type="number"
            inputMode="decimal"
            min={0}
            step="any"
            value={form.avgBuyPrice || ""}
            onChange={(e) => setField("avgBuyPrice", Number(e.target.value))}
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Stop-loss (₹)</span>
          <input
            className={styles.input}
            type="number"
            inputMode="decimal"
            min={0}
            step="any"
            placeholder="Optional"
            value={form.stopLoss ?? ""}
            onChange={(e) =>
              setField("stopLoss", e.target.value === "" ? null : Number(e.target.value))
            }
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Target (₹)</span>
          <input
            className={styles.input}
            type="number"
            inputMode="decimal"
            min={0}
            step="any"
            placeholder="Optional"
            value={form.targetPrice ?? ""}
            onChange={(e) =>
              setField("targetPrice", e.target.value === "" ? null : Number(e.target.value))
            }
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Broker</span>
          <select
            className={styles.input}
            value={form.broker ?? ""}
            onChange={(e) => setField("broker", e.target.value || null)}
          >
            <option value="">Select broker</option>
            {BROKERS.map((broker) => (
              <option key={broker} value={broker}>
                {broker}
              </option>
            ))}
            {form.broker && !BROKERS.includes(form.broker as (typeof BROKERS)[number]) && (
              <option value={form.broker}>{form.broker}</option>
            )}
          </select>
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Sector</span>
          <input
            className={styles.input}
            type="text"
            placeholder="IT, Banking, Pharma…"
            value={form.sector ?? ""}
            onChange={(e) => setField("sector", e.target.value || null)}
          />
        </label>
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <div className={styles.actions}>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" size="sm" loading={saving}>
          {saving ? "Saving" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
