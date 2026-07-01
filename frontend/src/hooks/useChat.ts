"use client";

import { useState, useCallback, useRef } from "react";
import { sendMessage, ChatResponse } from "@/lib/api";

/* ── Types ──────────────────────────────────────────────────────────────── */
export interface Message {
  id:          string;
  role:        "user" | "assistant";
  content:     string;
  timestamp:   number;
  // Only on assistant messages:
  sources?:    ChatResponse;
  isAdvisory?: boolean;
  isError?:    boolean;
}

export interface ChatSession {
  id:        string;
  title:     string;
  fundTags:  string[];
  createdAt: number;
}

/* ── Advisory detection ─────────────────────────────────────────────────── */
const ADVISORY_KEYWORDS = [
  "cannot provide investment advice",
  "not provide financial advice",
  "outside scope",
  "advisory query",
  "cannot recommend",
  "consult a financial advisor",
  "not qualified to advise",
];

function isAdvisoryResponse(answer: string): boolean {
  const lower = answer.toLowerCase();
  return ADVISORY_KEYWORDS.some((kw) => lower.includes(kw));
}

/* ── Extract short fund tags from fund names ────────────────────────────── */
function extractFundTags(funds: string[]): string[] {
  return funds.map((f) => {
    if (f.includes("Mid Cap"))    return "Mid Cap";
    if (f.includes("Large Cap"))  return "Large Cap";
    if (f.includes("Small Cap"))  return "Small Cap";
    if (f.includes("Gold"))       return "Gold ETF";
    if (f.includes("Silver"))     return "Silver ETF";
    return f.split(" ").slice(1, 3).join(" ");
  });
}

/* ── Hook ───────────────────────────────────────────────────────────────── */
export function useChat() {
  const [messages, setMessages]     = useState<Message[]>([]);
  const [isLoading, setIsLoading]   = useState(false);
  const [sessionId, setSessionId]   = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("mf-session-id");
      if (stored) return stored;
      const id = crypto.randomUUID();
      localStorage.setItem("mf-session-id", id);
      return id;
    }
    return crypto.randomUUID();
  });
  const [chatHistory, setChatHistory] = useState<ChatSession[]>(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("mf-chat-history");
      return stored ? JSON.parse(stored) : [];
    }
    return [];
  });
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  /* ── Send a message ──────────────────────────────────────────────────── */
  const send = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;

    // Add user message
    const userMsg: Message = {
      id:        crypto.randomUUID(),
      role:      "user",
      content:   query.trim(),
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await sendMessage(query.trim(), sessionId);
      const advisory = isAdvisoryResponse(response.answer);

      const assistantMsg: Message = {
        id:         crypto.randomUUID(),
        role:       "assistant",
        content:    response.answer,
        timestamp:  Date.now(),
        sources:    response,
        isAdvisory: advisory,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setLatestResponse(response);

      // Update chat history in sidebar
      const fundTags = extractFundTags(response.source_funds);
      setChatHistory((prev) => {
        const existing = prev.find((s) => s.id === sessionId);
        let updated: ChatSession[];
        if (existing) {
          updated = prev.map((s) =>
            s.id === sessionId
              ? { ...s, title: query.trim().slice(0, 40), fundTags }
              : s,
          );
        } else {
          updated = [
            { id: sessionId, title: query.trim().slice(0, 40), fundTags, createdAt: Date.now() },
            ...prev,
          ];
        }
        localStorage.setItem("mf-chat-history", JSON.stringify(updated.slice(0, 20)));
        return updated;
      });
    } catch (err) {
      const errorMsg: Message = {
        id:        crypto.randomUUID(),
        role:      "assistant",
        content:   `Something went wrong: ${err instanceof Error ? err.message : "Unknown error"}. Please try again.`,
        timestamp: Date.now(),
        isError:   true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId]);

  /* ── New chat ────────────────────────────────────────────────────────── */
  const newChat = useCallback(() => {
    const id = crypto.randomUUID();
    setSessionId(id);
    setMessages([]);
    setLatestResponse(null);
    localStorage.setItem("mf-session-id", id);
  }, []);

  return {
    messages,
    isLoading,
    sessionId,
    chatHistory,
    latestResponse,
    send,
    newChat,
  };
}
