import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { formatBpsAsPercent } from "@/lib/format";
import type { ScanResult } from "@/types/scan";

interface HoneypotPanelProps {
  result: ScanResult;
}

interface IndicatorProps {
  label: string;
  description: string;
  active: boolean | null | undefined;
}

function HoneypotIndicator({ label, description, active }: IndicatorProps) {
  return (
    <div className="rounded-lg border border-border bg-surface-elevated p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{label}</h3>
        {active ? (
          <Badge variant="danger">Flagged</Badge>
        ) : (
          <Badge variant="success">Clear</Badge>
        )}
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}

function simulationStatus(value: boolean | null | undefined, positive: string, negative: string) {
  if (value === null || value === undefined) {
    return <Badge variant="neutral">Not tested</Badge>;
  }
  return value ? (
    <Badge variant="success">{positive}</Badge>
  ) : (
    <Badge variant="danger">{negative}</Badge>
  );
}

export function HoneypotPanel({ result }: HoneypotPanelProps) {
  return (
    <Card
      title="Honeypot & trading"
      description="Heuristic trading restrictions and optional Anvil trade simulation"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <HoneypotIndicator
          label="Trading gate"
          description="Admin can enable or disable trading (launch gate scams)."
          active={result.trading_enabled_control}
        />
        <HoneypotIndicator
          label="Whitelist"
          description="Only approved wallets may transfer tokens."
          active={result.whitelist_control}
        />
        <HoneypotIndicator
          label="Sell blocking"
          description="Blacklist combined with sell-limit patterns."
          active={result.blacklist_sell_blocking}
        />
        <HoneypotIndicator
          label="Transfer tax"
          description="Configurable buy/sell fee controls in contract logic."
          active={result.transfer_tax_control}
        />
      </div>

      <div className="mt-5 rounded-lg border border-accent/20 bg-accent/5 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground">Trade simulation (V3)</h3>
          {result.trade_simulated ? (
            <Badge variant="default">Simulated on fork</Badge>
          ) : (
            <Badge variant="neutral">Not run — enable TRADE_SIMULATION_ENABLED on backend</Badge>
          )}
        </div>

        {result.trade_simulated ? (
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Can buy</dt>
              <dd className="mt-1">{simulationStatus(result.can_buy, "Success", "Blocked")}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Can sell</dt>
              <dd className="mt-1">{simulationStatus(result.can_sell, "Success", "Blocked")}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Buy tax</dt>
              <dd className="mt-1 font-mono text-sm">{formatBpsAsPercent(result.buy_tax_bps)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Sell tax</dt>
              <dd className="mt-1 font-mono text-sm">{formatBpsAsPercent(result.sell_tax_bps)}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-xs leading-relaxed text-muted-foreground">
            When enabled, ChainSentinel forks mainnet via Anvil and executes a real buy → transfer → sell
            round-trip to confirm honeypot behavior.
          </p>
        )}
      </div>
    </Card>
  );
}
