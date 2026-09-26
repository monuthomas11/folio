"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { IconArrowDown, IconArrowUp, IconClose, IconPencil, IconPlus, IconRefresh, IconTrash } from "@/components/icons";
import { api } from "@/lib/api";
import { formatDate, formatINR, formatPrice, formatQuantity, formatSignedINR, formatTime } from "@/lib/format";
import type {
  Trade,
  TradeAssetClass,
  TradeChargesInput,
  TradeExit,
  TradeExitInput,
  TradeInput,
  TradeInstrumentType,
  TradeOptionType,
  TradebookSummary,
} from "@/lib/types";
import styles from "./page.module.css";

const today = () => new Date().toISOString().slice(0, 10);

function blankCharges(): TradeChargesInput {
  return {
    brokerage: null,
    sttCtt: null,
    exchangeTransaction: null,
    sebi: null,
    gst: null,
    stampDuty: null,
    ipft: null,
    other: null,
    contractNoteRef: null,
  };
}

function blankTrade(assetClass: TradeAssetClass): TradeInput {
  return {
    symbol: "",
    side: "long",
    assetClass,
    instrumentType: assetClass === "fno" ? "option" : "equity",
    exchange: assetClass === "fno" ? "NSE" : null,
    underlyingType: assetClass === "fno" ? "index" : null,
    underlyingSymbol: null,
    contractSymbol: null,
    expiryDate: null,
    strikePrice: null,
    tickSize: null,
    optionType: assetClass === "fno" ? "CE" : null,
    lotSize: null,
    entryLots: null,
    productType: assetClass === "fno" ? "NRML" : null,
    entryAt: null,
    entryOrderId: null,
    entryContractNoteRef: null,
    strategy: null,
    thesis: null,
    settlementType: assetClass === "fno" ? "cash" : null,
    marginUsed: null,
    entryDate: today(),
    entryQuantity: assetClass === "fno" ? null : 0,
    entryPrice: 0,
    broker: null,
    notes: null,
    entryCharges: assetClass === "fno" ? blankCharges() : null,
  };
}

function pnlClass(value: number | null) {
  if (value == null) return styles.pending;
  return value >= 0 ? styles.gain : styles.loss;
}

function PnlValue({ value }: { value: number | null }) {
  return <span className={`num ${pnlClass(value)}`}>{value == null ? "—" : formatSignedINR(value)}</span>;
}

function useDialogAccessibility(onClose: () => void) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    const focusable = () => Array.from(dialog.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ));
    const initialFocus = dialog.querySelector<HTMLElement>("[autofocus]") ?? focusable()[0];
    document.body.style.overflow = "hidden";
    initialFocus?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (items.length === 0) {
        event.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    dialog.addEventListener("keydown", onKeyDown);
    return () => {
      dialog.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, []);

  return dialogRef;
}

function expiryWarning(expiryDate: string | null) {
  if (!expiryDate) return null;
  const day = 24 * 60 * 60 * 1000;
  const daysRemaining = Math.ceil((Date.parse(`${expiryDate}T00:00:00Z`) - Date.parse(`${today()}T00:00:00Z`)) / day);
  if (daysRemaining < 0) return "Expired; record an explicit settlement or exit when confirmed.";
  if (daysRemaining === 0) return "Expires today; record an explicit settlement or exit when confirmed.";
  if (daysRemaining <= 7) return `Expires in ${daysRemaining} ${daysRemaining === 1 ? "day" : "days"}.`;
  return null;
}

function NumericField({
  value,
  onChange,
  min = 0,
  step = "0.01",
}: {
  value: number | null;
  onChange: (value: number | null) => void;
  min?: number;
  step?: string;
}) {
  return (
    <input
      type="number"
      min={min}
      step={step}
      value={value == null || value === 0 ? "" : value}
      onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
    />
  );
}

function ChargeFields({
  value,
  onChange,
}: {
  value: TradeChargesInput;
  onChange: (value: TradeChargesInput) => void;
}) {
  const setField = <K extends keyof TradeChargesInput>(key: K, next: TradeChargesInput[K]) => {
    onChange({ ...value, [key]: next });
  };
  return (
    <div className={styles.chargeBlock}>
      <div className={styles.chargeHeader}>
        <div>
          <span className={styles.sectionLabel}>Actual contract-note charges</span>
          <p>Use zero where a component is genuinely not charged. Blank values keep net P/L provisional.</p>
        </div>
      </div>
      <div className={styles.chargeGrid}>
        <label><span>Brokerage</span><NumericField value={value.brokerage} onChange={(next) => setField("brokerage", next)} /></label>
        <label><span>STT / CTT</span><NumericField value={value.sttCtt} onChange={(next) => setField("sttCtt", next)} /></label>
        <label><span>Exchange</span><NumericField value={value.exchangeTransaction} onChange={(next) => setField("exchangeTransaction", next)} /></label>
        <label><span>SEBI</span><NumericField value={value.sebi} onChange={(next) => setField("sebi", next)} /></label>
        <label><span>GST</span><NumericField value={value.gst} onChange={(next) => setField("gst", next)} /></label>
        <label><span>Stamp duty</span><NumericField value={value.stampDuty} onChange={(next) => setField("stampDuty", next)} /></label>
        <label><span>IPFT</span><NumericField value={value.ipft} onChange={(next) => setField("ipft", next)} /></label>
        <label><span>Other</span><NumericField value={value.other} onChange={(next) => setField("other", next)} /></label>
        <label className={styles.wideField}><span>Contract-note reference</span><input value={value.contractNoteRef ?? ""} onChange={(event) => setField("contractNoteRef", event.target.value || null)} placeholder="Optional reference" /></label>
      </div>
    </div>
  );
}

