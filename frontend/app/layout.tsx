import type { Metadata } from "next";
import "./globals.css";
import { ClientProviders } from "./providers";

export const metadata: Metadata = {
  title: "Reddit Idea Miner",
  description: "Find recurring Reddit complaints in any niche and rank business ideas grounded in real posts.",
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
