import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { ScanResult } from "@/types/scan";

interface CapabilityPanelProps {
  result: ScanResult;
}

interface IndicatorProps {
  label: string;
  description: string;
  active: boolean | null | undefined;
}

function CapabilityIndicator({ label, description, active }: IndicatorProps) {
  return (
    <div className="rounded-lg border border-border bg-surface-elevated p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{label}</h3>
        {active === true ? (
          <Badge variant="danger">Detected</Badge>
        ) : active === false ? (
          <Badge variant="success">Clear</Badge>
        ) : (
          <Badge variant="neutral">—</Badge>
        )}
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}

export function CapabilityPanel({ result }: CapabilityPanelProps) {
  const indicators = [
    {
      label: "Mint",
      description: "Supply inflation — admin can create new tokens.",
      active: result.mint_capability,
    },
    {
      label: "Pause",
      description: "Transfer freeze — all user movement can be halted.",
      active: result.pause_capability,
    },
    {
      label: "Blacklist",
      description: "Selective blocking — specific wallets may be censored.",
      active: result.blacklist_capability,
    },
    {
      label: "Ownership",
      description: "Centralized admin controls via Ownable pattern.",
      active: result.ownership_capability,
    },
  ];

  const activeCount = indicators.filter((item) => item.active).length;

  return (
    <Card
      title="Capabilities"
      description={`Dangerous contract surfaces detected in logic (${activeCount}/4 active)`}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {indicators.map((indicator) => (
          <CapabilityIndicator key={indicator.label} {...indicator} />
        ))}
      </div>
    </Card>
  );
}
