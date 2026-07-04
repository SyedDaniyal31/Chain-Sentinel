import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import {
  centralizationLevelColor,
  centralizationLevelLabel,
  confidenceLevelColor,
  confidenceLevelLabel,
  formatRiskScore,
  riskLevelColor,
  riskLevelLabel,
  threatLevelColor,
  threatLevelLabel,
} from "@/lib/format";
import type { CentralizationLevel, ConfidenceLevel, RiskLevel, ThreatLevel } from "@/types/scan";

interface RiskScoreGaugeProps {
  score: string | null | undefined;
  level: RiskLevel | null | undefined;
  threatLevel?: ThreatLevel | null;
  centralizationLevel?: CentralizationLevel | null;
  confidenceLevel?: ConfidenceLevel | null;
}

function gaugeColor(score: number): string {
  if (score <= 33) {
    return "from-risk-low to-emerald-400";
  }
  if (score <= 66) {
    return "from-risk-medium to-amber-400";
  }
  return "from-risk-high to-red-500";
}

interface DimensionBadgeProps {
  label: string;
  value: string;
  className: string;
}

function DimensionBadge({ label, value, className }: DimensionBadgeProps) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-surface-elevated/60 p-4">
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
      <Badge className={className}>{value}</Badge>
    </div>
  );
}

export function RiskScoreGauge({
  score,
  level,
  threatLevel,
  centralizationLevel,
  confidenceLevel,
}: RiskScoreGaugeProps) {
  const numericScore = formatRiskScore(score);
  const clamped = Math.min(Math.max(numericScore, 0), 100);
  const showDimensions = threatLevel || centralizationLevel || confidenceLevel;

  return (
    <Card
      title="Risk intelligence"
      description="Composite score plus Risk Engine V2 threat, centralization, and confidence dimensions"
    >
      <div className="flex flex-col gap-8">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="text-center sm:text-left">
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Risk score
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-6xl font-bold tabular-nums tracking-tight text-foreground">
                {numericScore.toFixed(0)}
              </span>
              <span className="text-2xl text-muted-foreground">/100</span>
            </div>
            {level ? (
              <Badge className={`mt-3 ${riskLevelColor(level)}`}>{riskLevelLabel(level)}</Badge>
            ) : null}
          </div>

          <div className="w-full max-w-md flex-1">
            <div className="mb-2 flex justify-between text-xs text-muted-foreground">
              <span>Low</span>
              <span>Medium</span>
              <span>High</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-surface-elevated">
              <div
                className={`h-full rounded-full bg-gradient-to-r transition-all duration-700 ${gaugeColor(clamped)}`}
                style={{ width: `${clamped}%` }}
                role="progressbar"
                aria-valuenow={clamped}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Risk score"
              />
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
              V1 score combines governance, capabilities, honeypot heuristics, and trade simulation. V2
              dimensions below decompose threat mechanics, authority concentration, and evidence quality.
            </p>
          </div>
        </div>

        {showDimensions ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {threatLevel ? (
              <DimensionBadge
                label="Threat level"
                value={threatLevelLabel(threatLevel)}
                className={threatLevelColor(threatLevel)}
              />
            ) : null}
            {centralizationLevel ? (
              <DimensionBadge
                label="Centralization"
                value={centralizationLevelLabel(centralizationLevel)}
                className={centralizationLevelColor(centralizationLevel)}
              />
            ) : null}
            {confidenceLevel ? (
              <DimensionBadge
                label="Confidence"
                value={confidenceLevelLabel(confidenceLevel)}
                className={confidenceLevelColor(confidenceLevel)}
              />
            ) : null}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
