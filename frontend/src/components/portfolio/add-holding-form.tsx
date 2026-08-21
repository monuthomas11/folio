"use client";

import { useEffect, useState, type FormEvent } from "react";
import type { Holding, HoldingsInput } from "@/lib/types";
import { Button } from "@/components/ui/button";
import styles from "./add-holding-form.module.css";

interface AddHoldingFormProps {
  onAdded: (input: HoldingsInput) => Promise<void>;
  onUpdated?: (id: string, input: HoldingsInput) => Promise<void>;
  editing?: Holding | null;
  onCancelEdit?: () => void;
}

const EMPTY: HoldingsInput = {
  symbol: "",
  quantity: 0,
  avgBuyPrice: 0,
  stopLoss: null,
  targetPrice: null,
  broker: null,
  sector: null,
};

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

export function AddHoldingForm({
  onAdded,
  onUpdated,
  editing,
  onCancelEdit,
}: AddHoldingFormProps) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<HoldingsInput>(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editing) {
      setForm(toInput(editing));
      setOpen(true);
      setError(null);
    }
  }, [editing]);

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
    setSubmitting(true);
    try {
      if (editing && onUpdated) {
        await onUpdated(editing.id, form);
        onCancelEdit?.();
      } else {
        await onAdded(form);
      }
      setForm(EMPTY);
      setOpen(false);
    } catch (err) {
      setError(
        err instanceof Error && err.message
          ? err.message
          : "Couldn't save the holding. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const close = () => {
    setOpen(false);
    setForm(EMPTY);
    setError(null);
    onCancelEdit?.();
  };

  if (!open) {
    return (
      <div className={styles.trigger}>
        <Button onClick={() => setOpen(true)}>
          <span aria-hidden>+</span> Add a holding
        </Button>
      </div>
    );
  }

  const isEditing = Boolean(editing);

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.formHeader}>
        <h2 className={styles.formTitle}>
          {isEditing ? `Edit ${form.symbol}` : "Add a holding"}
        </h2>
        <p className={styles.formHint}>
          These are your records — we never overwrite them. Prices refresh on demand.
        </p>
      </div>

      <div className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.label}>Symbol</span>
          <input
            className={styles.input}
            type="text"
            autoCapitalize="characters"
            placeholder="RELIANCE"
            value={form.symbol}
            onChange={(e) => setField("symbol", e.target.value.toUpperCase())}
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
            placeholder="12"
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
            placeholder="2480.50"
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
          <input
            className={styles.input}
            type="text"
            placeholder="Zerodha, Groww…"
            value={form.broker ?? ""}
            onChange={(e) => setField("broker", e.target.value || null)}
          />
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
        <Button type="button" variant="ghost" onClick={close}>
          Cancel
        </Button>
        <Button type="submit" loading={submitting}>
          {submitting ? (isEditing ? "Saving" : "Adding") : isEditing ? "Save changes" : "Add holding"}
        </Button>
      </div>
    </form>
  );
}