import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { formatSeconds, truncateAddress } from "@/lib/format";
import type { GovernanceIntelligence, ScanResult } from "@/types/scan";

interface GovernanceIntelligencePanelProps {
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

function labelize(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
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

function governanceBadge(value: string | null | undefined, variant: "default" | "success" | "warning" | "danger" = "default") {
  if (!value || value === "none" || value === "unknown") {
    return <Badge variant="neutral">{labelize(value ?? "none")}</Badge>;
  }
  if (value === "timelock" || value === "multisig") {
    return <Badge variant="success">{labelize(value)}</Badge>;
  }
  if (value === "eoa" || value === "access_control") {
    return <Badge variant="warning">{labelize(value)}</Badge>;
  }
  return <Badge variant={variant}>{labelize(value)}</Badge>;
}

function resolveGovernance(result: ScanResult): GovernanceIntelligence {
  if (result.governance) {
    return result.governance;
  }
  return {
    governance_type: result.governance_type ?? "none",
    upgrade_authority: result.upgrade_authority ?? "none",
    has_timelock: Boolean(result.is_timelock),
    role_count: result.role_count ?? 0,
    roles: result.governance_roles ?? [],
    ownership_address: result.governance_ownership_address,
    ownership_renounced: result.governance?.ownership_renounced,
    source_confidence: result.governance?.source_confidence,
  };
}

export function GovernanceIntelligencePanel({ result }: GovernanceIntelligencePanelProps) {
  const governance = resolveGovernance(result);
  const ownership =
    governance.ownership_address ?? result.governance_ownership_address ?? result.owner_address;

  return (
    <Card
      title="Governance intelligence"
      description="M2 ownership tracing, upgrade authority, AccessControl roles, and timelock status"
    >
      <dl>
        <DataRow
          label="Governance pattern"
          value={governanceBadge(governance.governance_type)}
        />
        <DataRow label="Ownership" value={addressValue(ownership)} />
        {governance.ownership_renounced ? (
          <DataRow
            label="Ownership status"
            value={<Badge variant="success">Renounced</Badge>}
          />
        ) : null}
        {governance.source_confidence ? (
          <DataRow
            label="Source confidence"
            value={governanceBadge(governance.source_confidence, "success")}
          />
        ) : null}
        <DataRow
          label="Upgrade authority"
          value={governanceBadge(governance.upgrade_authority, "warning")}
        />
        <DataRow
          label="Timelock status"
          value={
            governance.has_timelock ? (
              <Badge variant="success">
                Protected · min delay {formatSeconds(result.min_delay)}
              </Badge>
            ) : (
              <Badge variant="neutral">No timelock detected</Badge>
            )
          }
        />
        <DataRow
          label="Role count"
          value={
            governance.role_count > 0 ? (
              <Badge variant="default">{governance.role_count} roles</Badge>
            ) : (
              <span className="text-muted-foreground">No AccessControl roles</span>
            )
          }
        />
      </dl>

      {governance.roles.length > 0 ? (
        <div className="mt-4 border-t border-border/60 pt-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Roles
          </h3>
          <ul className="space-y-2">
            {governance.roles.map((role) => (
              <li
                key={role.role_id}
                className="rounded-lg border border-border/60 bg-surface-elevated/50 px-3 py-2 text-xs"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="default">{role.name}</Badge>
                  {role.is_default_admin ? <Badge variant="success">Default admin</Badge> : null}
                </div>
                <p className="mt-1 font-mono text-muted-foreground">{role.role_id}</p>
                {role.admin_role_name ? (
                  <p className="mt-1 text-muted-foreground">
                    Admin role: <span className="text-foreground">{role.admin_role_name}</span>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Card>
  );
}
