"use client";

import { useState, useCallback, useRef, useEffect } from "react";
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

/* ── localStorage helpers ───────────────────────────────────────────────── */
const MAX_SESSIONS = 20;

function saveMessages(sessionId: string, messages: Message[]) {
  try {
    localStorage.setItem(`mf-messages-${sessionId}`, JSON.stringify(messages));
  } catch {
    // localStorage full — silently fail
  }
}

function loadMessages(sessionId: string): Message[] {
  try {
    const stored = localStorage.getItem(`mf-messages-${sessionId}`);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function pruneOldSessions(sessions: ChatSession[]) {
  // Remove messages for sessions beyond the cap
  const toRemove = sessions.slice(MAX_SESSIONS);
  for (const s of toRemove) {
    localStorage.removeItem(`mf-messages-${s.id}`);
  }
  return sessions.slice(0, MAX_SESSIONS);
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

  /* ── Restore messages for the current session on mount ─────────────── */
  useEffect(() => {
    const restored = loadMessages(sessionId);
    if (restored.length > 0) {
      setMessages(restored);
      // Restore latestResponse from the last assistant message
      const lastAssistant = [...restored].reverse().find((m) => m.role === "assistant" && m.sources);
      if (lastAssistant?.sources) {
        setLatestResponse(lastAssistant.sources);
      }
    }
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Persist messages whenever they change ─────────────────────────── */
  useEffect(() => {
    if (messages.length > 0) {
      saveMessages(sessionId, messages);
    }
  }, [messages, sessionId]);

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
        const pruned = pruneOldSessions(updated);
        localStorage.setItem("mf-chat-history", JSON.stringify(pruned));
        return pruned;
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

  /* ── Load a past session ─────────────────────────────────────────────── */
  const loadSession = useCallback((targetSessionId: string) => {
    if (targetSessionId === sessionId) return; // Already active

    // Save current messages before switching
    if (messages.length > 0) {
      saveMessages(sessionId, messages);
    }

    // Switch to the target session
    setSessionId(targetSessionId);
    localStorage.setItem("mf-session-id", targetSessionId);

    // Load messages from localStorage
    const restored = loadMessages(targetSessionId);
    setMessages(restored);

    // Restore latestResponse from the last assistant message
    const lastAssistant = [...restored].reverse().find((m) => m.role === "assistant" && m.sources);
    setLatestResponse(lastAssistant?.sources ?? null);
  }, [sessionId, messages]);

  /* ── New chat ────────────────────────────────────────────────────────── */
  const newChat = useCallback(() => {
    // Save current messages before starting a new chat
    if (messages.length > 0) {
      saveMessages(sessionId, messages);
    }

    const id = crypto.randomUUID();
    setSessionId(id);
    setMessages([]);
    setLatestResponse(null);
    localStorage.setItem("mf-session-id", id);
  }, [sessionId, messages]);

  return {
    messages,
    isLoading,
    sessionId,
    chatHistory,
    latestResponse,
    send,
    newChat,
    loadSession,
  };
}
