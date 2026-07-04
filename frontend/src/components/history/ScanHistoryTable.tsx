"use client";

import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import {
  formatDateTime,
  formatRiskScore,
  formatStatusLabel,
  riskLevelColor,
  riskLevelLabel,
  truncateAddress,
} from "@/lib/format";
import type { ScanListItem, RiskLevel } from "@/types/scan";

interface ScanHistoryTableProps {
  items: ScanListItem[];
}

function statusVariant(status: ScanListItem["status"]) {
  switch (status) {
    case "completed":
      return "success" as const;
    case "failed":
    case "cancelled":
      return "danger" as const;
    case "running":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

function riskBadge(level: RiskLevel | null) {
  if (!level) {
    return <Badge variant="neutral">—</Badge>;
  }
  return <Badge className={riskLevelColor(level)}>{riskLevelLabel(level)}</Badge>;
}

export function ScanHistoryTable({ items }: ScanHistoryTableProps) {
  const router = useRouter();

  if (items.length === 0) {
    return (
      <Card title="Recent scans" description="Paginated scan history sorted newest first">
        <div className="rounded-lg border border-dashed border-border px-6 py-12 text-center">
          <p className="text-lg font-medium text-foreground">No scans yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            Run your first contract analysis from the dashboard to populate scan history.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Recent scans" description="Click a row to open full scan intelligence">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-3 py-3 font-semibold">ID</th>
              <th className="px-3 py-3 font-semibold">Type</th>
              <th className="px-3 py-3 font-semibold">Address</th>
              <th className="px-3 py-3 font-semibold">Risk score</th>
              <th className="px-3 py-3 font-semibold">Risk level</th>
              <th className="px-3 py-3 font-semibold">Status</th>
              <th className="px-3 py-3 font-semibold">Created</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                onClick={() => router.push(`/scan/${item.id}`)}
                className="cursor-pointer border-b border-border/60 transition hover:bg-surface-elevated/70"
              >
                <td className="px-3 py-3 font-mono text-xs">#{item.id}</td>
                <td className="px-3 py-3 capitalize">{item.scan_type}</td>
                <td className="px-3 py-3">
                  <code className="font-mono text-xs" title={item.target_address}>
                    {truncateAddress(item.target_address, 8)}
                  </code>
                </td>
                <td className="px-3 py-3 font-mono tabular-nums">
                  {item.risk_score ? formatRiskScore(item.risk_score).toFixed(0) : "—"}
                </td>
                <td className="px-3 py-3">{riskBadge(item.risk_level)}</td>
                <td className="px-3 py-3">
                  <Badge variant={statusVariant(item.status)}>{formatStatusLabel(item.status)}</Badge>
                </td>
                <td className="px-3 py-3 text-muted-foreground">{formatDateTime(item.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
