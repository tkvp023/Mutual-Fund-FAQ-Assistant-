"use client";

import { useState } from "react";
import { useChat } from "@/hooks/useChat";
import Sidebar from "@/components/Sidebar";
import ChatInterface from "@/components/ChatInterface";
import SourcesPanel from "@/components/SourcesPanel";
import styles from "./page.module.css";

export default function Home() {
  const {
    messages,
    isLoading,
    sessionId,
    chatHistory,
    latestResponse,
    send,
    newChat,
    loadSession,
  } = useChat();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  // Auto-open sources when a response arrives
  const handleSend = (query: string) => {
    send(query);
    // Sources panel will open when response arrives
  };

  // Handle selecting a past session from sidebar
  const handleSelectSession = (id: string) => {
    loadSession(id);
    setSidebarOpen(false); // Close sidebar on mobile
  };

  // Toggle sources panel
  const toggleSources = () => setSourcesOpen((v) => !v);

  return (
    <main className={styles.main}>
      <Sidebar
        chatHistory={chatHistory}
        activeSessionId={sessionId}
        onNewChat={newChat}
        onSelectSession={handleSelectSession}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
      />

      <ChatInterface
        messages={messages}
        isLoading={isLoading}
        latestResponse={latestResponse}
        onSend={handleSend}
        onToggleSources={toggleSources}
        sourcesOpen={sourcesOpen}
      />

      <SourcesPanel
        response={latestResponse}
        isOpen={sourcesOpen}
        onClose={() => setSourcesOpen(false)}
      />
    </main>
  );
}

