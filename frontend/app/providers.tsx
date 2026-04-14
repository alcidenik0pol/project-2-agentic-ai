"use client";

import { AnalysisProvider } from "@/contexts/AnalysisContext";
import { WebSocketProvider } from "@/contexts/WebSocketContext";
import { MainLayout } from "@/components/layout/MainLayout";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <AnalysisProvider>
      <WebSocketProvider>
        <MainLayout>
          {children}
        </MainLayout>
      </WebSocketProvider>
    </AnalysisProvider>
  );
}
