import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { truncateAddress } from "@/lib/format";
import type { CapabilityDetail, ScanResult } from "@/types/scan";

interface CapabilityIntelligencePanelProps {
  result: ScanResult;
}

const CAPABILITY_LABELS: Record<string, string> = {
  mint: "Mint",
  burn: "Burn",
  pause: "Pause",
  blacklist: "Blacklist",
  whitelist: "Whitelist",
  freeze: "Freeze",
  seize: "Seize",
  trading_gate: "Trading Gate",
  max_wallet: "Max Wallet",
  max_transaction: "Max Transaction",
  cooldown: "Cooldown",
  anti_bot: "Anti-Bot",
  buy_tax: "Buy Tax",
  sell_tax: "Sell Tax",
  dynamic_tax: "Dynamic Tax",
  treasury_fee: "Treasury Fee",
  fee_exemption: "Fee Exemption",
  transfer_ownership: "Transfer Ownership",
  renounce_ownership: "Renounce Ownership",
  grant_role: "Grant Role",
  revoke_role: "Revoke Role",
};

function severityVariant(severity: CapabilityDetail["severity"]) {
  switch (severity) {
    case "critical":
      return "danger" as const;
    case "high":
      return "danger" as const;
    case "medium":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

function confidenceVariant(confidence: CapabilityDetail["confidence"]) {
  switch (confidence) {
    case "high":
      return "success" as const;
    case "medium":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

function controllerLabel(controller: string | null | undefined) {
  if (!controller) {
    return "—";
  }
  if (controller.startsWith("0x")) {
    return truncateAddress(controller);
  }
  return controller;
}

function resolveCapabilities(result: ScanResult): Record<string, CapabilityDetail> {
  if (result.capabilities && Object.keys(result.capabilities).length > 0) {
    return result.capabilities;
  }
  if (result.capabilities_detail) {
    return result.capabilities_detail;
  }
  return {};
}

export function CapabilityIntelligencePanel({ result }: CapabilityIntelligencePanelProps) {
  const capabilities = resolveCapabilities(result);
  const enabledEntries = Object.entries(capabilities).filter(([, detail]) => detail.enabled);
  const enabledCount = result.capability_count ?? enabledEntries.length;

  return (
    <Card
      title="Capability intelligence"
      description={`M3 dangerous powers and controllers (${enabledCount} active)`}
    >
      {enabledEntries.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No dangerous capabilities detected in logic contract analysis.
        </p>
      ) : (
        <div className="space-y-3">
          {enabledEntries.map(([key, detail]) => (
            <div
              key={key}
              className="rounded-lg border border-border bg-surface-elevated/60 p-4"
            >
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-foreground">
                  {CAPABILITY_LABELS[key] ?? key}
                </h3>
                <Badge variant="danger">Enabled</Badge>
              </div>
              <dl className="grid gap-2 text-xs sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">Controller</dt>
                  <dd className="font-mono text-foreground">{controllerLabel(detail.controller)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Detection</dt>
                  <dd className="text-foreground">{detail.detection_method}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Severity</dt>
                  <dd>
                    <Badge variant={severityVariant(detail.severity)}>{detail.severity}</Badge>
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Confidence</dt>
                  <dd>
                    <Badge variant={confidenceVariant(detail.confidence)}>{detail.confidence}</Badge>
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 border-t border-border/60 pt-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Full capability matrix
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-xs">
            <thead>
              <tr className="border-b border-border/60 text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Capability</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="py-2 pr-3 font-medium">Controller</th>
                <th className="py-2 pr-3 font-medium">Severity</th>
                <th className="py-2 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(capabilities).map(([key, detail]) => (
                <tr key={key} className="border-b border-border/40">
                  <td className="py-2 pr-3 font-medium text-foreground">
                    {CAPABILITY_LABELS[key] ?? key}
                  </td>
                  <td className="py-2 pr-3">
                    {detail.enabled ? (
                      <Badge variant="danger">Enabled</Badge>
                    ) : (
                      <Badge variant="success">Clear</Badge>
                    )}
                  </td>
                  <td className="py-2 pr-3 font-mono text-muted-foreground">
                    {controllerLabel(detail.controller)}
                  </td>
                  <td className="py-2 pr-3">
                    <Badge variant={severityVariant(detail.severity)}>{detail.severity}</Badge>
                  </td>
                  <td className="py-2">
                    <Badge variant={confidenceVariant(detail.confidence)}>{detail.confidence}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}
