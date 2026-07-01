"use client";

import { useRef, useEffect, useState } from "react";
import { Message } from "@/hooks/useChat";
import { ChatResponse } from "@/lib/api";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import QueryChips from "./QueryChips";
import styles from "./ChatInterface.module.css";

interface ChatInterfaceProps {
  messages:       Message[];
  isLoading:      boolean;
  latestResponse: ChatResponse | null;
  onSend:         (query: string) => void;
  onToggleSources: () => void;
  sourcesOpen:    boolean;
}

export default function ChatInterface({
  messages,
  isLoading,
  latestResponse,
  onSend,
  onToggleSources,
  sourcesOpen,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  const isWelcome = messages.length === 0;

  // Auto-scroll on new message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput("");
  };

  const handleChipSelect = (query: string) => {
    onSend(query);
  };

  return (
    <div className={styles.container}>
      {/* Status bar */}
      {!isWelcome && (
        <div className={styles.statusBar}>
          <div className={styles.statusLeft}>
            <span className={styles.statusItem}>
              ⏱ Latency: {latestResponse ? `${latestResponse.response_time_ms}ms` : "--"}
            </span>
          </div>
          <span className={styles.statusOnline}>✅ Online</span>
        </div>
      )}

      {/* Messages area */}
      <div className={styles.messagesArea} ref={scrollRef}>
        {isWelcome ? (
          <QueryChips onSelect={handleChipSelect} />
        ) : (
          <div className={styles.messagesList}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className={styles.inputArea}>
        <form className={styles.inputForm} onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            className={styles.input}
            placeholder={isWelcome ? "Ask about any HDFC fund..." : "Ask a follow-up question..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            id="chat-input"
          />
          {!isWelcome && latestResponse && (
            <button
              type="button"
              className={styles.sourcesToggle}
              onClick={onToggleSources}
              title="Toggle sources"
            >
              📋 {sourcesOpen ? "" : latestResponse.num_chunks}
            </button>
          )}
          <button
            type="submit"
            className={`${styles.sendBtn} ${input.trim() ? styles.sendBtnActive : ""}`}
            disabled={!input.trim() || isLoading}
            id="send-btn"
          >
            ↑
          </button>
        </form>

        <p className={styles.disclaimer}>
          AI can make mistakes. Verify important financial data.
        </p>
      </div>

      {/* Bottom disclaimer bar */}
      <div className={styles.disclaimerBar}>
        <span className={styles.disclaimerText}>
          Equity investments are subject to market risks. Read all scheme related documents carefully before investing.
        </span>
      </div>
    </div>
  );
}
