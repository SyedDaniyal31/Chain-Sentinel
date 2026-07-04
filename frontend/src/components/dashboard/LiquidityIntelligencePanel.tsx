import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { truncateAddress } from "@/lib/format";
import type { LiquidityIntelligence, LiquidityPool, ScanResult } from "@/types/scan";

interface LiquidityIntelligencePanelProps {
  result: ScanResult;
}

function formatUsd(value: string | null | undefined) {
  if (!value) {
    return "$0.00";
  }
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return value;
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

function lockVariant(locked: boolean) {
  return locked ? ("success" as const) : ("danger" as const);
}

function resolveLiquidityIntelligence(result: ScanResult): LiquidityIntelligence {
  if (result.liquidity) {
    return result.liquidity;
  }

  return {
    has_liquidity: Boolean(result.liquidity_has_liquidity),
    liquidity_usd: result.liquidity_usd ?? "0.00",
    primary_dex: result.liquidity_primary_dex,
    pair_address: result.liquidity_pair_address,
    lp_owner: result.liquidity_lp_owner,
    liquidity_locked: Boolean(result.liquidity_locked),
    liquidity_lock_percentage: result.liquidity_lock_percentage ?? "0.00",
    lock_expiry: result.liquidity_lock_expiry,
    top_pools: result.liquidity_top_pools ?? [],
  };
}

function PoolRow({ pool }: { pool: LiquidityPool }) {
  return (
    <div className="rounded-lg border border-border/70 bg-muted/10 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium capitalize text-foreground">{pool.dex}</p>
          <p className="font-mono text-xs text-muted-foreground">
            {truncateAddress(pool.pair_address)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-foreground">{formatUsd(pool.liquidity_usd)}</p>
          <p className="text-xs text-muted-foreground">
            {pool.liquidity_native.toFixed(2)} native (2-sided est.)
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Badge variant={lockVariant(pool.liquidity_locked)}>
          {pool.liquidity_locked ? "Locked" : "Unlocked"} · {pool.liquidity_lock_percentage}%
        </Badge>
        {pool.lp_owner ? (
          <Badge variant="neutral">LP holder {truncateAddress(pool.lp_owner)}</Badge>
        ) : null}
      </div>
    </div>
  );
}

export function LiquidityIntelligencePanel({ result }: LiquidityIntelligencePanelProps) {
  const liquidity = resolveLiquidityIntelligence(result);

  return (
    <Card className="border-border/80 bg-surface/80">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border/70 px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-foreground">Liquidity Intelligence</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            DEX pair discovery, depth estimate, and LP lock posture (M5.1).
          </p>
        </div>
        <Badge variant={liquidity.has_liquidity ? "success" : "danger"}>
          {liquidity.has_liquidity ? "Liquidity found" : "No liquidity"}
        </Badge>
      </div>

      <div className="grid gap-4 px-6 py-5 lg:grid-cols-2">
        <div className="space-y-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Primary pool</p>
            <p className="mt-1 text-lg font-semibold text-foreground">
              {liquidity.primary_dex ? liquidity.primary_dex.toUpperCase() : "—"}
            </p>
            <p className="font-mono text-xs text-muted-foreground">
              {liquidity.pair_address ? truncateAddress(liquidity.pair_address) : "No pair discovered"}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border/70 bg-muted/10 p-3">
              <p className="text-xs text-muted-foreground">Estimated depth</p>
              <p className="mt-1 text-sm font-semibold text-foreground">
                {formatUsd(liquidity.liquidity_usd)}
              </p>
            </div>
            <div className="rounded-lg border border-border/70 bg-muted/10 p-3">
              <p className="text-xs text-muted-foreground">LP lock</p>
              <p className="mt-1 text-sm font-semibold text-foreground">
                {liquidity.liquidity_locked ? "Locked" : "Unlocked"}
              </p>
              <p className="text-xs text-muted-foreground">{liquidity.liquidity_lock_percentage}% supply</p>
            </div>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Dominant LP holder</p>
            <p className="mt-1 font-mono text-sm text-foreground">
              {liquidity.lp_owner ? truncateAddress(liquidity.lp_owner, 10) : "—"}
            </p>
          </div>
        </div>

        <div>
          <p className="mb-3 text-xs uppercase tracking-wide text-muted-foreground">Top pools</p>
          {liquidity.top_pools.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
              No DEX pools with reserves were discovered for this token on the configured chain.
            </div>
          ) : (
            <div className="space-y-3">
              {liquidity.top_pools.map((pool) => (
                <PoolRow key={`${pool.dex}-${pool.pair_address}`} pool={pool} />
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
