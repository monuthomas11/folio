"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, ApiError } from "@/lib/api";
import { IconClose, IconSend, IconSparkles } from "@/components/icons";
import type { ChatMessage } from "@/lib/types";
import styles from "./ask-ai.module.css";

const MAX_SENT_HISTORY = 10;

const STARTERS: Record<"portfolio" | "holding", string[]> = {
  portfolio: [
    "Which positions need attention?",
    "How concentrated is my portfolio?",
    "What should I do first?",
  ],
  holding: [
    "Why this rating?",
    "What should I watch for?",
    "Should I add or reduce?",
  ],
};

interface AskAiProps {
  context: "portfolio" | "holding";
  holdingId?: string;
  label?: string;
  enabled: boolean;
}

export function AskAi({ context, holdingId, label, enabled }: AskAiProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastReply, setLastReply] = useState<{ reply: string; provider: string } | null>(null);

  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const drawerTitle = label ?? "Ask AI";

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, sending, open]);

  useEffect(() => {
    if (open) {
      const id = window.setTimeout(() => inputRef.current?.focus(), 50);
      return () => window.clearTimeout(id);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const trigger = triggerRef.current;
    return () => {
      trigger?.focus();
    };
  }, [open]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending || !enabled) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const history = [...messages, userMessage].slice(-MAX_SENT_HISTORY);
    const prior = history.slice(0, -1).map((m) => ({ role: m.role, content: m.content }));

    setMessages(history);
    setDraft("");
    setSending(true);
    setError(null);
    try {
      const res = await api.askAi({
        context,
        ...(context === "holding" && holdingId ? { holdingId } : {}),
        message: trimmed,
        history: prior,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setLastReply({ reply: res.reply, provider: res.provider });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't get an answer.");
      if (err instanceof ApiError && err.status === 404) {
        setError("No analysis available for this context yet. Run an analysis first.");
      }
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = () => {
    void send(draft);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(draft);
    }
  };

  const pickStarter = (q: string) => {
    void send(q);
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={`${styles.trigger} ${!enabled ? styles.triggerDisabled : ""}`}
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="ask-ai-drawer"
        title={!enabled ? "Run an analysis first to ask questions" : "Ask AI about this analysis"}
      >
        <span className={styles.triggerIcon} aria-hidden>
          <IconSparkles width={14} height={14} />
        </span>
        <span>Ask AI</span>
        {messages.length > 0 && <span className={styles.triggerBadge} aria-hidden>{messages.length}</span>}
      </button>

      {open && (
        <div className={styles.overlay} onClick={() => setOpen(false)}>
          <section
            id="ask-ai-drawer"
            className={styles.drawer}
            role="dialog"
            aria-modal="true"
            aria-label={drawerTitle}
            onClick={(e) => e.stopPropagation()}
          >
            <header className={styles.drawerHead}>
              <div className={styles.drawerTitle}>
                <span className={styles.drawerIcon} aria-hidden>
                  <IconSparkles width={14} height={14} />
                </span>
                <div>
                  <h2 className={styles.drawerHeading}>{drawerTitle}</h2>
                  <p className={styles.drawerSub}>Live fundamentals, news and your stored analysis</p>
                </div>
              </div>
              <button type="button" className={styles.close} onClick={() => setOpen(false)} aria-label="Close Ask AI">
                <IconClose width={16} height={16} />
              </button>
            </header>

            {!enabled && (
              <div className={styles.notice} role="status">
                <span className={styles.noticeDot} aria-hidden />
                Run an analysis first to ask questions about this {context === "portfolio" ? "portfolio" : "holding"}.
              </div>
            )}

            {lastReply && enabled && (
              <div className={styles.providerRow}>
                <span className={styles.providerTag}>
                  {lastReply.provider === "mock" ? "Mock analysis" : `via ${lastReply.provider}`}
                </span>
              </div>
            )}

            <div ref={listRef} className={styles.scroll} role="log" aria-live="polite" aria-label="Conversation">
              {messages.length === 0 ? (
                <div className={styles.empty}>
                  <div className={styles.emptyIcon} aria-hidden>
                    <IconSparkles width={18} height={18} />
                  </div>
                  <p className={styles.emptyTitle}>{enabled ? "Ask about this analysis" : "No analysis yet"}</p>
                  <p className={styles.emptyText}>
                    {enabled
                      ? "Ask about this analysis — answers combine fresh fundamentals and news with your stored analysis and holdings."
                      : "Run an analysis first to ask questions about this context. The AI answers from the latest recommendation and your positions."}
                  </p>
                </div>
              ) : (
                messages.map((m, i) => (
                  <div key={i} className={m.role === "user" ? styles.bubbleUser : styles.bubbleAssistant}>
                    <span className={styles.bubbleMeta}>{m.role === "user" ? "You" : "AI"}</span>
                    {m.role === "user" ? (
                      <p className={styles.bubbleText}>{m.content}</p>
                    ) : (
                      <div className={`${styles.bubbleText} ${styles.bubbleMarkdown}`}>
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className={styles.mdParagraph}>{children}</p>,
                            ul: ({ children }) => <ul className={styles.mdList}>{children}</ul>,
                            ol: ({ children }) => <ol className={styles.mdList}>{children}</ol>,
                            li: ({ children }) => <li className={styles.mdListItem}>{children}</li>,
                            h1: ({ children }) => <h1 className={styles.mdHeading}>{children}</h1>,
                            h2: ({ children }) => <h2 className={styles.mdHeading}>{children}</h2>,
                            h3: ({ children }) => <h3 className={styles.mdHeading}>{children}</h3>,
                            h4: ({ children }) => <h4 className={styles.mdHeading}>{children}</h4>,
                            strong: ({ children }) => <strong className={styles.mdStrong}>{children}</strong>,
                            em: ({ children }) => <em className={styles.mdEm}>{children}</em>,
                            a: ({ href, children }) => (
                              <a className={styles.mdLink} href={href} target="_blank" rel="noopener noreferrer">
                                {children}
                              </a>
                            ),
                            code: ({ children }) => <code className={styles.mdCode}>{children}</code>,
                          }}
                        >
                          {m.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                ))
              )}

              {sending && (
                <div className={styles.bubbleAssistant}>
                  <span className={styles.bubbleMeta}>AI</span>
                  <p className={`${styles.bubbleText} ${styles.thinking}`} aria-hidden>
                    Thinking…
                  </p>
                </div>
              )}
            </div>

            {enabled && messages.length === 0 && (
              <div className={styles.starters}>
                {STARTERS[context].map((q) => (
                  <button key={q} type="button" className={styles.starter} onClick={() => pickStarter(q)} disabled={sending}>
                    {q}
                  </button>
                ))}
              </div>
            )}

            {error && (
              <div className={styles.error} role="alert">
                <span>{error}</span>
                <button type="button" className={styles.retry} onClick={() => inputRef.current?.focus()}>
                  Dismiss
                </button>
              </div>
            )}

            <div className={styles.composer}>
              <label className={styles.srOnly} htmlFor="ask-ai-input">
                Ask a question about this analysis
              </label>
              <textarea
                id="ask-ai-input"
                ref={inputRef}
                className={styles.input}
                rows={2}
                value={draft}
                placeholder={enabled ? "Ask a question…" : "Run an analysis to enable chat"}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={!enabled || sending}
              />
              <button
                type="button"
                className={styles.send}
                onClick={handleSubmit}
                disabled={!enabled || !draft.trim() || sending}
                aria-label="Send"
              >
                <IconSend width={16} height={16} />
              </button>
            </div>

            <p className={styles.disclaimer}>Informational only — not personalized investment advice.</p>
          </section>
        </div>
      )}
    </>
  );
}
