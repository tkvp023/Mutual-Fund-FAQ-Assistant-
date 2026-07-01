"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message } from "@/hooks/useChat";
import styles from "./MessageBubble.module.css";
import { useState } from "react";

interface MessageBubbleProps {
  message: Message;
}

/* ── Section badge color mapping ────────────────────────────────────────── */
const SECTION_COLORS: Record<string, string> = {
  overview:            "var(--badge-overview)",
  returns:             "var(--badge-returns)",
  holdings:            "var(--badge-holdings)",
  faq:                 "var(--badge-faq)",
  exit_load_tax:       "var(--badge-exit-load)",
  fund_management:     "var(--badge-fund-mgmt)",
  peer_comparison:     "var(--badge-peer)",
  performance_ranking: "var(--badge-returns)",
  investment_info:     "var(--badge-overview)",
  about_fund:          "var(--badge-article)",
  fund_house:          "var(--badge-sid)",
};

function getSectionLabel(section: string): string {
  const labels: Record<string, string> = {
    overview:            "FACTSHEET",
    returns:             "RETURNS",
    holdings:            "HOLDINGS",
    faq:                 "FAQ",
    exit_load_tax:       "TAX & FEES",
    fund_management:     "MANAGEMENT",
    peer_comparison:     "COMPARISON",
    performance_ranking: "RANKING",
    investment_info:     "INVESTMENT",
    about_fund:          "ABOUT",
    fund_house:          "FUND HOUSE",
  };
  return labels[section] || section.toUpperCase();
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  /* ── User bubble ──────────────────────────────────────────────────────── */
  if (message.role === "user") {
    return (
      <div className={styles.userContainer}>
        <div className={styles.userBubble}>
          {message.content}
        </div>
      </div>
    );
  }

  /* ── Error bubble ─────────────────────────────────────────────────────── */
  if (message.isError) {
    return (
      <div className={styles.assistantContainer}>
        <div className={styles.errorBubble}>
          <div className={styles.errorHeader}>
            <span className={styles.errorIcon}>⚠</span>
            <span>Error</span>
          </div>
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  /* ── Advisory bubble ──────────────────────────────────────────────────── */
  if (message.isAdvisory) {
    return (
      <div className={styles.assistantContainer}>
        <div className={styles.advisoryWarning}>
          <span className={styles.advisoryIcon}>⛔</span>
        </div>
        <div className={styles.advisoryBubble}>
          <div className={styles.advisoryHeader}>
            ⛔ ADVISORY QUERY — OUTSIDE SCOPE
          </div>
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>

        {/* Suggestion cards */}
        <div className={styles.advisoryCards}>
          <a
            href="https://www.amfiindia.com/investor-corner"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.advisoryCard}
          >
            <div className={styles.advisoryCardIcon}>🔗</div>
            <div>
              <strong>AMFI Investor Education</strong>
              <span>Learn more about evaluating mutual funds and understanding market risks independently.</span>
            </div>
            <span className={styles.externalIcon}>↗</span>
          </a>
          <div className={styles.advisoryCardAlt}>
            <div className={styles.advisoryCardIcon}>📊</div>
            <div>
              <strong>View Objective Data Instead</strong>
              <span>I can show you the expense ratio, AUM, and historical performance for HDFC funds.</span>
            </div>
            <span className={styles.arrowIcon}>→</span>
          </div>
        </div>

        <div className={styles.noSources}>
          <span>📋 Sources</span>
          <em>No factual sources cited for advisory query.</em>
        </div>
      </div>
    );
  }

  /* ── Normal assistant bubble ──────────────────────────────────────────── */
  const sources = message.sources;
  return (
    <div className={styles.assistantContainer}>
      <div className={styles.assistantBubble}>
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Source badge */}
        {sources && sources.source_urls.length > 0 && (
          <div className={styles.sourceBadgeRow}>
            <span className={styles.sourceLabel}>Source:</span>
            <a
              href={sources.source_urls[0]}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.sourceBadge}
            >
              🔗 Groww.in
            </a>
          </div>
        )}

        {/* Divider + Stats footer */}
        {sources && (
          <>
            <div className={styles.divider} />
            <div className={styles.statsRow}>
              <span className={styles.modelInfo}>
                ⚡ {sources.model} · {(sources.response_time_ms / 1000).toFixed(1)}s
              </span>
              <div className={styles.actions}>
                <button onClick={handleCopy} title="Copy" className={styles.actionBtn}>
                  {copied ? "✓" : "📋"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
