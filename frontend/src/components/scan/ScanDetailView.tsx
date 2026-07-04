"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { CapabilityIntelligencePanel } from "@/components/dashboard/CapabilityIntelligencePanel";
import { CapabilityPanel } from "@/components/dashboard/CapabilityPanel";
import { ErrorAlert } from "@/components/dashboard/ErrorAlert";
import { GovernanceIntelligencePanel } from "@/components/dashboard/GovernanceIntelligencePanel";
import { GovernancePanel } from "@/components/dashboard/GovernancePanel";
import { HoneypotIntelligencePanel } from "@/components/dashboard/HoneypotIntelligencePanel";
import { HoneypotPanel } from "@/components/dashboard/HoneypotPanel";
import { LiquidityIntelligencePanel } from "@/components/dashboard/LiquidityIntelligencePanel";
import { ProtocolIntelligencePanel } from "@/components/dashboard/ProtocolIntelligencePanel";
import { LoadingSkeleton } from "@/components/dashboard/LoadingSkeleton";
import { RiskReasonsPanel } from "@/components/dashboard/RiskReasonsPanel";
import { RiskScoreGauge } from "@/components/dashboard/RiskScoreGauge";
import { WalletIntelligencePanel } from "@/components/dashboard/WalletIntelligencePanel";
import { AppHeader } from "@/components/layout/AppHeader";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { getScan } from "@/lib/api";
import { truncateAddress } from "@/lib/format";
import type { ScanJob } from "@/types/scan";
import { ApiError } from "@/types/scan";

interface ScanDetailViewProps {
  scanId: number;
}

export function ScanDetailView({ scanId }: ScanDetailViewProps) {
  const [scan, setScan] = useState<ScanJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const job = await getScan(scanId);
        if (!cancelled) {
          setScan(job);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else {
            setError("Unable to load scan details.");
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [scanId]);

  const result = scan?.result;
  const showResults = scan?.status === "completed" && result;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <AppHeader active="history" />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-foreground">Scan #{scanId}</h2>
          {scan ? (
            <p className="mt-1 font-mono text-sm text-muted-foreground">
              {truncateAddress(scan.target_address, 10)} · {scan.scan_type}
            </p>
          ) : null}
        </div>
        <Link
          href="/history"
          className="rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm font-medium text-foreground transition hover:bg-surface"
        >
          ← Back to history
        </Link>
      </div>

      {error ? <ErrorAlert message={error} /> : null}

      {isLoading ? (
        <div className="space-y-4">
          <div className="flex justify-center py-8">
            <Spinner label="Loading scan details…" />
          </div>
          <LoadingSkeleton />
        </div>
      ) : null}

      {!isLoading && scan ? (
        <div className="space-y-4">
          <ScanStatusBanner
            status={scan.status}
            scanId={scan.id}
            isPolling={false}
            pollCount={0}
          />

          {scan.status === "failed" ? (
            <ErrorAlert title="Scan failed" message="This scan job did not complete successfully." />
          ) : null}

          {showResults ? (
            <div className="space-y-6">
              <RiskScoreGauge
                score={scan.risk_score ?? result.risk_score}
                level={result.risk_level}
                threatLevel={result.threat_level}
                centralizationLevel={result.centralization_level}
                confidenceLevel={result.confidence_level}
              />
              <div className="grid gap-6 lg:grid-cols-2">
                <GovernanceIntelligencePanel result={result} />
                <GovernancePanel result={result} />
              </div>
              <CapabilityIntelligencePanel result={result} />
              <CapabilityPanel result={result} />
              <HoneypotIntelligencePanel result={result} />
              <HoneypotPanel result={result} />
              <LiquidityIntelligencePanel result={result} />
              <WalletIntelligencePanel result={result} />
              <ProtocolIntelligencePanel result={result} />
              <RiskReasonsPanel reasons={result.risk_reasons} />
            </div>
          ) : scan.status !== "failed" ? (
            <div className="rounded-xl border border-border bg-surface/80 px-6 py-10 text-center">
              <Badge variant="warning">Analysis incomplete</Badge>
              <p className="mt-3 text-sm text-muted-foreground">
                This scan has not finished processing yet. Refresh later or return to history.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
