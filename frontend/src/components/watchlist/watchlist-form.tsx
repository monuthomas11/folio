"use client";

import { useEffect, useState, type FormEvent } from "react";
import type { WatchlistInput, WatchlistItem, WatchlistLevelKind } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { IconClose, IconPlus } from "@/components/icons";
import styles from "./watchlist-form.module.css";

interface WatchlistFormProps {
  editing: WatchlistItem | null;
  onAdded: (input: WatchlistInput) => Promise<void>;
  onUpdated: (id: string, input: WatchlistInput) => Promise<void>;
  onCancel: () => void;
}

type DraftLevel = {
  kind: WatchlistLevelKind;
  label: string;
  lowerPrice: string;
  upperPrice: string;
};

const EMPTY_LEVEL: DraftLevel = {
  kind: "entry",
  label: "",
  lowerPrice: "",
  upperPrice: "",
};

function levelToDraft(level: WatchlistItem["levels"][number]): DraftLevel {
  return {
    kind: level.kind,
    label: level.label ?? "",
    lowerPrice: String(level.lowerPrice),
    upperPrice: level.upperPrice == null ? "" : String(level.upperPrice),
  };
}

export function WatchlistForm({ editing, onAdded, onUpdated, onCancel }: WatchlistFormProps) {
  const [open, setOpen] = useState(Boolean(editing));
  const [symbol, setSymbol] = useState("");
  const [notes, setNotes] = useState("");
  const [levels, setLevels] = useState<DraftLevel[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editing) {
      setOpen(true);
      setSymbol(editing.symbol);
      setNotes(editing.notes ?? "");
      setLevels(editing.levels.map(levelToDraft));
      setError(null);
    }
  }, [editing]);

  const reset = () => {
    setOpen(false);
    setSymbol("");
    setNotes("");
    setLevels([]);
    setError(null);
    onCancel();
  };

  const updateLevel = (index: number, patch: Partial<DraftLevel>) => {
    setLevels((current) => current.map((level, i) => (i === index ? { ...level, ...patch } : level)));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!symbol.trim()) {
      setError("Symbol is required.");
      return;
    }
    const parsedLevels = [];
    for (const level of levels) {
      const lower = Number(level.lowerPrice);
      const upper = level.upperPrice.trim() === "" ? null : Number(level.upperPrice);
      if (!Number.isFinite(lower) || lower <= 0) {
        setError("Every level needs a positive lower price.");
        return;
      }
      if (upper !== null && (!Number.isFinite(upper) || upper <= 0 || upper < lower)) {
        setError("Upper prices must be positive and at least the lower price.");
        return;
      }
      parsedLevels.push({
        kind: level.kind,
        label: level.label.trim() || null,
        lowerPrice: lower,
        upperPrice: upper,
      });
    }
    const input: WatchlistInput = {
      symbol: symbol.trim().toUpperCase(),
      notes: notes.trim() || null,
      levels: parsedLevels,
    };
    setSubmitting(true);
    try {
      if (editing) await onUpdated(editing.id, input);
      else await onAdded(input);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t save the watchlist item.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <div className={styles.trigger}>
        <Button onClick={() => setOpen(true)}>
          <IconPlus width={15} height={15} /> Add a watchlist item
        </Button>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.formHeader}>
        <div>
          <h2 className={styles.formTitle}>{editing ? `Edit ${editing.symbol}` : "Add to watchlist"}</h2>
          <p className={styles.formHint}>Keep a thesis and flexible levels for the stocks you may buy.</p>
        </div>
        <button type="button" className={styles.close} onClick={reset} aria-label="Close form">
          <IconClose width={17} height={17} />
        </button>
      </div>

      <div className={styles.itemFields}>
        <label className={styles.field}>
          <span className={styles.label}>Symbol</span>
          <input className={styles.input} value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="RELIANCE" required />
        </label>
        <label className={`${styles.field} ${styles.notesField}`}>
          <span className={styles.label}>Thesis / notes</span>
          <textarea className={styles.textarea} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="What are you watching?" rows={2} />
        </label>
      </div>

      <div className={styles.levelHeader}>
        <div>
          <h3 className={styles.levelTitle}>Levels</h3>
          <p className={styles.levelHint}>A blank upper price makes a point level.</p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={() => setLevels((current) => [...current, { ...EMPTY_LEVEL }])}>
          <IconPlus width={14} height={14} /> Add level
        </Button>
      </div>

      {levels.length === 0 ? (
        <div className={styles.noLevels}>No levels yet. Add one to receive a manual alert when price reaches it.</div>
      ) : (
        <div className={styles.levelList}>
          {levels.map((level, index) => (
            <div className={styles.levelRow} key={index}>
              <label className={styles.field}>
                <span className={styles.label}>Type</span>
                <select className={styles.input} value={level.kind} onChange={(event) => updateLevel(index, { kind: event.target.value as WatchlistLevelKind })}>
                  <option value="entry">Entry</option>
                  <option value="target">Target</option>
                  <option value="stop-loss">Stop-loss</option>
                  <option value="invalidation">Invalidation</option>
                </select>
              </label>
              <label className={styles.field}>
                <span className={styles.label}>Label <span className={styles.optional}>Optional</span></span>
                <input className={styles.input} value={level.label} onChange={(event) => updateLevel(index, { label: event.target.value })} placeholder="Breakout" />
              </label>
              <label className={styles.field}>
                <span className={styles.label}>Lower (₹)</span>
                <input className={styles.input} type="number" min="0" step="any" inputMode="decimal" value={level.lowerPrice} onChange={(event) => updateLevel(index, { lowerPrice: event.target.value })} placeholder="100" required />
              </label>
              <label className={styles.field}>
                <span className={styles.label}>Upper (₹) <span className={styles.optional}>Optional</span></span>
                <input className={styles.input} type="number" min="0" step="any" inputMode="decimal" value={level.upperPrice} onChange={(event) => updateLevel(index, { upperPrice: event.target.value })} placeholder="105" />
              </label>
              <button type="button" className={styles.remove} onClick={() => setLevels((current) => current.filter((_, i) => i !== index))} aria-label={`Remove level ${index + 1}`}>
                <IconClose width={15} height={15} />
              </button>
            </div>
          ))}
        </div>
      )}

      {error && <p className={styles.error} role="alert">{error}</p>}
      <div className={styles.actions}>
        <Button type="button" variant="ghost" onClick={reset}>Cancel</Button>
        <Button type="submit" loading={submitting}>{submitting ? "Saving" : editing ? "Save changes" : "Add to watchlist"}</Button>
      </div>
    </form>
  );
}
