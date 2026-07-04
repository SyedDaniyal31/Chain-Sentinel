import { Card } from "@/components/ui/Card";
import type { ScanSummaryResponse } from "@/types/scan";

interface SummaryCardsProps {
  summary: ScanSummaryResponse;
}

interface MetricCardProps {
  label: string;
  value: string | number;
  hint?: string;
}

function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface/80 p-4 shadow-sm backdrop-blur">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-2 text-3xl font-bold tabular-nums text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  return (
    <Card title="Scan intelligence summary" description="Platform-wide analytics from persisted scan jobs">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total scans" value={summary.total_scans} />
        <MetricCard
          label="Completed"
          value={summary.completed_scans}
          hint={`${summary.failed_scans} failed`}
        />
        <MetricCard label="High risk" value={summary.high_risk} hint="Completed scans in HIGH band" />
        <MetricCard
          label="Average score"
          value={summary.average_risk_score.toFixed(1)}
          hint={`${summary.medium_risk} medium · ${summary.low_risk} low`}
        />
      </div>
    </Card>
  );
}
