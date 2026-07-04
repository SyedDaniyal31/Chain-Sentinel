import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { formatStatusLabel } from "@/lib/format";
import type { ScanJobStatus } from "@/types/scan";

interface ScanStatusBannerProps {
  status: ScanJobStatus | null;
  scanId: number | null;
  isPolling: boolean;
  pollCount: number;
}

function statusVariant(status: ScanJobStatus): "default" | "success" | "warning" | "danger" | "neutral" {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
    case "cancelled":
      return "danger";
    case "running":
      return "warning";
    default:
      return "neutral";
  }
}

export function ScanStatusBanner({ status, scanId, isPolling, pollCount }: ScanStatusBannerProps) {
  if (!status && !isPolling) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface-elevated px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        {status ? (
          <Badge variant={statusVariant(status)}>{formatStatusLabel(status)}</Badge>
        ) : null}
        {scanId ? <span className="font-mono text-sm text-muted-foreground">Scan #{scanId}</span> : null}
      </div>
      {isPolling ? <Spinner label={`Analyzing on-chain… (poll ${pollCount})`} size="sm" /> : null}
    </div>
  );
}