function tradeInputFromTrade(trade: Trade): TradeInput {
  const entryCharge = trade.entryCharge;
  return {
    symbol: trade.assetClass === "fno" ? trade.underlyingSymbol ?? trade.symbol : trade.symbol,
    side: trade.side,
    assetClass: trade.assetClass,
    instrumentType: trade.instrumentType,
    exchange: trade.exchange,
    underlyingType: trade.underlyingType,
    underlyingSymbol: trade.underlyingSymbol,
    contractSymbol: trade.contractSymbol,
    expiryDate: trade.expiryDate,
    strikePrice: trade.strikePrice,
    tickSize: trade.tickSize,
    optionType: trade.optionType,
    lotSize: trade.lotSize,
    entryLots: trade.entryLots,
    productType: trade.productType,
    entryAt: trade.entryAt,
    entryOrderId: trade.entryOrderId,
    entryContractNoteRef: trade.entryContractNoteRef,
    strategy: trade.strategy,
    thesis: trade.thesis,
    settlementType: trade.settlementType,
    marginUsed: trade.marginUsed,
    entryDate: trade.entryDate,
    entryQuantity: trade.assetClass === "fno" ? null : trade.entryQuantity,
    entryPrice: trade.entryPrice,
    broker: trade.broker,
    notes: trade.notes,
    entryCharges: trade.assetClass === "fno"
      ? {
          brokerage: entryCharge?.brokerage ?? null,
          sttCtt: entryCharge?.sttCtt ?? null,
          exchangeTransaction: entryCharge?.exchangeTransaction ?? null,
          sebi: entryCharge?.sebi ?? null,
          gst: entryCharge?.gst ?? null,
          stampDuty: entryCharge?.stampDuty ?? null,
          ipft: entryCharge?.ipft ?? null,
          other: entryCharge?.other ?? null,
          contractNoteRef: entryCharge?.contractNoteRef ?? null,
        }
      : null,
  };
}

