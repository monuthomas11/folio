"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { formatPrice, formatQuantity, formatSignedINR } from "@/lib/format";
import type { Holding } from "@/lib/types";
import styles from "./exit-holding-dialog.module.css";

interface ExitHoldingDialogProps {
  holding: Holding;
  onClose: () => void;
  onSubmit: (input: { quantity: number; exitPrice: number }) => Promise<void>;
  error: string | null;
}

export function ExitHoldingDialog({
  holding,
  onClose,
  onSubmit,
  error,
}: ExitHoldingDialogProps) {
  const [quantity, setQuantity] = useState(String(holding.quantity));
  const [exitPrice, setExitPrice] = useState(
    holding.currentLtp != null ? String(holding.currentLtp) : "",
  );
  const [validationError, setValidationError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [onClose, saving]);

  const numericQuantity = Number(quantity);
  const numericExitPrice = Number(exitPrice);
  const estimatedPnl = useMemo(() => {
    if (!Number.isFinite(numericQuantity) || !Number.isFinite(numericExitPrice)) return null;
    return numericQuantity * (numericExitPrice - holding.avgBuyPrice);
  }, [holding.avgBuyPrice, numericExitPrice, numericQuantity]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!Number.isFinite(numericQuantity) || numericQuantity <= 0) {
      setValidationError("Enter a quantity greater than zero.");
      return;
    }
    if (numericQuantity > holding.quantity) {
      setValidationError(`Quantity cannot exceed ${formatQuantity(holding.quantity)}.`);
      return;
    }
    if (!Number.isFinite(numericExitPrice) || numericExitPrice <= 0) {
      setValidationError("Enter the price at which you exited this position.");
      return;
    }

    setValidationError(null);
    setSaving(true);
    try {
      await onSubmit({ quantity: numericQuantity, exitPrice: numericExitPrice });
    } catch {
      setSaving(false);
    }
  }

  const isFullExit = numericQuantity === holding.quantity;

  return (
    <div className={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && !saving && onClose()}>
      <section
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="exit-holding-title"
      >
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Record a sale</p>
            <h2 id="exit-holding-title">Exit {holding.symbol}</h2>
            <p className={styles.subtitle}>
              Capture the execution price to add this sale to realized P/L.
            </p>
          </div>
          <button type="button" className={styles.close} onClick={onClose} disabled={saving} aria-label="Close dialog">
            ×
          </button>
        </header>

        <div className={styles.positionNote}>
          <span>Open position</span>
          <strong>{formatQuantity(holding.quantity)} shares at {formatPrice(holding.avgBuyPrice)}</strong>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.fields}>
            <label>
              <span>Quantity sold</span>
              <input
                autoFocus
                type="number"
                min="0.001"
                max={holding.quantity}
                step="0.001"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
            </label>
            <label>
              <span>Exit price</span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                placeholder={holding.currentLtp != null ? undefined : "e.g. 2,450"}
                value={exitPrice}
                onChange={(event) => setExitPrice(event.target.value)}
              />
            </label>
          </div>

          {estimatedPnl != null && (
            <div className={`${styles.estimate} ${estimatedPnl >= 0 ? styles.estimateGain : styles.estimateLoss}`}>
              <span>Estimated realized P/L</span>
              <strong>{formatSignedINR(estimatedPnl)}</strong>
            </div>
          )}

          <p className={styles.helper}>
            {isFullExit
              ? "This will close the open position and keep the sale in your realized P/L history."
              : `After this sale, ${formatQuantity(Math.max(0, holding.quantity - (Number.isFinite(numericQuantity) ? numericQuantity : 0)))} shares will remain open.`}
          </p>

          {(validationError || error) && <p className={styles.error} role="alert">{validationError || error}</p>}

          <footer className={styles.actions}>
            <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
            <Button type="submit" loading={saving}>Record exit</Button>
          </footer>
        </form>
      </section>
    </div>
  );
}
