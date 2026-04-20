interface RequestBudgetProps {
  requestsInWindow: number;
  limit: number;
}

export function RequestBudget({ requestsInWindow, limit }: RequestBudgetProps) {
  const pct = Math.min(100, (requestsInWindow / limit) * 100);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between h-7">
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
          Reddit requests
        </span>
        <span className="text-sm font-mono font-medium text-foreground">
          {requestsInWindow}
          <span className="text-muted-foreground">/{limit}</span>{" "}
          <span className="text-muted-foreground">used</span>
        </span>
      </div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            backgroundImage: "linear-gradient(to right, #f472b6, #ec4899)",
          }}
        />
      </div>
    </div>
  );
}
