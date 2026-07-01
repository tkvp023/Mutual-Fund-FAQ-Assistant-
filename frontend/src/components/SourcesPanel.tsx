"use client";

import { ChatResponse } from "@/lib/api";
import SourceCard from "./SourceCard";
import styles from "./SourcesPanel.module.css";

interface SourcesPanelProps {
  response: ChatResponse | null;
  isOpen:   boolean;
  onClose:  () => void;
}

export default function SourcesPanel({ response, isOpen, onClose }: SourcesPanelProps) {
  if (!isOpen || !response) return null;

  // Build source cards from the response metadata
  const sourceCards = response.source_sections.map((section, i) => ({
    section,
    fund:   response.source_funds[i] || response.source_funds[0] || "Unknown",
    url:    response.source_urls[i]  || response.source_urls[0]  || "#",
  }));

  // Deduplicate by fund+section
  const unique = sourceCards.filter(
    (s, i, arr) => arr.findIndex((x) => x.fund === s.fund && x.section === s.section) === i
  );

  return (
    <aside className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h3>Sources</h3>
          <span className={styles.count}>{unique.length}</span>
        </div>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Close sources">
          ✕
        </button>
      </div>

      <div className={styles.cardList}>
        {unique.map((src, i) => (
          <SourceCard key={i} section={src.section} fund={src.fund} url={src.url} />
        ))}
      </div>

      {/* Context active card */}
      <div className={styles.contextCard}>
        <div className={styles.contextLabel}>CONTEXT ACTIVE</div>
        <p className={styles.contextText}>{response.context_summary}</p>
      </div>
    </aside>
  );
}
