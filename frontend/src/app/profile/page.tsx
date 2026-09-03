"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { IconCheck, IconClose, IconCopy, IconKey, IconTrash } from "@/components/icons";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { formatDate, formatTime } from "@/lib/format";
import type { ApiKey, CreatedApiKey } from "@/lib/types";
import styles from "./page.module.css";

export default function ProfilePage() {
  const { user } = useAuth();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<CreatedApiKey | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setKeys(await api.getApiKeys());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t load your API keys.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadKeys();
  }, [loadKeys]);

  useEffect(() => {
    if (!newKey) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNewKey(null);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [newKey]);

  const createKey = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Give the API key a name so you can identify it later.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const created = await api.createApiKey(trimmedName);
      setKeys((current) => [created, ...current]);
      setName("");
      setCopied(false);
      setNewKey(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t create the API key.");
    } finally {
      setCreating(false);
    }
  };

  const copyKey = async () => {
    if (!newKey) return;
    try {
      await navigator.clipboard.writeText(newKey.key);
      setCopied(true);
    } catch {
      setError("Couldn’t copy the key. Select it and copy it manually.");
    }
  };

  const revokeKey = async (key: ApiKey) => {
    if (key.revokedAt || !window.confirm(`Revoke “${key.name}”? Applications using this key will stop working.`)) return;
    setRevokingId(key.id);
    setError(null);
    try {
      await api.revokeApiKey(key.id);
      setKeys((current) => current.map((item) => item.id === key.id ? { ...item, revokedAt: new Date().toISOString() } : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t revoke the API key.");
    } finally {
      setRevokingId(null);
    }
  };

  const deleteKey = async (key: ApiKey) => {
    if (!key.revokedAt || !window.confirm(`Permanently delete “${key.name}” from this list?`)) return;
    setDeletingId(key.id);
    setError(null);
    try {
      await api.deleteApiKey(key.id);
      setKeys((current) => current.filter((item) => item.id !== key.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn’t delete the API key.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <AppShell>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.overline}><span className={styles.overlineDot} aria-hidden />Account</div>
          <h1 className={styles.pageTitle}>Profile</h1>
          <p className={styles.pageSubtitle}>Manage your account and integrations.</p>
        </div>
      </header>

      {error && <div className={styles.error} role="alert"><span>{error}</span><button type="button" onClick={() => void loadKeys()} className={styles.retry}>Retry</button></div>}

      <section className={styles.accountSection} aria-labelledby="account-heading">
        <div className={styles.sectionHeader}><div><h2 id="account-heading">Account details</h2><p>Your Folio account information.</p></div></div>
        <dl className={styles.accountGrid}>
          <div><dt>Name</dt><dd>{user?.name ?? "—"}</dd></div>
          <div><dt>Email</dt><dd>{user?.email ?? "—"}</dd></div>
        </dl>
      </section>

      <section className={styles.apiSection} aria-labelledby="api-heading">
        <div className={styles.sectionHeader}>
          <div>
            <div className={styles.sectionEyebrow}><IconKey width={14} height={14} />Developer access</div>
            <h2 id="api-heading">API keys</h2>
            <p>Connect a trusted server-side application to add items to your watchlist.</p>
          </div>
        </div>

        <div className={styles.createRow}>
          <label className={styles.field}>
            <span className={styles.label}>Key name</span>
            <input className={styles.input} value={name} onChange={(event) => setName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void createKey(); }} placeholder="Ideas importer" maxLength={100} />
          </label>
          <Button onClick={() => void createKey()} loading={creating}>{creating ? "Creating" : "Create API key"}</Button>
        </div>

        <p className={styles.securityNote}>Keys can add watchlist items only. Store a new key in your server-side secret manager; Folio will show the full value once.</p>

        <div className={styles.keyList}>
          <div className={styles.listHeader}><h3>Existing keys</h3><span>{keys.length} {keys.length === 1 ? "key" : "keys"}</span></div>
          {loading ? <><Skeleton height="4.5rem" radius="var(--radius-md)" /><Skeleton height="4.5rem" radius="var(--radius-md)" /></> : keys.length === 0 ? <div className={styles.empty}>No API keys yet. Create one when you are ready to connect an external app.</div> : keys.map((key) => {
            const revoked = Boolean(key.revokedAt);
            return <div className={styles.keyRow} key={key.id}>
              <div className={styles.keyIcon} aria-hidden><IconKey width={16} height={16} /></div>
              <div className={styles.keyInfo}><strong>{key.name}</strong><code>{key.keyPrefix}********</code><span>Created {formatDate(key.createdAt)}{key.lastUsedAt ? ` · Last used ${formatTime(key.lastUsedAt)}` : " · Not used yet"}</span></div>
              <span className={`${styles.status} ${revoked ? styles.revoked : styles.active}`}>{revoked ? "Revoked" : "Active"}</span>
              {revoked ? <Button variant="ghost" size="sm" className={styles.deleteKey} onClick={() => void deleteKey(key)} loading={deletingId === key.id} aria-label={`Permanently delete ${key.name}`} title={`Permanently delete ${key.name}`}>{deletingId !== key.id && <IconTrash width={14} height={14} />} {deletingId === key.id ? "Deleting" : "Delete"}</Button> : <Button variant="ghost" size="sm" className={styles.revoke} onClick={() => void revokeKey(key)} loading={revokingId === key.id} aria-label={`Revoke ${key.name}`} title={`Revoke ${key.name}`}>{revokingId !== key.id && <IconTrash width={14} height={14} />} {revokingId === key.id ? "Revoking" : "Revoke"}</Button>}
            </div>;
          })}
        </div>
      </section>

      {newKey && <div className={styles.modalBackdrop} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setNewKey(null); }}>
        <section className={styles.modal} role="dialog" aria-modal="true" aria-labelledby="new-key-heading">
          <button type="button" className={styles.modalClose} onClick={() => setNewKey(null)} aria-label="Close API key dialog"><IconClose width={17} height={17} /></button>
          <div className={styles.modalIcon} aria-hidden><IconKey width={20} height={20} /></div>
          <h2 id="new-key-heading">Your API key is ready</h2>
          <p>Copy this key now. For your security, the full value will not be shown again.</p>
          <div className={styles.secretBox}><code>{newKey.key}</code><Button variant="secondary" size="sm" onClick={() => void copyKey()}>{copied ? <IconCheck width={14} height={14} /> : <IconCopy width={14} height={14} />}{copied ? "Copied" : "Copy key"}</Button></div>
          <div className={styles.modalWarning} role="status">Treat this key like a password. Never commit it to source control or put it in browser code.</div>
          <Button className={styles.modalAction} onClick={() => setNewKey(null)}>{copied ? "Done" : "I’ve saved the key"}</Button>
        </section>
      </div>}
    </AppShell>
  );
}
