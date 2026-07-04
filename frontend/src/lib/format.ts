import type {
  CentralizationLevel,
  ConfidenceLevel,
  RiskLevel,
  ThreatLevel,
} from "@/types/scan";

export function truncateAddress(address: string, chars = 6): string {
  if (address.length <= 2 + chars * 2) {
    return address;
  }
  return `${address.slice(0, chars + 2)}…${address.slice(-chars)}`;
}

export function formatRiskScore(score: string | null | undefined): number {
  if (!score) {
    return 0;
  }
  const parsed = Number.parseFloat(score);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatBpsAsPercent(bps: number | null | undefined): string {
  if (bps === null || bps === undefined) {
    return "—";
  }
  return `${(bps / 100).toFixed(2)}%`;
}

export function formatSeconds(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) {
    return "—";
  }
  if (seconds >= 86400) {
    return `${Math.round(seconds / 86400)}d`;
  }
  if (seconds >= 3600) {
    return `${Math.round(seconds / 3600)}h`;
  }
  return `${seconds}s`;
}

export function riskLevelLabel(level: RiskLevel | null | undefined): string {
  switch (level) {
    case "high":
      return "High Risk";
    case "medium":
      return "Medium Risk";
    case "low":
      return "Low Risk";
    default:
      return "Unknown";
  }
}

export function riskLevelColor(level: RiskLevel | null | undefined): string {
  switch (level) {
    case "high":
      return "text-risk-high border-risk-high/40 bg-risk-high/10";
    case "medium":
      return "text-risk-medium border-risk-medium/40 bg-risk-medium/10";
    case "low":
      return "text-risk-low border-risk-low/40 bg-risk-low/10";
    default:
      return "text-muted border-border bg-surface-elevated";
  }
}

type SeverityLevel = RiskLevel | ThreatLevel | CentralizationLevel | ConfidenceLevel;

function severityLabel(level: SeverityLevel | null | undefined, prefix: string): string {
  if (!level) {
    return "Unknown";
  }
  return `${prefix} · ${level.charAt(0).toUpperCase()}${level.slice(1)}`;
}

function severityColor(level: SeverityLevel | null | undefined): string {
  switch (level) {
    case "critical":
      return "text-risk-critical border-risk-critical/40 bg-risk-critical/10";
    case "high":
      return "text-risk-high border-risk-high/40 bg-risk-high/10";
    case "medium":
      return "text-risk-medium border-risk-medium/40 bg-risk-medium/10";
    case "low":
      return "text-risk-low border-risk-low/40 bg-risk-low/10";
    default:
      return "text-muted border-border bg-surface-elevated";
  }
}

export function threatLevelLabel(level: ThreatLevel | null | undefined): string {
  return severityLabel(level, "Threat");
}

export function centralizationLevelLabel(level: CentralizationLevel | null | undefined): string {
  return severityLabel(level, "Centralization");
}

export function confidenceLevelLabel(level: ConfidenceLevel | null | undefined): string {
  return severityLabel(level, "Confidence");
}

export function threatLevelColor(level: ThreatLevel | null | undefined): string {
  return severityColor(level);
}

export function centralizationLevelColor(level: CentralizationLevel | null | undefined): string {
  return severityColor(level);
}

export function confidenceLevelColor(level: ConfidenceLevel | null | undefined): string {
  return severityColor(level);
}

export function formatStatusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