function TradeForm({
  assetClass,
  open,
  editing,
  onSaved,
  onCancel,
}: {
  assetClass: TradeAssetClass;
  open: boolean;
  editing: Trade | null;
  onSaved: (input: TradeInput, id?: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<TradeInput>(() => blankTrade(assetClass));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(editing ? tradeInputFromTrade(editing) : blankTrade(assetClass));
    setError(null);
  }, [editing, assetClass, open]);

  const setField = <K extends keyof TradeInput>(key: K, value: TradeInput[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const close = () => {
    setError(null);
    onCancel();
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.symbol.trim()) return setError(assetClass === "fno" ? "Underlying symbol is required." : "Symbol is required.");
    if (!form.entryDate) return setError("Entry date is required.");
    if (assetClass === "equity" && (form.entryQuantity == null || form.entryQuantity <= 0)) return setError("Quantity must be greater than zero.");
    if (assetClass === "fno") {
      if (!form.entryLots || !form.lotSize || form.entryLots <= 0 || form.lotSize <= 0) return setError("Enter a positive lot count and lot size.");
      if (!form.expiryDate || !form.contractSymbol || !form.underlyingSymbol || !form.tickSize || form.tickSize <= 0) return setError("Contract, underlying, expiry, and tick size are required.");
      if (form.expiryDate < form.entryDate) return setError("Expiry date cannot be before entry date.");
      if (form.instrumentType === "option" && (!form.strikePrice || !form.optionType)) return setError("Options require strike price and CE/PE type.");
    }
    if (form.entryPrice <= 0) return setError("Entry price or premium must be greater than zero.");
    setSaving(true);
    setError(null);
    try {
      await onSaved({ ...form, assetClass }, editing?.id);
      close();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t save the trade.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;
  const isFno = assetClass === "fno";
  const setNumber = (key: keyof TradeInput, value: number | null) => setField(key, value as never);

  return (
    <form className={styles.form} onSubmit={submit}>
      <div className={styles.formHeader}>
        <div>
          <h2>{editing ? `Edit ${form.symbol}` : isFno ? "Record an F&O trade" : "Record an equity trade"}</h2>
          <p>{isFno ? "Capture the exact contract and contract-note costs. Long trades only in this release." : "Entry details stay fixed once an exit is recorded."}</p>
        </div>
        <button type="button" className={styles.closeButton} onClick={close} aria-label="Close trade form"><IconClose width={17} height={17} /></button>
      </div>
      <div className={styles.formGrid}>
        {isFno ? (
          <>
            <label><span>Instrument</span><select value={form.instrumentType} onChange={(event) => { const next = event.target.value as TradeInstrumentType; setField("instrumentType", next); if (next === "future") { setField("strikePrice", null); setField("optionType", null); } else if (!form.optionType) { setField("optionType", "CE"); } }}><option value="option">Option</option><option value="future">Future</option></select></label>
            <label><span>Direction</span><select value="long" disabled><option value="long">Long · buy then sell</option></select></label>
            <label><span>Exchange</span><select value={form.exchange ?? "NSE"} onChange={(event) => setField("exchange", event.target.value as "NSE" | "BSE")}><option value="NSE">NSE</option><option value="BSE">BSE</option></select></label>
            <label><span>Underlying type</span><select value={form.underlyingType ?? "index"} onChange={(event) => setField("underlyingType", event.target.value as "index" | "stock")}><option value="index">Index</option><option value="stock">Stock</option></select></label>
            <label><span>Underlying symbol</span><input value={form.underlyingSymbol ?? ""} onChange={(event) => { const value = event.target.value.toUpperCase(); setField("underlyingSymbol", value); setField("symbol", value); }} placeholder="NIFTY" required /></label>
            <label><span>Contract symbol</span><input value={form.contractSymbol ?? ""} onChange={(event) => setField("contractSymbol", event.target.value.toUpperCase() || null)} placeholder="Exchange contract identifier" required /></label>
            <label><span>Expiry date</span><input type="date" value={form.expiryDate ?? ""} onChange={(event) => setField("expiryDate", event.target.value || null)} required /></label>
            <label><span>Tick size</span><NumericField value={form.tickSize} onChange={(next) => setNumber("tickSize", next)} min={0.000001} step="0.01" /></label>
            {form.instrumentType === "option" && <label><span>Option type</span><select value={form.optionType ?? "CE"} onChange={(event) => setField("optionType", event.target.value as TradeOptionType)}><option value="CE">Call (CE)</option><option value="PE">Put (PE)</option></select></label>}
            {form.instrumentType === "option" && <label><span>Strike price (₹)</span><NumericField value={form.strikePrice} onChange={(next) => setNumber("strikePrice", next)} min={0.01} /></label>}
            <label><span>Lot size</span><NumericField value={form.lotSize} onChange={(next) => setNumber("lotSize", next)} min={1} step="1" /></label>
            <label><span>Lots</span><NumericField value={form.entryLots} onChange={(next) => setNumber("entryLots", next)} min={1} step="1" /></label>
            <label><span>Entry price / premium (₹)</span><NumericField value={form.entryPrice} onChange={(next) => setNumber("entryPrice", next)} min={0.01} /></label>
            <label><span>Product</span><select value={form.productType ?? "NRML"} onChange={(event) => setField("productType", event.target.value)}><option value="NRML">NRML</option><option value="MIS">MIS</option></select></label>
            {form.instrumentType === "future" && <label><span>Margin used (₹)</span><NumericField value={form.marginUsed} onChange={(next) => setNumber("marginUsed", next)} min={0} /></label>}
            <label><span>Entry date</span><input type="date" value={form.entryDate} onChange={(event) => setField("entryDate", event.target.value)} required /></label>
            <label><span>Entry time</span><input type="datetime-local" value={form.entryAt?.slice(0, 16) ?? ""} onChange={(event) => setField("entryAt", event.target.value || null)} /></label>
            <label><span>Broker</span><input value={form.broker ?? ""} onChange={(event) => setField("broker", event.target.value || null)} placeholder="Zerodha, Groww…" /></label>
            <label><span>Entry order ID</span><input value={form.entryOrderId ?? ""} onChange={(event) => setField("entryOrderId", event.target.value || null)} /></label>
            <label><span>Entry contract note</span><input value={form.entryContractNoteRef ?? ""} onChange={(event) => setField("entryContractNoteRef", event.target.value || null)} /></label>
            <label><span>Strategy / setup</span><input value={form.strategy ?? ""} onChange={(event) => setField("strategy", event.target.value || null)} placeholder="Breakout, reversal…" /></label>
            <label><span>Settlement</span><select value={form.settlementType ?? "cash"} onChange={(event) => setField("settlementType", event.target.value)}><option value="cash">Cash</option><option value="physical">Physical</option><option value="manual">Manual</option></select></label>
            <label className={styles.wideField}><span>Thesis</span><textarea value={form.thesis ?? ""} onChange={(event) => setField("thesis", event.target.value || null)} placeholder="Why this contract and setup?" rows={2} /></label>
            <label className={styles.wideField}><span>Notes</span><textarea value={form.notes ?? ""} onChange={(event) => setField("notes", event.target.value || null)} placeholder="Optional context" rows={2} /></label>
          </>
        ) : (
          <>
            <label><span>Side</span><select value={form.side} onChange={(event) => setField("side", event.target.value as "long" | "short")}><option value="long">Long · buy then sell</option><option value="short">Short · sell then cover</option></select></label>
            <label><span>Symbol</span><input value={form.symbol} onChange={(event) => setField("symbol", event.target.value.toUpperCase())} placeholder="RELIANCE" required /></label>
            <label><span>Entry date</span><input type="date" value={form.entryDate} onChange={(event) => setField("entryDate", event.target.value)} required /></label>
            <label><span>Quantity</span><NumericField value={form.entryQuantity} onChange={(next) => setNumber("entryQuantity", next)} min={0.001} step="0.001" /></label>
            <label><span>Entry price (₹)</span><NumericField value={form.entryPrice} onChange={(next) => setNumber("entryPrice", next)} min={0.01} /></label>
            <label><span>Broker</span><input value={form.broker ?? ""} onChange={(event) => setField("broker", event.target.value || null)} placeholder="Zerodha, Groww…" /></label>
            <label className={styles.wideField}><span>Notes</span><textarea value={form.notes ?? ""} onChange={(event) => setField("notes", event.target.value || null)} placeholder="Optional setup or context" rows={2} /></label>
          </>
        )}
      </div>
      {isFno && form.entryCharges && <ChargeFields value={form.entryCharges} onChange={(next) => setField("entryCharges", next)} />}
      {error && <p className={styles.formError} role="alert">{error}</p>}
      <div className={styles.formActions}><Button type="button" variant="ghost" onClick={close}>Cancel</Button><Button type="submit" loading={saving}>{editing ? "Save changes" : "Add trade"}</Button></div>
    </form>
  );
}

function ExitDialog({ trade, onClose, onSubmit }: { trade: Trade; onClose: () => void; onSubmit: (input: TradeExitInput) => Promise<void> }) {
  const isFno = trade.assetClass === "fno";
  const [lots, setLots] = useState(String(trade.remainingLots ?? 1));
  const [quantity, setQuantity] = useState(String(trade.remainingQuantity));
  const [price, setPrice] = useState(trade.currentLtp == null ? "" : String(trade.currentLtp));
  const [exitDate, setExitDate] = useState(today());
  const [reason, setReason] = useState("manual");
  const [exitOrderId, setExitOrderId] = useState("");
  const [exitContractNoteRef, setExitContractNoteRef] = useState("");
  const [notes, setNotes] = useState("");
  const [charges, setCharges] = useState<TradeChargesInput>(blankCharges());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const numericPrice = Number(price);
  const numericUnits = isFno ? Number(lots) * (trade.lotSize ?? 0) : Number(quantity);
  const estimated = numericUnits > 0 && numericPrice > 0 ? (numericPrice - trade.entryPrice) * numericUnits : null;
  const chargesComplete = Object.entries(charges).filter(([key]) => key !== "contractNoteRef").every(([, value]) => value != null);
  const entryAllocation = trade.entryCharge?.complete && trade.entryQuantity > 0 && estimated != null
    ? (trade.entryCharge.total ?? 0) * numericUnits / trade.entryQuantity
    : null;
  const exitChargeTotal = chargesComplete
    ? Object.entries(charges).filter(([key]) => key !== "contractNoteRef").reduce((sum, [, value]) => sum + (Number(value) || 0), 0)
    : null;
  const estimatedNet = estimated != null && entryAllocation != null && exitChargeTotal != null ? estimated - entryAllocation - exitChargeTotal : null;

  const dialogRef = useDialogAccessibility(() => { if (!saving) onClose(); });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numericExitPrice = Number(price);
    if (!Number.isFinite(numericExitPrice) || numericExitPrice <= 0) return setError("Enter the exit price or premium.");
    if (!exitDate || exitDate < trade.entryDate) return setError("Exit date cannot be before entry date.");
    if (isFno) {
      const numericLots = Number(lots);
      if (!Number.isInteger(numericLots) || numericLots <= 0 || numericLots > (trade.remainingLots ?? 0)) return setError(`Lots must be between 1 and ${trade.remainingLots}.`);
    } else {
      const numericQuantity = Number(quantity);
      if (!Number.isFinite(numericQuantity) || numericQuantity <= 0 || numericQuantity > trade.remainingQuantity) return setError(`Quantity must be between 0 and ${formatQuantity(trade.remainingQuantity)}.`);
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        quantity: isFno ? null : Number(quantity),
        exitLots: isFno ? Number(lots) : null,
        exitPrice: numericExitPrice,
        exitDate,
        exitAt: null,
        exitReason: reason || null,
        exitOrderId: exitOrderId || null,
        exitContractNoteRef: exitContractNoteRef || null,
        notes: notes || null,
        charges: isFno ? charges : null,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t record the exit.");
      setSaving(false);
    }
  }

  return (
    <div className={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && !saving && onClose()}>
      <section ref={dialogRef} className={`${styles.dialog} ${styles.dialogWide}`} role="dialog" aria-modal="true" aria-labelledby="exit-title">
        <div className={styles.formHeader}><div><p className={styles.dialogLabel}>{isFno ? "Close contract" : trade.side === "long" ? "Sell position" : "Cover position"}</p><h2 id="exit-title">Exit {trade.symbol}</h2><p>Record an exit lot. Entry details remain locked after this save.</p></div><button type="button" className={styles.closeButton} onClick={onClose} disabled={saving} aria-label="Close exit dialog"><IconClose width={17} height={17} /></button></div>
        <div className={styles.positionNote}><span>{isFno ? `${formatQuantity(trade.remainingLots ?? 0)} lots · ${formatQuantity(trade.remainingQuantity)} units remain open` : `${formatQuantity(trade.remainingQuantity)} shares remain open`}</span><strong>Entry {formatPrice(trade.entryPrice)} · {formatDate(trade.entryDate)}</strong></div>
        <form className={styles.exitForm} onSubmit={submit}>
          <div className={styles.formGrid}>
            {isFno ? <label><span>Exit lots</span><input autoFocus type="number" min="1" max={trade.remainingLots ?? undefined} step="1" value={lots} onChange={(event) => setLots(event.target.value)} /></label> : <label><span>Quantity</span><input autoFocus type="number" min="0.001" max={trade.remainingQuantity} step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>}
            <label><span>{isFno ? "Exit price / premium" : trade.side === "long" ? "Exit price" : "Cover price"}</span><input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} /></label>
            <label><span>Exit date</span><input type="date" min={trade.entryDate} value={exitDate} onChange={(event) => setExitDate(event.target.value)} /></label>
            {isFno && <label><span>Exit reason</span><select value={reason} onChange={(event) => setReason(event.target.value)}><option value="manual">Manual close</option><option value="target">Target</option><option value="stop-loss">Stop-loss</option><option value="expiry">Expiry / settlement</option><option value="exercise">Exercise</option></select></label>}
            {isFno && <label><span>Exit order ID</span><input value={exitOrderId} onChange={(event) => setExitOrderId(event.target.value)} /></label>}
            {isFno && <label><span>Exit contract-note reference</span><input value={exitContractNoteRef} onChange={(event) => setExitContractNoteRef(event.target.value)} /></label>}
            <label className={styles.wideField}><span>Notes</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional exit context" rows={2} /></label>
          </div>
          {isFno && <ChargeFields value={charges} onChange={setCharges} />}
          {estimated != null && <div className={`${styles.estimate} ${estimated >= 0 ? styles.estimateGain : styles.estimateLoss}`}><span>Estimated gross P/L <small>{estimatedNet == null ? "Net preview needs complete charges" : `Net preview ${formatINR(estimatedNet)}`}</small></span><strong>{formatSignedINR(estimated)}</strong></div>}
          {error && <p className={styles.formError} role="alert">{error}</p>}
          <div className={styles.formActions}><Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button><Button type="submit" loading={saving}>Record exit</Button></div>
        </form>
      </section>
    </div>
  );
}

function MarkDialog({ trade, onClose, onSaved }: { trade: Trade; onClose: () => void; onSaved: (value: number) => Promise<void> }) {
  const [value, setValue] = useState(trade.currentLtp == null ? "" : String(trade.currentLtp));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useDialogAccessibility(() => { if (!saving) onClose(); });
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!Number(value) || Number(value) <= 0) return setError("Enter a positive contract mark.");
    setSaving(true);
    try { await onSaved(Number(value)); onClose(); } catch (err) { setError(err instanceof Error ? err.message : "Couldn’t save the mark."); } finally { setSaving(false); }
  }
  return (
    <div className={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && !saving && onClose()}>
      <section ref={dialogRef} className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="mark-title">
        <div className={styles.formHeader}><div><p className={styles.dialogLabel}>Manual contract mark</p><h2 id="mark-title">Update {trade.symbol}</h2><p>Enter the latest futures price or option premium from your broker.</p></div><button type="button" className={styles.closeButton} onClick={onClose} disabled={saving} aria-label="Close mark dialog"><IconClose width={17} height={17} /></button></div>
        <form className={styles.exitForm} onSubmit={submit}><label className={styles.singleField}><span>Current mark (₹)</span><input autoFocus type="number" min="0.01" step="0.01" value={value} onChange={(event) => setValue(event.target.value)} /></label>{error && <p className={styles.formError} role="alert">{error}</p>}<div className={styles.formActions}><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" loading={saving}>Save mark</Button></div></form>
      </section>
    </div>
  );
}

