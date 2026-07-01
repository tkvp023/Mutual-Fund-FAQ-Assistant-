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
    chatHistory,
    latestResponse,
    send,
    newChat,
  } = useChat();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  // Auto-open sources when a response arrives
  const handleSend = (query: string) => {
    send(query);
    // Sources panel will open when response arrives
  };

  // Toggle sources panel
  const toggleSources = () => setSourcesOpen((v) => !v);

  return (
    <main className={styles.main}>
      <Sidebar
        chatHistory={chatHistory}
        onNewChat={newChat}
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
