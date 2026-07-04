"use client";

import { useCallback, useState } from "react";

import { CapabilityIntelligencePanel } from "@/components/dashboard/CapabilityIntelligencePanel";
import { CapabilityPanel } from "@/components/dashboard/CapabilityPanel";
import { ErrorAlert } from "@/components/dashboard/ErrorAlert";
import { GovernanceIntelligencePanel } from "@/components/dashboard/GovernanceIntelligencePanel";
import { GovernancePanel } from "@/components/dashboard/GovernancePanel";
import { HoneypotIntelligencePanel } from "@/components/dashboard/HoneypotIntelligencePanel";
import { HoneypotPanel } from "@/components/dashboard/HoneypotPanel";
import { LoadingSkeleton } from "@/components/dashboard/LoadingSkeleton";
import { RiskReasonsPanel } from "@/components/dashboard/RiskReasonsPanel";
import { RiskScoreGauge } from "@/components/dashboard/RiskScoreGauge";
import { ScanForm } from "@/components/dashboard/ScanForm";
import { ScanStatusBanner } from "@/components/dashboard/ScanStatusBanner";
import { AppHeader } from "@/components/layout/AppHeader";
import { useScanPolling } from "@/hooks/useScanPolling";
import { createScan } from "@/lib/api";
import { truncateAddress } from "@/lib/format";
import { ApiError } from "@/types/scan";

export function Dashboard() {
  const { scan, isPolling, error: pollError, pollCount, startPolling, reset } = useScanPolling();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [activeScanId, setActiveScanId] = useState<number | null>(null);

  const handleScanSubmit = useCallback(
    async (address: string) => {
      setIsSubmitting(true);
      setSubmitError(null);
      reset();

      try {
        const created = await createScan({
          scan_type: "contract",
          target_address: address,
        });
        setActiveScanId(created.id);
        startPolling(created.id);
      } catch (err) {
        if (err instanceof ApiError) {
          setSubmitError(err.message);
        } else {
          setSubmitError(
            "Unable to reach ChainSentinel API. Ensure the backend is running and NEXT_PUBLIC_API_URL is set.",
          );
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [reset, startPolling],
  );

  const displayError = submitError ?? pollError;
  const result = scan?.result;
  const showResults = scan?.status === "completed" && result;
  const showLoading = isPolling || isSubmitting || (scan && !showResults && scan.status !== "failed");

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <AppHeader active="dashboard" />

      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-4">
          <section className="rounded-xl border border-border bg-surface/80 p-5 shadow-sm backdrop-blur">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted">New scan</h2>
            <ScanForm
              onSubmit={handleScanSubmit}
              isSubmitting={isSubmitting}
              disabled={isPolling}
            />
          </section>

          {scan ? (
            <section className="rounded-xl border border-border bg-surface/80 p-5 text-sm">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">Target</h2>
              <code className="block break-all font-mono text-xs text-foreground">{scan.target_address}</code>
              <p className="mt-2 text-xs text-muted-foreground">
                {truncateAddress(scan.target_address)} · chain analysis at block{" "}
                {result?.latest_block ?? "…"}
              </p>
            </section>
          ) : null}
        </aside>

        <main className="space-y-4">
          {displayError ? (
            <ErrorAlert
              message={displayError}
              onDismiss={() => {
                setSubmitError(null);
              }}
            />
          ) : null}

          <ScanStatusBanner
            status={scan?.status ?? null}
            scanId={activeScanId}
            isPolling={isPolling}
            pollCount={pollCount}
          />

          {showLoading && !showResults ? <LoadingSkeleton /> : null}

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
              <RiskReasonsPanel reasons={result.risk_reasons} />
            </div>
          ) : null}

          {!scan && !isSubmitting && !displayError ? (
            <section className="rounded-xl border border-dashed border-border bg-surface/40 px-6 py-16 text-center">
              <p className="text-lg font-medium text-foreground">No scan results yet</p>
              <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
                Submit a contract address to run ChainSentinel&apos;s full analysis pipeline — proxy detection,
                admin tracing, capability scanning, honeypot heuristics, and optional trade simulation.
              </p>
            </section>
          ) : null}
        </main>
      </div>
    </div>
  );
}
