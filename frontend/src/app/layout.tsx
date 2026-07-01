import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HDFC Mutual Fund Assistant | FundFacts",
  description:
    "Factual answers about HDFC Mutual Fund schemes — NAV, returns, expense ratios, holdings, and more. Powered by RAG + Groq LPU.",
  keywords: "HDFC, mutual fund, chatbot, RAG, Groq, NAV, expense ratio, returns",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
