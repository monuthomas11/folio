"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { IconDownload, IconUpload } from "@/components/icons";
import { api } from "@/lib/api";
import type { ImportResult } from "@/lib/types";
import styles from "./import-export.module.css";

interface ImportExportProps {
  disabled?: boolean;
  onImported: () => Promise<void> | void;
  onError: (message: string) => void;
}

function download(csv: string, filename: string): void {
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ImportExport({ disabled = false, onImported, onError }: ImportExportProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);

  const handleExport = async () => {
    setExporting(true);
    setResult(null);
    setResultError(null);
    try {
      const csv = await api.exportHoldings();
      download(csv, "holdings.csv");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  };

  const handleFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setImporting(true);
    setResult(null);
    setResultError(null);
    try {
      const text = await file.text();
      const res = await api.importHoldings(text);
      setResult(res);
      if (res.created > 0) await onImported();
      if (res.errors.length > 0) {
        const sample = res.errors.slice(0, 3).map((err) => `Row ${err.row}: ${err.message}`);
        setResultError(
          `${res.errors.length} row(s) skipped — ${sample.join(" | ")}${res.errors.length > 3 ? " …" : ""}`,
        );
      }
    } catch (err) {
      setResultError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.actions}>
        <Button
          variant="secondary"
          onClick={() => void handleExport()}
          loading={exporting}
          disabled={disabled || importing}
        >
          {!exporting && <IconDownload width={15} height={15} />}
          {exporting ? "Exporting" : "Export"}
        </Button>
        <Button
          variant="secondary"
          onClick={() => fileInputRef.current?.click()}
          loading={importing}
          disabled={exporting}
        >
          {!importing && <IconUpload width={15} height={15} />}
          {importing ? "Importing" : "Import"}
        </Button>
        <input
          ref={fileInputRef}
          className={styles.fileInput}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => void handleFile(e)}
          aria-label="Import holdings from CSV"
        />
      </div>

      {result && (
        <p className={styles.result} role="status">
          Imported {result.created} holding{result.created === 1 ? "" : "s"}.
        </p>
      )}
      {resultError && (
        <p className={styles.resultError} role="alert">
          {resultError}
        </p>
      )}

      <p className={styles.hint}>
        CSV columns: symbol, quantity, avg_buy_price, stop_loss, target_price, broker, sector
      </p>
    </div>
  );
}