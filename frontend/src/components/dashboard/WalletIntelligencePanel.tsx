import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { truncateAddress } from "@/lib/format";
import type { ScanResult, WalletIntelligence } from "@/types/scan";

interface WalletIntelligencePanelProps {
  result: ScanResult;
}

function fundingLabel(source: string | null | undefined) {
  if (!source || source === "unknown") {
    return "Unknown";
  }
  return source.replace(/_/g, " ");
}

function resolveWalletIntelligence(result: ScanResult): WalletIntelligence {
  if (result.wallet_intelligence) {
    return result.wallet_intelligence;
  }

  return {
    ownership: {
      creator: result.wallet_creator,
      deployer: result.wallet_deployer,
      owner: result.wallet_owner,
      treasury: result.wallet_treasury,
      proxy_admin: null,
      multisig: null,
      timelock: null,
      upgrade_authority: null,
      roles: [],
    },
    funding: {
      first_funding_tx_hash: null,
      funding_wallet: result.wallet_funding_wallet,
      funding_source: result.wallet_funding_source ?? "unknown",
      is_fresh_wallet: Boolean(result.wallet_is_fresh_deployer),
      deployer_tx_count: 0,
      contract_creation_tx_hash: null,
      contract_creation_block: null,
    },
    reputation: {
      known_scam: Boolean(result.wallet_reputation_known_scam),
      phishing: Boolean(result.wallet_reputation_phishing),
      sanctioned: Boolean(result.wallet_reputation_sanctioned),
      exploit_related: Boolean(result.wallet_reputation_exploit_related),
      confidence: result.wallet_reputation_confidence ?? "low",
    },
    graph: result.wallet_relationship_graph ?? { nodes: [], edges: [] },
    wallet_risk_score: result.wallet_risk_score ?? 0,
    deployer_is_fresh: Boolean(result.wallet_is_fresh_deployer),
    creator_owns_majority: Boolean(result.wallet_creator_owns_majority),
    lp_owner_is_creator: Boolean(result.wallet_lp_owner_is_creator),
    exchange_funded_deployer: Boolean(result.wallet_exchange_funded_deployer),
    tornado_funded_deployer: Boolean(result.wallet_tornado_funded_deployer),
    treasury_is_multisig: Boolean(result.wallet_treasury_is_multisig),
  };
}

function reputationVariant(flag: boolean) {
  return flag ? ("danger" as const) : ("success" as const);
}

export function WalletIntelligencePanel({ result }: WalletIntelligencePanelProps) {
  const wallet = resolveWalletIntelligence(result);
  const hasData = result.wallet_risk_score !== null && result.wallet_risk_score !== undefined;

  return (
    <Card className="border-border/80 bg-surface/80">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border/70 px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-foreground">Wallet Intelligence</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Ownership tracing, funding analysis, reputation, and wallet relationships (M5.2).
          </p>
        </div>
        <Badge variant={wallet.wallet_risk_score >= 40 ? "danger" : wallet.wallet_risk_score >= 20 ? "warning" : "neutral"}>
          Wallet risk {wallet.wallet_risk_score}/100
        </Badge>
      </div>

      {!hasData ? (
        <div className="px-6 py-8 text-center text-sm text-muted-foreground">
          Wallet intelligence was not collected for this scan.
        </div>
      ) : (
        <div className="grid gap-6 px-6 py-5 lg:grid-cols-2">
          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Ownership</p>
              <dl className="mt-2 space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Creator</dt>
                  <dd className="font-mono">{truncateAddress(wallet.ownership.creator)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Owner</dt>
                  <dd className="font-mono">{truncateAddress(wallet.ownership.owner)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Treasury</dt>
                  <dd className="font-mono">{truncateAddress(wallet.ownership.treasury)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Deployer</dt>
                  <dd className="font-mono">{truncateAddress(wallet.ownership.deployer)}</dd>
                </div>
              </dl>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Funding</p>
              <div className="mt-2 rounded-lg border border-border/70 bg-muted/10 p-3 text-sm">
                <p>
                  Source: <span className="font-medium capitalize">{fundingLabel(wallet.funding.funding_source)}</span>
                </p>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  Funder {truncateAddress(wallet.funding.funding_wallet, 10)}
                </p>
                {wallet.deployer_is_fresh ? (
                  <Badge variant="warning" className="mt-2">
                    Fresh deployer wallet
                  </Badge>
                ) : null}
              </div>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Reputation</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge variant={reputationVariant(wallet.reputation.known_scam)}>Known scam</Badge>
                <Badge variant={reputationVariant(wallet.reputation.phishing)}>Phishing</Badge>
                <Badge variant={reputationVariant(wallet.reputation.sanctioned)}>Sanctioned</Badge>
                <Badge variant={reputationVariant(wallet.reputation.exploit_related)}>Exploit related</Badge>
                <Badge variant="neutral">Confidence {wallet.reputation.confidence}</Badge>
              </div>
            </div>
          </div>

          <div>
            <p className="mb-3 text-xs uppercase tracking-wide text-muted-foreground">Wallet graph</p>
            {wallet.graph.nodes.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
                No wallet relationships discovered.
              </div>
            ) : (
              <div className="space-y-3">
                {wallet.graph.nodes.map((node) => (
                  <div key={node.id} className="rounded-lg border border-border/70 bg-muted/10 p-3">
                    <p className="text-sm font-medium capitalize text-foreground">{node.label}</p>
                    <p className="font-mono text-xs text-muted-foreground">{truncateAddress(node.id)}</p>
                    {node.role ? (
                      <Badge variant="neutral" className="mt-2">
                        {node.role.replace(/_/g, " ")}
                      </Badge>
                    ) : null}
                  </div>
                ))}
                <div className="rounded-lg border border-border/60 bg-muted/5 p-3">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Relationships
                  </p>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {wallet.graph.edges.map((edge, index) => (
                      <li key={`${edge.source}-${edge.target}-${index}`}>
                        {truncateAddress(edge.source, 6)} → {truncateAddress(edge.target, 6)} ·{" "}
                        {edge.relationship.replace(/_/g, " ")}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              {wallet.creator_owns_majority ? <Badge variant="danger">Creator owns majority</Badge> : null}
              {wallet.lp_owner_is_creator ? <Badge variant="danger">LP owner is creator</Badge> : null}
              {wallet.tornado_funded_deployer ? <Badge variant="danger">Tornado funded</Badge> : null}
              {wallet.exchange_funded_deployer ? <Badge variant="success">Exchange funded</Badge> : null}
              {wallet.treasury_is_multisig ? <Badge variant="success">Treasury multisig</Badge> : null}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
