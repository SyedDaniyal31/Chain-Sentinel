import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { formatSeconds, truncateAddress } from "@/lib/format";
import type { ScanResult } from "@/types/scan";

interface GovernancePanelProps {
  result: ScanResult;
}

interface DataRowProps {
  label: string;
  value: ReactNode;
}

function DataRow({ label, value }: DataRowProps) {
  return (
    <div className="flex flex-col gap-1 border-b border-border/60 py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium text-foreground">{value}</dd>
    </div>
  );
}

function boolBadge(value: boolean | null | undefined, positiveLabel = "Yes", negativeLabel = "No") {
  if (value === null || value === undefined) {
    return <Badge variant="neutral">—</Badge>;
  }
  return value ? (
    <Badge variant="warning">{positiveLabel}</Badge>
  ) : (
    <Badge variant="success">{negativeLabel}</Badge>
  );
}

function addressValue(address: string | null | undefined) {
  if (!address) {
    return <span className="text-muted-foreground">Not detected</span>;
  }
  return (
    <code className="rounded bg-surface-elevated px-2 py-1 font-mono text-xs" title={address}>
      {truncateAddress(address)}
    </code>
  );
}

export function GovernancePanel({ result }: GovernancePanelProps) {
  return (
    <Card
      title="Governance"
      description="Upgrade authority, proxy patterns, and admin wallet classification"
    >
      <dl>
        <DataRow label="Contract bytecode" value={boolBadge(result.is_contract, "Present", "Empty")} />
        <DataRow
          label="Upgradeable proxy"
          value={boolBadge(result.is_upgradeable, "EIP-1967 proxy", "Not upgradeable")}
        />
        <DataRow label="Implementation" value={addressValue(result.implementation_address)} />
        <DataRow label="Admin address" value={addressValue(result.admin_address)} />
        <DataRow
          label="Admin type"
          value={
            result.admin_type ? (
              <Badge variant="default">{result.admin_type.toUpperCase()}</Badge>
            ) : (
              "—"
            )
          }
        />
        <DataRow label="Traced owner" value={addressValue(result.owner_address)} />
        <DataRow
          label="Owner type"
          value={
            result.owner_type ? (
              <Badge variant="default">{result.owner_type.toUpperCase()}</Badge>
            ) : (
              "—"
            )
          }
        />
        <DataRow
          label="Timelock governed"
          value={
            result.is_timelock ? (
              <Badge variant="success">
                Yes · min delay {formatSeconds(result.min_delay)}
              </Badge>
            ) : (
              boolBadge(false, "Yes", "No")
            )
          }
        />
      </dl>
    </Card>
  );
}
