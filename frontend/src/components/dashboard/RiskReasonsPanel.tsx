import { Card } from "@/components/ui/Card";

interface RiskReasonsPanelProps {
  reasons: string[] | null | undefined;
}

export function RiskReasonsPanel({ reasons }: RiskReasonsPanelProps) {
  const items = reasons ?? [];

  return (
    <Card title="Risk findings" description="Rule-based reasons that contributed to the score">
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No risk signals recorded for this scan.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((reason, index) => (
            <li
              key={`${index}-${reason.slice(0, 24)}`}
              className="flex gap-3 rounded-lg border border-border/60 bg-surface-elevated px-3 py-2 text-sm text-foreground"
            >
              <span
                className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-semibold text-accent"
                aria-hidden
              >
                {index + 1}
              </span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
