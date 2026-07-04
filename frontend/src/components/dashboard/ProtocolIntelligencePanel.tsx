import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { ProtocolIntelligence, ScanResult } from "@/types/scan";

interface ProtocolIntelligencePanelProps {
  result: ScanResult;
}

function confidenceVariant(level: string) {
  switch (level) {
    case "high":
      return "success" as const;
    case "medium":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

function resolveProtocolIntelligence(result: ScanResult): ProtocolIntelligence | null {
  return result.protocol_intelligence ?? null;
}

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function resolveConfidence(protocol: ProtocolIntelligence) {
  if (typeof protocol.confidence === "string") {
    return { score: null, level: protocol.confidence };
  }
  return protocol.confidence;
}

function IntegrationList({
  title,
  items,
}: {
  title: string;
  items: Array<{ key: string; label: string; confidence: number }>;
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <Badge key={item.key} variant="neutral">
            {item.label} ({item.confidence}%)
          </Badge>
        ))}
      </div>
    </div>
  );
}

export function ProtocolIntelligencePanel({ result }: ProtocolIntelligencePanelProps) {
  const protocol = resolveProtocolIntelligence(result);
  const confidence = protocol ? resolveConfidence(protocol) : null;

  return (
    <Card className="border-border/80 bg-surface/80">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border/70 px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-foreground">Protocol Intelligence</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Protocol family, DeFi and infrastructure integrations, standards, frameworks, and proxy classification.
          </p>
        </div>
        {protocol && confidence ? (
          <Badge variant={confidenceVariant(confidence.level)}>
            {confidence.score !== null
              ? `Confidence ${confidence.score} (${confidence.level})`
              : `Confidence ${confidence.level}`}
          </Badge>
        ) : null}
      </div>

      {!protocol || (protocol.protocol_name === "unknown" && protocol.standards.length === 0) ? (
        <div className="px-6 py-8 text-center text-sm text-muted-foreground">
          Protocol intelligence was not collected for this scan.
        </div>
      ) : (
        <div className="grid gap-6 px-6 py-5 lg:grid-cols-2">
          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Protocol Family</p>
              <p className="mt-1 text-lg font-semibold capitalize text-foreground">
                {formatLabel(protocol.family ?? protocol.protocol_family)}
              </p>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Protocol Name</p>
              <p className="mt-1 text-lg font-semibold capitalize text-foreground">
                {formatLabel(protocol.name ?? protocol.protocol_name)}
              </p>
              <p className="text-sm capitalize text-muted-foreground">
                {formatLabel(protocol.protocol_type)}
              </p>
            </div>

            <IntegrationList
              title="DEX Integrations"
              items={(protocol.dexes ?? []).map((dex) => ({
                key: `${dex.name}-${dex.role}`,
                label: `${dex.name} (${dex.role})`,
                confidence: dex.confidence,
              }))}
            />

            <IntegrationList
              title="Lending Integrations"
              items={(protocol.lending ?? []).map((loan) => ({
                key: `${loan.name}-${loan.role}`,
                label: `${loan.name} (${loan.role})`,
                confidence: loan.confidence,
              }))}
            />

            <IntegrationList
              title="Oracle Integrations"
              items={(protocol.oracles ?? []).map((oracle) => ({
                key: oracle.name,
                label: oracle.name,
                confidence: oracle.confidence,
              }))}
            />

            <IntegrationList
              title="Bridges"
              items={(protocol.bridges ?? []).map((bridge) => ({
                key: `${bridge.name}-${bridge.role}`,
                label: `${bridge.name} (${bridge.role})`,
                confidence: bridge.confidence,
              }))}
            />

            <IntegrationList
              title="Vaults"
              items={(protocol.vaults ?? []).map((vault) => ({
                key: `${vault.name}-${vault.type}`,
                label: `${vault.name} (${vault.type})`,
                confidence: vault.confidence,
              }))}
            />

            <IntegrationList
              title="NFTs"
              items={(protocol.nfts ?? []).map((nft) => ({
                key: `${nft.standard}-${nft.marketplace}`,
                label: nft.marketplace ? `${nft.standard} · ${nft.marketplace}` : nft.standard,
                confidence: nft.confidence,
              }))}
            />

            <IntegrationList
              title="Governance"
              items={(protocol.governance ?? []).map((gov) => ({
                key: gov.name,
                label: gov.name,
                confidence: gov.confidence,
              }))}
            />

            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Standards</p>
              <div className="flex flex-wrap gap-2">
                {protocol.standards.length === 0 ? (
                  <Badge variant="neutral">None detected</Badge>
                ) : (
                  protocol.standards.map((standard) => (
                    <Badge key={standard} variant="neutral">
                      {standard}
                    </Badge>
                  ))
                )}
              </div>
            </div>

            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Frameworks</p>
              <div className="flex flex-wrap gap-2">
                {protocol.frameworks.length === 0 ? (
                  <Badge variant="neutral">None detected</Badge>
                ) : (
                  protocol.frameworks.map((framework) => (
                    <Badge key={framework} variant="warning">
                      {framework}
                    </Badge>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Confidence Score</p>
              <p className="mt-1 text-sm font-semibold text-foreground">
                {confidence?.score ?? "—"}
              </p>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Confidence Level</p>
              <p className="mt-1 text-sm font-semibold capitalize text-foreground">
                {confidence?.level ?? "—"}
              </p>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Proxy type</p>
              <p className="mt-1 text-sm font-semibold capitalize text-foreground">
                {formatLabel(protocol.proxy_type)}
              </p>
            </div>

            {protocol.integrations.length > 0 ? (
              <div>
                <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Integrations</p>
                <div className="flex flex-wrap gap-2">
                  {protocol.integrations.map((integration) => (
                    <Badge key={integration} variant="neutral">
                      {integration}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}

            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Detection reasons</p>
              {protocol.detection_reasons.length === 0 ? (
                <p className="text-sm text-muted-foreground">No detection reasons recorded.</p>
              ) : (
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {protocol.detection_reasons.map((reason) => (
                    <li key={reason} className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2">
                      {reason}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {protocol.architecture_summary &&
            (protocol.architecture_summary.application_type !== "unknown" ||
              protocol.architecture_summary.protocol_stack.length > 0) ? (
              <div>
                <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                  Architecture Summary
                </p>
                <div className="space-y-2 rounded-lg border border-border/60 bg-muted/10 px-3 py-3 text-sm">
                  <p>
                    <span className="text-muted-foreground">Application type:</span>{" "}
                    <span className="capitalize text-foreground">
                      {formatLabel(protocol.architecture_summary.application_type)}
                    </span>
                  </p>
                  {protocol.architecture_summary.protocol_stack.length > 0 ? (
                    <p>
                      <span className="text-muted-foreground">Protocol stack:</span>{" "}
                      {protocol.architecture_summary.protocol_stack.join(", ")}
                    </p>
                  ) : null}
                  {protocol.architecture_summary.oracle ? (
                    <p>
                      <span className="text-muted-foreground">Oracle:</span>{" "}
                      {protocol.architecture_summary.oracle}
                    </p>
                  ) : null}
                  {protocol.architecture_summary.liquidity ? (
                    <p>
                      <span className="text-muted-foreground">Liquidity:</span>{" "}
                      {protocol.architecture_summary.liquidity}
                    </p>
                  ) : null}
                  {protocol.architecture_summary.bridge ? (
                    <p>
                      <span className="text-muted-foreground">Bridge:</span>{" "}
                      {protocol.architecture_summary.bridge}
                    </p>
                  ) : null}
                  {protocol.architecture_summary.governance ? (
                    <p>
                      <span className="text-muted-foreground">Governance:</span>{" "}
                      {protocol.architecture_summary.governance}
                    </p>
                  ) : null}
                  {protocol.architecture_summary.upgradeability ? (
                    <p>
                      <span className="text-muted-foreground">Upgradeability:</span>{" "}
                      {formatLabel(protocol.architecture_summary.upgradeability)}
                    </p>
                  ) : null}
                  {protocol.architecture_summary.ownership ? (
                    <p>
                      <span className="text-muted-foreground">Ownership:</span>{" "}
                      {protocol.architecture_summary.ownership}
                    </p>
                  ) : null}
                </div>
              </div>
            ) : null}

            {(protocol.relationships ?? []).length > 0 ? (
              <div>
                <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                  Relationships
                </p>
                <div className="overflow-x-auto rounded-lg border border-border/60">
                  <table className="min-w-full text-left text-sm">
                    <thead className="border-b border-border/60 bg-muted/10 text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Source</th>
                        <th className="px-3 py-2">Relationship</th>
                        <th className="px-3 py-2">Target</th>
                        <th className="px-3 py-2">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {protocol.relationships?.map((relationship) => (
                        <tr
                          key={`${relationship.source}-${relationship.relationship_type}-${relationship.target}`}
                          className="border-b border-border/40 last:border-b-0"
                        >
                          <td className="px-3 py-2 text-foreground">{relationship.source}</td>
                          <td className="px-3 py-2 text-muted-foreground">
                            {relationship.relationship_type}
                          </td>
                          <td className="px-3 py-2 text-foreground">{relationship.target}</td>
                          <td className="px-3 py-2 text-muted-foreground">
                            {relationship.confidence}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {protocol.architecture_graph ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Graph prepared: {protocol.architecture_graph.nodes.length} nodes,{" "}
                    {protocol.architecture_graph.edges.length} edges
                  </p>
                ) : null}
              </div>
            ) : null}

            {protocol.threat_surface &&
            (protocol.threat_surface.external_dependencies.length > 0 ||
              protocol.threat_surface.trust_boundaries.length > 0 ||
              protocol.threat_surface.attack_paths.length > 0) ? (
              <div className="space-y-4 border-t border-border/60 pt-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Threat Surface</p>

                {protocol.threat_surface.external_dependencies.length > 0 ? (
                  <IntegrationList
                    title="External Dependencies"
                    items={protocol.threat_surface.external_dependencies.map((dep) => ({
                      key: `${dep.category}-${dep.name}`,
                      label: `${dep.name}${dep.role ? ` (${dep.role})` : ""}`,
                      confidence: dep.confidence,
                    }))}
                  />
                ) : null}

                {protocol.threat_surface.trust_boundaries.length > 0 ? (
                  <IntegrationList
                    title="Trust Boundaries"
                    items={protocol.threat_surface.trust_boundaries.map((boundary) => ({
                      key: `${boundary.boundary_type}-${boundary.label}`,
                      label: boundary.label,
                      confidence: boundary.confidence,
                    }))}
                  />
                ) : null}

                {protocol.threat_surface.critical_assets.length > 0 ? (
                  <IntegrationList
                    title="Critical Assets"
                    items={protocol.threat_surface.critical_assets.map((asset) => ({
                      key: `${asset.asset_type}-${asset.label}`,
                      label: asset.label,
                      confidence: asset.confidence,
                    }))}
                  />
                ) : null}

                {protocol.threat_surface.attack_paths.length > 0 ? (
                  <div>
                    <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                      Attack Paths
                    </p>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {protocol.threat_surface.attack_paths.map((path) => (
                        <li
                          key={path.name}
                          className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2"
                        >
                          <p className="font-medium text-foreground">{path.name}</p>
                          <p className="mt-1">{path.steps.join(" → ")}</p>
                          <p className="mt-1 text-xs">Confidence {path.confidence}%</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {protocol.threat_surface.dependency_graph ? (
                  <p className="text-xs text-muted-foreground">
                    Dependency graph prepared:{" "}
                    {protocol.threat_surface.dependency_graph.nodes.length} nodes,{" "}
                    {protocol.threat_surface.dependency_graph.edges.length} edges
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </Card>
  );
}
