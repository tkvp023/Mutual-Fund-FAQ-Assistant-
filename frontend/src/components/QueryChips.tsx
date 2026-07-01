"use client";

import styles from "./QueryChips.module.css";

interface QueryChipsProps {
  onSelect: (query: string) => void;
}

const SUGGESTIONS = [
  {
    icon: "🏛",
    text: "What is the expense ratio of HDFC Mid Cap Fund?",
  },
  {
    icon: "📈",
    text: "What is the exit load for HDFC Gold ETF FoF?",
  },
  {
    icon: "📊",
    text: "Compare 5Y returns of all HDFC funds",
  },
  {
    icon: "👤",
    text: "Who manages HDFC Small Cap Fund?",
  },
];

export default function QueryChips({ onSelect }: QueryChipsProps) {
  return (
    <div className={styles.welcome}>
      {/* Branding header */}
      <div className={styles.brandRow}>
        <h1 className={styles.brandName}>
          FundFacts <span className={styles.brandIcon}>📈</span>
        </h1>
        <span className={styles.brandSub}>HDFC · POWERED BY GROQ</span>
      </div>

      <div className={styles.badges}>
        <span className={styles.badgeGroq}>⚡ Groq LPU</span>
        <span className={styles.badgeFacts}>⚠ Facts Only</span>
      </div>

      {/* Hero */}
      <div className={styles.hero}>
        <div className={styles.shieldIcon}>🛡</div>
        <h2 className={styles.heroTitle}>Factual answers about HDFC Mutual Funds</h2>
        <p className={styles.heroSub}>
          Ask me anything about scheme details, performance, expense ratios, or exit loads.
          Verified against official documents.
        </p>
      </div>

      {/* Suggestion chips */}
      <div className={styles.chipGrid}>
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            className={styles.chip}
            onClick={() => onSelect(s.text)}
          >
            <span className={styles.chipIcon}>{s.icon}</span>
            <span className={styles.chipText}>{s.text}</span>
          </button>
        ))}
      </div>

      {/* Data source */}
      <div className={styles.sourcesRow}>
        <span className={styles.sourcesLabel}>DATA SOURCE</span>
        <div className={styles.sourceBadges}>
          <span className={styles.sourceBadge}>Groww.in</span>
        </div>
      </div>
    </div>
  );
}