function ChargeDialog({ trade, exit, onClose, onSaved }: { trade: Trade; exit?: TradeExit; onClose: () => void; onSaved: (charges: TradeChargesInput) => Promise<void> }) {
  const existing = exit?.charges ?? trade.entryCharge;
  const [charges, setCharges] = useState<TradeChargesInput>({
    brokerage: existing?.brokerage ?? null,
    sttCtt: existing?.sttCtt ?? null,
    exchangeTransaction: existing?.exchangeTransaction ?? null,
    sebi: existing?.sebi ?? null,
    gst: existing?.gst ?? null,
    stampDuty: existing?.stampDuty ?? null,
    ipft: existing?.ipft ?? null,
    other: existing?.other ?? null,
    contractNoteRef: existing?.contractNoteRef ?? null,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useDialogAccessibility(() => { if (!saving) onClose(); });
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try { await onSaved(charges); onClose(); } catch (err) { setError(err instanceof Error ? err.message : "Couldn’t save charges."); } finally { setSaving(false); }
  }
  return (
    <div className={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && !saving && onClose()}>
      <section ref={dialogRef} className={`${styles.dialog} ${styles.dialogWide}`} role="dialog" aria-modal="true" aria-labelledby="charges-title">
        <div className={styles.formHeader}><div><p className={styles.dialogLabel}>Charge correction</p><h2 id="charges-title">{exit ? "Exit charges" : "Entry charges"}</h2><p>Record the actual values from the broker contract note.</p></div><button type="button" className={styles.closeButton} onClick={onClose} disabled={saving} aria-label="Close charge dialog"><IconClose width={17} height={17} /></button></div>
        <form className={styles.exitForm} onSubmit={submit}><ChargeFields value={charges} onChange={setCharges} />{error && <p className={styles.formError} role="alert">{error}</p>}<div className={styles.formActions}><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" loading={saving}>Save charges</Button></div></form>
      </section>
    </div>
  );
}

function TradeRow({ trade, onEdit, onDelete, onExit, onMark, onCharges }: { trade: Trade; onEdit: (trade: Trade) => void; onDelete: (trade: Trade) => void; onExit: (trade: Trade) => void; onMark: (trade: Trade) => void; onCharges: (trade: Trade, exit?: TradeExit) => void }) {
  const isLong = trade.side === "long";
  const isFno = trade.assetClass === "fno";
  const displayPnl = isFno ? trade.netTotalPnl : trade.totalPnl;
  const expiryNotice = isFno && trade.status === "open" ? expiryWarning(trade.expiryDate) : null;
  const incompleteExit = trade.entryCharge?.complete
    ? trade.exits.find((exit) => !exit.charges?.complete)
    : undefined;
  const chargesAction = trade.chargesComplete
    ? "Charges"
    : incompleteExit
      ? "Complete exit charges"
      : "Complete entry charges";
  return (
    <article className={styles.tradeCard}>
      <div className={styles.tradeTop}>
        <div className={styles.identity}>
          <div className={styles.symbolLine}><strong>{isFno ? trade.underlyingSymbol ?? trade.symbol : trade.symbol}</strong><span className={`${styles.side} ${isLong ? styles.long : styles.short}`}>{isLong ? <IconArrowUp width={12} height={12} /> : <IconArrowDown width={12} height={12} />}{isLong ? "Long" : "Short"}</span><span className={`${styles.status} ${trade.status === "closed" ? styles.closed : styles.open}`}>{trade.status}</span>{isFno && <span className={styles.contractPill}>{trade.instrumentType === "option" ? `${trade.optionType} ${formatPrice(trade.strikePrice ?? 0)}` : "Future"}</span>}</div>
          <span className={styles.meta}>{isFno ? `${trade.exchange} · ${trade.contractSymbol} · ${trade.entryLots} lots × ${trade.lotSize} · expiry ${trade.expiryDate ? formatDate(trade.expiryDate) : "—"}` : `${formatDate(trade.entryDate)} · ${formatQuantity(trade.entryQuantity)} shares at ${formatPrice(trade.entryPrice)}${trade.broker ? ` · ${trade.broker}` : ""}`}</span>
        </div>
        <div className={styles.actions}><Button variant="ghost" size="sm" onClick={() => onExit(trade)} disabled={trade.status === "closed"}>Exit</Button>{isFno && trade.status === "open" && <Button variant="ghost" size="sm" onClick={() => onMark(trade)}>Mark</Button>}{trade.exits.length === 0 && <><Button variant="ghost" size="sm" onClick={() => onEdit(trade)}><IconPencil width={14} height={14} />Edit</Button><Button variant="ghost" size="sm" className={styles.delete} onClick={() => onDelete(trade)}><IconTrash width={14} height={14} />Remove</Button></>}{isFno && <Button variant="ghost" size="sm" onClick={() => onCharges(trade, incompleteExit)}>{chargesAction}</Button>}</div>
      </div>
      <div className={styles.metrics}>
        <div><span>{isFno ? "Open lots" : "Remaining"}</span><strong className="num">{trade.status === "closed" ? "Closed" : isFno ? `${trade.remainingLots} lots` : formatQuantity(trade.remainingQuantity)}</strong></div>
        <div><span>{isFno ? "Contract mark" : "LTP"}</span><strong className="num">{trade.currentLtp == null ? isFno ? <span className={styles.pending}>Mark unavailable</span> : "—" : formatPrice(trade.currentLtp)}</strong>{isFno && trade.currentLtp != null && trade.lastUpdated && <small>{trade.markSource === "manual" ? "Manual" : "Exchange"} · {formatDate(trade.lastUpdated)} {formatTime(trade.lastUpdated)}</small>}</div>
        <div><span>Gross realized</span><strong><PnlValue value={trade.grossRealizedPnl} /></strong></div>
        <div><span>{isFno ? "Net total" : "Unrealized P/L"}</span><strong><PnlValue value={displayPnl} /></strong></div>
        <div><span>{isFno ? "Charges" : "Total P/L"}</span><strong>{isFno ? trade.totalCharges == null ? <span className={styles.pending}>Pending</span> : formatINR(trade.totalCharges) : <PnlValue value={trade.totalPnl} />}</strong></div>
      </div>
      {isFno && !trade.chargesComplete && <p className={styles.warningNote}>Net P/L is provisional until every entry and exit charge is recorded.</p>}
      {expiryNotice && <p className={styles.warningNote}>{expiryNotice} This contract will not be settled automatically.</p>}
      {trade.notes && <p className={styles.notes}>{trade.notes}</p>}
      {trade.exits.length > 0 && <details className={styles.exitHistory}><summary>{trade.exits.length} exit {trade.exits.length === 1 ? "lot" : "lots"}</summary><div className={styles.exitList}>{trade.exits.map((exit) => <div className={styles.exitRow} key={exit.id}><span>{formatDate(exit.exitDate)} · {isFno ? `${exit.exitLots} lots at ${formatPrice(exit.exitPrice)}` : `${formatQuantity(exit.quantity)} shares at ${formatPrice(exit.exitPrice)}`}</span><span className={styles.exitActions}><PnlValue value={isFno ? exit.netRealizedPnl : exit.realizedPnl} />{isFno && <Button variant="ghost" size="sm" onClick={() => onCharges(trade, exit)}>{exit.charges?.complete ? "Charges" : "Add charges"}</Button>}</span></div>)}</div></details>}
    </article>
  );
}

function Summary({ summary, assetClass }: { summary: TradebookSummary; assetClass: TradeAssetClass }) {
  if (assetClass === "fno") {
    return (
      <section className={`${styles.summary} ${styles.summaryFno}`} aria-label="F&O Tradebook summary">
        <div>
          <span>Total P/L</span>
          <strong><PnlValue value={summary.netTotalPnl} /></strong>
          <div className={styles.summarySupporting}>
            <small>Gross {summary.grossTotalPnl == null ? "pending" : formatSignedINR(summary.grossTotalPnl)}</small>
            <small>Charges {summary.totalCharges == null ? "incomplete" : formatINR(summary.totalCharges)}</small>
          </div>
        </div>
        <div>
          <span>Realized P/L</span>
          <strong><PnlValue value={summary.netRealizedPnl} /></strong>
          <div className={styles.summarySupporting}><small>Gross {formatSignedINR(summary.grossRealizedPnl)}</small></div>
        </div>
        <div>
          <span>Unrealized P/L</span>
          <strong><PnlValue value={summary.netUnrealizedPnl} /></strong>
          <div className={styles.summarySupporting}>
            <small>Gross {summary.grossUnrealizedPnl == null ? "pending" : formatSignedINR(summary.grossUnrealizedPnl)}</small>
            <small>{summary.unpricedOpenCount} marks unavailable · {summary.incompleteChargeCount} charges incomplete</small>
          </div>
        </div>
        <div>
          <span>Open book</span>
          <strong>{summary.openExposure == null ? <span className={styles.pending}>Exposure pending</span> : formatINR(summary.openExposure)}</strong>
          <div className={styles.summarySupporting}>
            <small>{summary.openCount} open · {summary.closedCount} closed</small>
            <small>{summary.winRate == null ? "Win rate —" : `Win rate ${summary.winRate.toFixed(1)}%`}</small>
          </div>
        </div>
      </section>
    );
  }

  const cards = [
    { label: "Realized P/L", value: summary.realizedPnl, kind: "pnl" },
    { label: "Unrealized P/L", value: summary.unrealizedPnl, kind: "pnl" },
    { label: "Total P/L", value: summary.totalPnl, kind: "pnl" },
    { label: "Trades", value: summary.tradeCount, kind: "count" },
  ];
  return <section className={styles.summary} aria-label="Equity Tradebook summary">{cards.map(({ label, value, kind }) => <div key={label}><span>{label}</span><strong>{kind === "count" ? value : <PnlValue value={value as number | null} />}</strong>{label === "Trades" && <small>{summary.openCount} open · {summary.closedCount} closed</small>}</div>)}</section>;
}

function TradebookPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const assetClass: TradeAssetClass = searchParams.get("tab") === "fno" ? "fno" : "equity";
  const [trades, setTrades] = useState<Trade[]>([]);
  const [summary, setSummary] = useState<TradebookSummary | null>(null);
  const [quoteErrors, setQuoteErrors] = useState<{ tradeId: string; symbol: string; message: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Trade | null>(null);
  const [tradeFormOpen, setTradeFormOpen] = useState(false);
  const [exitTarget, setExitTarget] = useState<Trade | null>(null);
  const [markTarget, setMarkTarget] = useState<Trade | null>(null);
  const [chargeTarget, setChargeTarget] = useState<{ trade: Trade; exit?: TradeExit } | null>(null);
  const [instrumentFilter, setInstrumentFilter] = useState<"all" | "future" | "option">("all");
  const [underlyingFilter, setUnderlyingFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "open" | "closed">("all");
  const [brokerFilter, setBrokerFilter] = useState("all");
  const [entryFrom, setEntryFrom] = useState("");
  const [entryTo, setEntryTo] = useState("");
  const [expiryFrom, setExpiryFrom] = useState("");
  const [expiryTo, setExpiryTo] = useState("");

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try { const data = await api.getTradebook(assetClass); setTrades(data.trades); setSummary(data.summary); setQuoteErrors(data.quoteErrors); }
    catch (err) { setError(err instanceof Error ? err.message : "Couldn’t load the Tradebook."); }
    finally { setLoading(false); }
  }, [assetClass]);

  useEffect(() => { void load(); }, [load]);

  const saveTrade = useCallback(async (input: TradeInput, id?: string) => { if (id) await api.updateTrade(id, input); else await api.addTrade(input); await load(true); }, [load]);
  const removeTrade = useCallback(async (trade: Trade) => { if (!window.confirm(`Remove ${trade.symbol} from the Tradebook?`)) return; try { await api.deleteTrade(trade.id); await load(true); } catch (err) { setError(err instanceof Error ? err.message : "Couldn’t remove the trade."); } }, [load]);
  const recordExit = useCallback(async (input: TradeExitInput) => { if (!exitTarget) return; await api.exitTrade(exitTarget.id, input); setExitTarget(null); await load(true); }, [exitTarget, load]);
  const refresh = async () => { setRefreshing(true); setError(null); try { const data = await api.refreshTradebook(assetClass); setTrades(data.trades); setSummary(data.summary); setQuoteErrors(data.quoteErrors); } catch (err) { setError(err instanceof Error ? err.message : "Price refresh failed."); } finally { setRefreshing(false); } };
  const active = useMemo(() => trades.filter((trade) => trade.status === "open").length, [trades]);
  const underlyings = useMemo(() => Array.from(new Set(trades.map((trade) => trade.assetClass === "fno" ? trade.underlyingSymbol : trade.symbol).filter((value): value is string => Boolean(value)))).sort(), [trades]);
  const brokers = useMemo(() => Array.from(new Set(trades.map((trade) => trade.broker).filter((value): value is string => Boolean(value)))).sort(), [trades]);
  const filteredTrades = useMemo(() => trades.filter((trade) => {
    const underlying = trade.assetClass === "fno" ? trade.underlyingSymbol : trade.symbol;
    if (assetClass === "fno" && instrumentFilter !== "all" && trade.instrumentType !== instrumentFilter) return false;
    if (underlyingFilter !== "all" && underlying !== underlyingFilter) return false;
    if (statusFilter !== "all" && trade.status !== statusFilter) return false;
    if (brokerFilter !== "all" && trade.broker !== brokerFilter) return false;
    if (entryFrom && trade.entryDate < entryFrom) return false;
    if (entryTo && trade.entryDate > entryTo) return false;
    if (assetClass === "fno" && expiryFrom && (!trade.expiryDate || trade.expiryDate < expiryFrom)) return false;
    if (assetClass === "fno" && expiryTo && (!trade.expiryDate || trade.expiryDate > expiryTo)) return false;
    return true;
  }), [assetClass, brokerFilter, entryFrom, entryTo, expiryFrom, expiryTo, instrumentFilter, statusFilter, trades, underlyingFilter]);
  const resetFilters = () => { setInstrumentFilter("all"); setUnderlyingFilter("all"); setStatusFilter("all"); setBrokerFilter("all"); setEntryFrom(""); setEntryTo(""); setExpiryFrom(""); setExpiryTo(""); };
  const filtersActive = instrumentFilter !== "all" || underlyingFilter !== "all" || statusFilter !== "all" || brokerFilter !== "all" || Boolean(entryFrom || entryTo || expiryFrom || expiryTo);
  const closeTradeForm = () => { setEditing(null); setTradeFormOpen(false); };
  const selectTab = (next: TradeAssetClass) => { const params = new URLSearchParams(searchParams.toString()); params.set("tab", next); router.replace(`${pathname}?${params.toString()}`); setEditing(null); setTradeFormOpen(false); };
  const handleTabKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    const tabs = Array.from(event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? []);
    const currentIndex = tabs.indexOf(event.currentTarget);
    const nextIndex = event.key === "ArrowRight" ? (currentIndex + 1) % tabs.length : event.key === "ArrowLeft" ? (currentIndex - 1 + tabs.length) % tabs.length : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
    if (nextIndex < 0 || tabs.length === 0) return;
    event.preventDefault();
    tabs[nextIndex].focus();
    tabs[nextIndex].click();
  };

  return (
    <AppShell>
      <header className={styles.pageHeader}><div><h1 className={styles.pageTitle}>Tradebook</h1><p className={styles.pageSubtitle}>A separate ledger for equity trades and exact F&O contract performance.</p></div><div className={styles.headerActions}><Button variant="secondary" onClick={() => void refresh()} loading={refreshing} disabled={loading || active === 0}><IconRefresh width={15} height={15} />{refreshing ? "Refreshing" : assetClass === "fno" ? "Refresh contract marks" : "Refresh prices"}</Button><Button onClick={() => { setEditing(null); setTradeFormOpen(true); }}><IconPlus width={15} height={15} /> Add {assetClass === "fno" ? "F&O trade" : "equity trade"}</Button></div></header>
      <nav className={styles.tabs} role="tablist" aria-label="Tradebook sections"><button type="button" role="tab" aria-selected={assetClass === "equity"} className={assetClass === "equity" ? styles.tabActive : styles.tab} onKeyDown={handleTabKeyDown} onClick={() => selectTab("equity")}>Equity <span>{assetClass === "equity" ? trades.length : ""}</span></button><button type="button" role="tab" aria-selected={assetClass === "fno"} className={assetClass === "fno" ? styles.tabActive : styles.tab} onKeyDown={handleTabKeyDown} onClick={() => selectTab("fno")}>F&O <span>{assetClass === "fno" ? trades.length : ""}</span></button></nav>
      {error && <div className={styles.error} role="alert"><span>{error}</span><button type="button" onClick={() => void load()}>Retry</button></div>}
      {summary && <Summary summary={summary} assetClass={assetClass} />}
      {assetClass === "fno" && summary?.incompleteChargeCount ? <p className={styles.pendingNote}>Net P/L is pending actual charges for {summary.incompleteChargeCount} {summary.incompleteChargeCount === 1 ? "trade" : "trades"}. Gross P/L remains available.</p> : null}
      {quoteErrors.length > 0 && <div className={styles.quoteNotice} role="status"><strong>Some contract marks need attention.</strong>{quoteErrors.map((item) => <span key={item.tradeId}>{item.symbol}: {item.message}</span>)}</div>}
      <details className={styles.filterDisclosure}>
        <summary className={styles.filterToggle}>Filters{filtersActive && <span className={styles.filterActive}>Active</span>}</summary>
        <section className={styles.filters} aria-label="Filter trades">
        {assetClass === "fno" && <label><span>Instrument</span><select value={instrumentFilter} onChange={(event) => setInstrumentFilter(event.target.value as "all" | "future" | "option")}><option value="all">All instruments</option><option value="future">Futures</option><option value="option">Options</option></select></label>}
        <label><span>{assetClass === "fno" ? "Underlying" : "Symbol"}</span><select value={underlyingFilter} onChange={(event) => setUnderlyingFilter(event.target.value)}><option value="all">All {assetClass === "fno" ? "underlyings" : "symbols"}</option>{underlyings.map((underlying) => <option key={underlying} value={underlying}>{underlying}</option>)}</select></label>
        <label><span>Status</span><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | "open" | "closed")}><option value="all">Open and closed</option><option value="open">Open</option><option value="closed">Closed</option></select></label>
        <label><span>Broker</span><select value={brokerFilter} onChange={(event) => setBrokerFilter(event.target.value)}><option value="all">All brokers</option>{brokers.map((broker) => <option key={broker} value={broker}>{broker}</option>)}</select></label>
        <label><span>Entry from</span><input type="date" value={entryFrom} onChange={(event) => setEntryFrom(event.target.value)} /></label>
        <label><span>Entry to</span><input type="date" value={entryTo} onChange={(event) => setEntryTo(event.target.value)} /></label>
        {assetClass === "fno" && <>
          <label><span>Expiry from</span><input type="date" value={expiryFrom} onChange={(event) => setExpiryFrom(event.target.value)} /></label>
          <label><span>Expiry to</span><input type="date" value={expiryTo} onChange={(event) => setExpiryTo(event.target.value)} /></label>
        </>}
        <Button type="button" variant="ghost" size="sm" onClick={resetFilters} disabled={!filtersActive}>Clear filters</Button>
        </section>
      </details>
      {tradeFormOpen && <TradeForm assetClass={assetClass} open editing={editing} onSaved={saveTrade} onCancel={closeTradeForm} />}
      {loading ? <div className={styles.skeleton}><Skeleton width="9rem" height="1.2rem" /><Skeleton height="15rem" radius="var(--radius-lg)" /></div> : trades.length === 0 ? <div className={styles.empty}><h2>Your {assetClass === "fno" ? "F&O" : "equity"} Tradebook is empty</h2><p>{assetClass === "fno" ? "Record a long future, Call, or Put with its exact contract details to begin." : "Record your first long or short equity trade to start tracking realized and unrealized P/L."}</p></div> : filteredTrades.length === 0 ? <div className={styles.empty}><h2>No trades match these filters</h2><p>Adjust the dates or selections to see more trades.</p><Button type="button" variant="secondary" onClick={resetFilters}>Clear filters</Button></div> : <section className={styles.list} aria-label={`${assetClass === "fno" ? "F&O" : "Equity"} trade history`}><div className={styles.listHeader}><h2>{assetClass === "fno" ? "F&O contracts" : "Equity trades"}</h2><span>Showing {filteredTrades.length} of {trades.length}</span></div>{filteredTrades.map((trade) => <TradeRow key={trade.id} trade={trade} onEdit={(tradeToEdit) => { setEditing(tradeToEdit); setTradeFormOpen(true); }} onDelete={removeTrade} onExit={setExitTarget} onMark={setMarkTarget} onCharges={(tradeToCharge, exit) => setChargeTarget({ trade: tradeToCharge, exit })} />)}</section>}
      {exitTarget && <ExitDialog trade={exitTarget} onClose={() => setExitTarget(null)} onSubmit={recordExit} />}
      {markTarget && <MarkDialog trade={markTarget} onClose={() => setMarkTarget(null)} onSaved={async (value) => { await api.updateTradeMark(markTarget.id, { ltp: value, source: "manual" }); setMarkTarget(null); await load(true); }} />}
      {chargeTarget && <ChargeDialog key={`${chargeTarget.trade.id}:${chargeTarget.exit?.id ?? "entry"}`} trade={chargeTarget.trade} exit={chargeTarget.exit} onClose={() => setChargeTarget(null)} onSaved={async (charges) => { if (chargeTarget.exit) await api.updateExitCharges(chargeTarget.trade.id, chargeTarget.exit.id, charges); else await api.updateTradeCharges(chargeTarget.trade.id, charges); await load(true); }} />}
    </AppShell>
  );
}

export default function TradebookPage() {
  return (
    <Suspense fallback={<AppShell><div className={styles.skeleton}><Skeleton width="9rem" height="1.2rem" /><Skeleton height="15rem" radius="var(--radius-lg)" /></div></AppShell>}>
      <TradebookPageContent />
    </Suspense>
  );
}
