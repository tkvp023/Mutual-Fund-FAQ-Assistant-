"use client";

import styles from "./SourceCard.module.css";

interface SourceCardProps {
  section: string;
  fund:    string;
  url:     string;
}

const SECTION_META: Record<string, { label: string; color: string; description: string }> = {
  overview:            { label: "FACTSHEET",  color: "var(--badge-factsheet)",  description: "Key metrics: NAV, AUM, expense ratio, benchmark, and risk profile." },
  returns:             { label: "RETURNS",    color: "var(--badge-returns)",    description: "Historical return data: 1Y, 3Y, 5Y, 10Y annualised and absolute returns." },
  holdings:            { label: "HOLDINGS",   color: "var(--badge-holdings)",   description: "Portfolio allocation: stocks, sectors, and asset weights." },
  faq:                 { label: "FAQ",        color: "var(--badge-faq)",        description: "Frequently asked questions about the fund scheme." },
  exit_load_tax:       { label: "TAX & FEES", color: "var(--badge-exit-load)",  description: "Exit load, stamp duty, LTCG/STCG tax implications." },
  fund_management:     { label: "MANAGEMENT", color: "var(--badge-fund-mgmt)",  description: "Fund manager details, experience, and other managed schemes." },
  peer_comparison:     { label: "COMPARISON", color: "var(--badge-peer)",       description: "Side-by-side comparison with similar category funds." },
  performance_ranking: { label: "RANKING",    color: "var(--badge-returns)",    description: "Category rank, risk statistics (Sharpe, alpha, beta)." },
  investment_info:     { label: "INVESTMENT",  color: "var(--badge-overview)",  description: "Minimum SIP, lumpsum amounts, and investment terms." },
  about_fund:          { label: "ABOUT",       color: "var(--badge-article)",  description: "Scheme description, objective, and benchmark index." },
  fund_house:          { label: "FUND HOUSE",  color: "var(--badge-sid)",      description: "AMC details: rank, AUM, contact, and custodian info." },
};

export default function SourceCard({ section, fund, url }: SourceCardProps) {
  const meta = SECTION_META[section] || {
    label: section.toUpperCase(),
    color: "var(--text-muted)",
    description: "Source data chunk.",
  };

  // Short fund name for display
  const shortFund = fund
    .replace("Direct Growth", "")
    .replace("Direct Plan Growth", "")
    .trim();

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.badge} style={{ background: meta.color }}>
          {meta.label}
        </span>
        <a href={url} target="_blank" rel="noopener noreferrer" className={styles.externalLink}>
          ↗
        </a>
      </div>
      <h4 className={styles.title}>{shortFund}</h4>
      <p className={styles.description}>{meta.description}</p>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className={styles.viewLink}
      >
        View on Groww &rsaquo;
      </a>
    </div>
  );
}
