import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tech Support Voice Agent | LiveKit Real-Time Assistant",
  description: "Real-time technical support voice agent powered by LiveKit Agents, Deepgram STT, Gemini Flash with Groq fallback, and Fish Audio TTS.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="ambient-glow-1" />
        <div className="ambient-glow-2" />
        {children}
      </body>
    </html>
  );
}
