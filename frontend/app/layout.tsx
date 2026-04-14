import type { Metadata } from "next";
import "./globals.css";
import { ClientProviders } from "./providers";

export const metadata: Metadata = {
  title: "Reddit Pain Point Analyzer",
  description: "Multi-agent Reddit analysis system for discovering unsolved pain points",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
