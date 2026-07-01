"use client";

import { ChatSession } from "@/hooks/useChat";
import styles from "./Sidebar.module.css";

interface SidebarProps {
  chatHistory: ChatSession[];
  onNewChat:   () => void;
  isOpen:      boolean;
  onToggle:    () => void;
}

export default function Sidebar({ chatHistory, onNewChat, isOpen, onToggle }: SidebarProps) {
  return (
    <>
      {/* Mobile hamburger */}
      <button className={styles.mobileToggle} onClick={onToggle} aria-label="Toggle sidebar">
        ☰
      </button>

      {/* Overlay for mobile */}
      {isOpen && <div className={styles.overlay} onClick={onToggle} />}

      <aside className={`${styles.sidebar} ${isOpen ? styles.sidebarOpen : ""}`}>
        {/* Identity */}
        <div className={styles.identity}>
          <div className={styles.avatar}>📈</div>
          <div className={styles.identityText}>
            <h3>Assistant</h3>
            <span>HDFC Navigator</span>
          </div>
        </div>

        {/* New Chat */}
        <button className={styles.newChatBtn} onClick={onNewChat} id="new-chat-btn">
          <span>⊕</span> New Chat
        </button>

        {/* Nav Items */}
        <button className={styles.navItemActive}>
          <span className={styles.navIcon}>⏱</span> History
        </button>

        {/* History items */}
        <div className={styles.historySection}>
          {chatHistory.slice(0, 10).map((session) => (
            <button key={session.id} className={styles.historyItem}>
              {session.title}
              {session.fundTags.slice(0, 1).map((tag) => (
                <span key={tag} className={styles.historyTag}>{tag}</span>
              ))}
            </button>
          ))}
        </div>

        {/* Bottom section */}
        <div className={styles.bottomSection}>
          <div className={styles.techStack}>
            ⚡ BGE + ChromaDB + Groq
          </div>
        </div>
      </aside>
    </>
  );
}
