import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type {
  HoneypotFinding,
  HoneypotIntelligence,
  HoneypotSeverity,
  HoneypotTradePathResult,
  ScanResult,
} from "@/types/scan";

interface HoneypotIntelligencePanelProps {
  result: ScanResult;
}

const FINDING_LABELS: Record<string, string> = {
  trading_gate: "Trading gate",
  whitelist_restriction: "Whitelist restriction",
  blacklist_probe: "Blacklist probe",
  sell_restriction: "Sell restriction",
  transfer_tax_control: "Transfer tax control",
  modifiable_tax: "Modifiable tax",
  anti_bot_pattern: "Anti-bot pattern",
  high_buy_tax: "High buy tax",
  high_sell_tax: "High sell tax",
  buy_path_blocked: "Buy path blocked",
  sell_path_blocked: "Sell path blocked",
  transfer_path_blocked: "Transfer path blocked",
  honeypot_confirmed: "Honeypot confirmed",
};

function severityVariant(severity: HoneypotSeverity) {
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

function confidenceVariant(confidence: HoneypotFinding["confidence"]) {
  switch (confidence) {
    case "high":
      return "success" as const;
    case "medium":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

function simulationStatusLabel(status: string) {
  switch (status) {
    case "completed":
      return "Completed";
    case "skipped":
      return "Skipped";
    case "pending":
      return "Pending";
    case "failed":
      return "Failed";
    default:
      return "Not run";
  }
}

function pathPhaseClass(path: HoneypotTradePathResult, simulationStatus: string) {
  if (!path.attempted) {
    return "border-border/60 bg-muted/20 text-muted-foreground";
  }
  if (path.success) {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-400";
  }
  return "border-red-500/40 bg-red-500/10 text-red-400";
}

function pathPhaseLabel(path: HoneypotTradePathResult, simulationStatus: string) {
  if (!path.attempted) {
    return simulationStatus === "not_run" ? "Not run" : "Skipped";
  }
  if (path.success) {
    return "Success";
  }
  return path.revert_reason ?? "Failed";
}

function resolveHoneypotIntelligence(result: ScanResult): HoneypotIntelligence {
  if (result.honeypot) {
    return result.honeypot;
  }

  return {
    summary: {
      finding_count: result.honeypot_finding_count ?? 0,
      critical_count: 0,
      honeypot_score: result.honeypot_score ?? 0,
      honeypot_risk: result.honeypot_risk ?? "low",
      is_suspected: Boolean(result.honeypot_is_suspected),
      is_confirmed: Boolean(result.honeypot_is_confirmed),
    },
    findings: result.honeypot_findings ?? [],
    simulation: result.honeypot_simulation ?? {
      status: result.honeypot_simulation_status ?? "not_run",
      fork_block: null,
      pair_address: null,
      router_address: null,
      buy: { attempted: false, success: null, tax_bps: null, revert_reason: null, gas_used: null },
      transfer: { attempted: false, success: null, tax_bps: null, revert_reason: null, gas_used: null },
      sell: { attempted: false, success: null, tax_bps: null, revert_reason: null, gas_used: null },
      round_trip_success: null,
    },
  };
}

export function HoneypotIntelligencePanel({ result }: HoneypotIntelligencePanelProps) {
  const intelligence = resolveHoneypotIntelligence(result);
  const { summary, findings, simulation } = intelligence;
  const activeFindings = findings.filter((finding) => finding.enabled);
  const simActive = simulation.status === "completed" || simulation.status === "skipped";

  return (
    <Card
      title="Honeypot intelligence"
      description={`Exit-path analysis · ${summary.finding_count} findings · Simulation: ${simulationStatusLabel(simulation.status).toUpperCase()}`}
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge variant={severityVariant(summary.honeypot_risk)}>
          Score {summary.honeypot_score}/100 · {summary.honeypot_risk}
        </Badge>
        <Badge variant={summary.is_suspected ? "warning" : "success"}>
          Suspected {summary.is_suspected ? "yes" : "no"}
        </Badge>
        <Badge variant={summary.is_confirmed ? "danger" : "neutral"}>
          Confirmed {summary.is_confirmed ? "yes" : "no"}
        </Badge>
        <Badge variant="neutral">Sim: {simulationStatusLabel(simulation.status)}</Badge>
      </div>

      <div className="mb-5">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Active findings
        </h3>
        {activeFindings.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No active honeypot findings detected in logic contract analysis.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {activeFindings.map((finding) => (
              <div
                key={finding.finding_type}
                className="rounded-lg border border-border bg-surface-elevated/60 p-4"
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-sm font-semibold text-foreground">
                    {FINDING_LABELS[finding.finding_type] ?? finding.finding_type}
                  </h4>
                  <Badge variant={severityVariant(finding.severity)}>{finding.severity}</Badge>
                </div>
                <p className="mb-2 text-xs text-muted-foreground">{finding.description}</p>
                <dl className="grid gap-1 text-xs sm:grid-cols-2">
                  <div>
                    <dt className="text-muted-foreground">Confidence</dt>
                    <dd>
                      <Badge variant={confidenceVariant(finding.confidence)}>{finding.confidence}</Badge>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Detection</dt>
                    <dd className="text-foreground">{finding.detection_method}</dd>
                  </div>
                </dl>
                {finding.evidence.length > 0 ? (
                  <ul className="mt-2 space-y-1 font-mono text-[11px] text-muted-foreground">
                    {finding.evidence.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mb-5 rounded-lg border border-border/60 bg-surface-elevated/40 p-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Trade path simulation
        </h3>
        <div className="relative grid gap-3 sm:grid-cols-3">
          {(["buy", "transfer", "sell"] as const).map((phase, index) => {
            const path = simulation[phase];
            return (
              <div key={phase} className="relative">
                {index > 0 ? (
                  <span
                    aria-hidden
                    className="absolute -left-3 top-1/2 hidden h-px w-3 -translate-y-1/2 bg-border sm:block"
                  />
                ) : null}
                <div className={`rounded-md border p-3 text-center ${pathPhaseClass(path, simulation.status)}`}>
                  <p className="text-xs font-semibold uppercase tracking-wider">{phase}</p>
                  <p className="mt-2 text-sm font-medium">{pathPhaseLabel(path, simulation.status)}</p>
                  {path.tax_bps != null ? (
                    <p className="mt-1 font-mono text-[11px] opacity-80">tax {path.tax_bps} bps</p>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
        {!simActive ? (
          <p className="mt-3 text-xs text-muted-foreground">
            Enable TRADE_SIMULATION_ENABLED on the backend to fork mainnet and run buy → transfer → sell.
          </p>
        ) : simulation.round_trip_success === false ? (
          <p className="mt-3 text-xs text-red-400/90">
            Round-trip failed — exit path may be restricted (confirmed honeypot when sell is blocked).
          </p>
        ) : simulation.round_trip_success ? (
          <p className="mt-3 text-xs text-emerald-400/90">Round-trip completed successfully on fork.</p>
        ) : null}
      </div>

      <div className="border-t border-border/60 pt-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Full findings table
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead>
              <tr className="border-b border-border/60 text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Type</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="py-2 pr-3 font-medium">Severity</th>
                <th className="py-2 pr-3 font-medium">Confidence</th>
                <th className="py-2 pr-3 font-medium">Method</th>
                <th className="py-2 font-medium">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((finding) => (
                <tr key={finding.finding_type} className="border-b border-border/40">
                  <td className="py-2 pr-3 font-medium text-foreground">
                    {FINDING_LABELS[finding.finding_type] ?? finding.finding_type}
                  </td>
                  <td className="py-2 pr-3">
                    {finding.enabled ? (
                      <Badge variant="danger">Active</Badge>
                    ) : (
                      <Badge variant="success">Clear</Badge>
                    )}
                  </td>
                  <td className="py-2 pr-3">
                    <Badge variant={severityVariant(finding.severity)}>{finding.severity}</Badge>
                  </td>
                  <td className="py-2 pr-3">
                    <Badge variant={confidenceVariant(finding.confidence)}>{finding.confidence}</Badge>
                  </td>
                  <td className="py-2 pr-3 text-muted-foreground">{finding.detection_method}</td>
                  <td className="py-2 font-mono text-[11px] text-muted-foreground">
                    {finding.evidence.length > 0 ? finding.evidence.join(", ") : "—"}
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
