/** Mirrors ChainSentinel backend scan API schemas. */

export type ScanType = "wallet" | "contract";
export type ScanJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type RiskLevel = "low" | "medium" | "high";
export type ThreatLevel = "low" | "medium" | "high" | "critical";
export type CentralizationLevel = "low" | "medium" | "high";
export type ConfidenceLevel = "low" | "medium" | "high";
export type GovernanceType =
  | "none"
  | "ownable"
  | "ownable2step"
  | "access_control"
  | "proxy_admin"
  | "timelock"
  | "multisig"
  | "unknown";
export type UpgradeAuthority = "none" | "eoa" | "multisig" | "timelock" | "contract" | "unknown";
export type CapabilitySeverity = "low" | "medium" | "high" | "critical";
export type CapabilityConfidence = "low" | "medium" | "high";
export type CapabilityDetectionMethod = "source" | "bytecode" | "role" | "simulation" | "none";

export type HoneypotFindingType =
  | "trading_gate"
  | "whitelist_restriction"
  | "blacklist_probe"
  | "sell_restriction"
  | "transfer_tax_control"
  | "modifiable_tax"
  | "anti_bot_pattern"
  | "high_buy_tax"
  | "high_sell_tax"
  | "buy_path_blocked"
  | "sell_path_blocked"
  | "transfer_path_blocked"
  | "honeypot_confirmed";

export type HoneypotSeverity = "low" | "medium" | "high" | "critical";
export type HoneypotConfidence = "low" | "medium" | "high";
export type HoneypotDetectionMethod = "source" | "bytecode" | "simulation" | "none";
export type HoneypotSimulationStatus = "not_run" | "skipped" | "pending" | "completed" | "failed";

export interface CapabilityDetail {
  enabled: boolean;
  controller: string | null;
  severity: CapabilitySeverity;
  confidence: CapabilityConfidence;
  detection_method: CapabilityDetectionMethod;
}

export interface HoneypotTradePathResult {
  attempted: boolean;
  success: boolean | null;
  tax_bps: number | null;
  revert_reason: string | null;
  gas_used: number | null;
}

export interface HoneypotFinding {
  finding_type: HoneypotFindingType;
  enabled: boolean;
  severity: HoneypotSeverity;
  confidence: HoneypotConfidence;
  detection_method: HoneypotDetectionMethod;
  title: string;
  description: string;
  evidence: string[];
}

export interface HoneypotSummary {
  finding_count: number;
  critical_count: number;
  honeypot_score: number;
  honeypot_risk: HoneypotSeverity;
  is_suspected: boolean;
  is_confirmed: boolean;
}

export interface HoneypotSimulationState {
  status: HoneypotSimulationStatus;
  fork_block: number | null;
  pair_address: string | null;
  router_address: string | null;
  buy: HoneypotTradePathResult;
  transfer: HoneypotTradePathResult;
  sell: HoneypotTradePathResult;
  round_trip_success: boolean | null;
}

export interface HoneypotIntelligence {
  summary: HoneypotSummary;
  findings: HoneypotFinding[];
  simulation: HoneypotSimulationState;
}

export interface LiquidityPool {
  dex: string;
  pair_address: string;
  token0: string;
  token1: string;
  reserve0: string;
  reserve1: string;
  liquidity_native: number;
  liquidity_usd: string;
  lp_total_supply: string;
  lp_owner: string | null;
  lp_owner_balance: string;
  liquidity_locked: boolean;
  liquidity_lock_percentage: string;
  lock_expiry: string | null;
}

export interface LiquidityIntelligence {
  has_liquidity: boolean;
  liquidity_usd: string;
  primary_dex: string | null;
  pair_address: string | null;
  lp_owner: string | null;
  liquidity_locked: boolean;
  liquidity_lock_percentage: string;
  lock_expiry: string | null;
  top_pools: LiquidityPool[];
}

export type FundingSourceType =
  | "unknown"
  | "eoa"
  | "exchange"
  | "bridge"
  | "mixer"
  | "tornado";

export interface WalletRoleNode {
  address: string;
  role: string;
}

export interface WalletOwnership {
  creator: string | null;
  deployer: string | null;
  owner: string | null;
  proxy_admin: string | null;
  treasury: string | null;
  multisig: string | null;
  timelock: string | null;
  upgrade_authority: string | null;
  roles: WalletRoleNode[];
}

export interface WalletFunding {
  first_funding_tx_hash: string | null;
  funding_wallet: string | null;
  funding_source: FundingSourceType;
  is_fresh_wallet: boolean;
  deployer_tx_count: number;
  contract_creation_tx_hash: string | null;
  contract_creation_block: number | null;
}

export interface WalletReputation {
  known_scam: boolean;
  phishing: boolean;
  sanctioned: boolean;
  exploit_related: boolean;
  confidence: ConfidenceLevel;
}

export interface WalletGraphNode {
  id: string;
  label: string;
  role: string | null;
}

export interface WalletGraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface WalletGraph {
  nodes: WalletGraphNode[];
  edges: WalletGraphEdge[];
}

export interface WalletIntelligence {
  ownership: WalletOwnership;
  funding: WalletFunding;
  reputation: WalletReputation;
  graph: WalletGraph;
  wallet_risk_score: number;
  deployer_is_fresh: boolean;
  creator_owns_majority: boolean;
  lp_owner_is_creator: boolean;
  exchange_funded_deployer: boolean;
  tornado_funded_deployer: boolean;
  treasury_is_multisig: boolean;
}

export interface ProtocolConfidence {
  score: number;
  level: ConfidenceLevel;
}

export interface DexIntegration {
  name: string;
  role: string;
  confidence: number;
}

export interface LendingIntegration {
  name: string;
  role: string;
  confidence: number;
}

export interface OracleIntegration {
  name: string;
  confidence: number;
}

export interface BridgeIntegration {
  name: string;
  role: string;
  confidence: number;
}

export interface VaultIntegration {
  name: string;
  type: string;
  confidence: number;
}

export interface NftIntegration {
  standard: string;
  marketplace: string;
  confidence: number;
}

export interface GovernanceIntegration {
  name: string;
  confidence: number;
}

export interface ProtocolRelationship {
  source: string;
  target: string;
  relationship_type: string;
  confidence: number;
  detection_source: string;
}

export interface ArchitectureGraphNode {
  id: string;
  label: string;
  node_type: string;
  address?: string | null;
}

export interface ArchitectureGraphEdge {
  source: string;
  target: string;
  relationship: string;
  confidence: number;
  detection_source: string;
}

export interface ArchitectureGraph {
  nodes: ArchitectureGraphNode[];
  edges: ArchitectureGraphEdge[];
}

export interface ArchitectureSummary {
  application_type: string;
  protocol_stack: string[];
  oracle: string | null;
  liquidity: string | null;
  bridge: string | null;
  governance: string | null;
  upgradeability: string | null;
  ownership: string | null;
}

export interface ExternalDependency {
  category: string;
  name: string;
  role: string;
  confidence: number;
  detection_source: string;
  address?: string | null;
}

export interface TrustBoundary {
  boundary_type: string;
  label: string;
  confidence: number;
  detection_source: string;
  address?: string | null;
}

export interface PrivilegedEntity {
  entity_type: string;
  label: string;
  confidence: number;
  detection_source: string;
  address?: string | null;
}

export interface AttackPath {
  name: string;
  steps: string[];
  confidence: number;
  detection_source: string;
}

export interface CriticalAsset {
  asset_type: string;
  label: string;
  confidence: number;
  address?: string | null;
}

export interface ThreatDependencyGraph {
  nodes: ArchitectureGraphNode[];
  edges: Array<{
    source: string;
    target: string;
    relationship: string;
    confidence: number;
  }>;
}

export interface ThreatSurface {
  external_dependencies: ExternalDependency[];
  trust_boundaries: TrustBoundary[];
  privileged_entities: PrivilegedEntity[];
  attack_paths: AttackPath[];
  dependency_graph: ThreatDependencyGraph;
  critical_assets: CriticalAsset[];
}

export interface ProtocolIntelligence {
  protocol_family: string;
  protocol_name: string;
  protocol_type: string;
  family?: string;
  name?: string;
  standards: string[];
  frameworks: string[];
  integrations: string[];
  proxy_type: string;
  dexes?: DexIntegration[];
  lending?: LendingIntegration[];
  oracles?: OracleIntegration[];
  bridges?: BridgeIntegration[];
  vaults?: VaultIntegration[];
  nfts?: NftIntegration[];
  governance?: GovernanceIntegration[];
  relationships?: ProtocolRelationship[];
  architecture_graph?: ArchitectureGraph;
  architecture_summary?: ArchitectureSummary;
  threat_surface?: ThreatSurface;
  confidence: ProtocolConfidence | ConfidenceLevel;
  detection_reasons: string[];
}

export interface GovernanceRole {
  name: string;
  role_id: string;
  admin_role_name: string | null;
  admin_role_id: string | null;
  is_default_admin: boolean;
}

export interface GovernanceIntelligence {
  governance_type: GovernanceType;
  upgrade_authority: UpgradeAuthority;
  has_timelock: boolean;
  role_count: number;
  roles: GovernanceRole[];
  ownership_address: string | null;
  ownership_renounced?: boolean;
  source_confidence?: ConfidenceLevel;
}
export type AdminType = "eoa" | "contract" | "multisig";

export interface ScanCreateRequest {
  scan_type: ScanType;
  target_address: string;
  chain_id?: number;
}

export interface ScanCreateResponse {
  id: number;
  status: ScanJobStatus;
}

export interface ScanResult {
  chain_id: number;
  latest_block: number;
  wallet_balance_wei: number | null;
  wallet_balance_eth: string | null;
  is_contract: boolean | null;
  bytecode_size: number | null;
  is_upgradeable: boolean | null;
  implementation_address: string | null;
  admin_address: string | null;
  admin_type: AdminType | null;
  owner_address: string | null;
  owner_type: AdminType | null;
  is_timelock: boolean | null;
  min_delay: number | null;
  mint_capability: boolean | null;
  pause_capability: boolean | null;
  blacklist_capability: boolean | null;
  ownership_capability: boolean | null;
  trading_enabled_control: boolean | null;
  whitelist_control: boolean | null;
  blacklist_sell_blocking: boolean | null;
  transfer_tax_control: boolean | null;
  trade_simulated: boolean | null;
  can_buy: boolean | null;
  can_sell: boolean | null;
  buy_tax_bps: number | null;
  sell_tax_bps: number | null;
  risk_score: string | null;
  risk_level: RiskLevel | null;
  risk_reasons: string[] | null;
  threat_level: ThreatLevel | null;
  centralization_level: CentralizationLevel | null;
  confidence_level: ConfidenceLevel | null;
  governance_type: GovernanceType | null;
  upgrade_authority: UpgradeAuthority | null;
  role_count: number | null;
  governance_roles: GovernanceRole[] | null;
  governance_ownership_address: string | null;
  governance: GovernanceIntelligence | null;
  capability_count: number | null;
  capabilities_detail: Record<string, CapabilityDetail> | null;
  capabilities: Record<string, CapabilityDetail> | null;
  honeypot_score: number | null;
  honeypot_risk: HoneypotSeverity | null;
  honeypot_finding_count: number | null;
  honeypot_is_suspected: boolean | null;
  honeypot_is_confirmed: boolean | null;
  honeypot_simulation_status: HoneypotSimulationStatus | null;
  honeypot_findings: HoneypotFinding[] | null;
  honeypot_simulation: HoneypotSimulationState | null;
  honeypot: HoneypotIntelligence | null;
  liquidity_has_liquidity: boolean | null;
  liquidity_usd: string | null;
  liquidity_primary_dex: string | null;
  liquidity_pair_address: string | null;
  liquidity_lp_owner: string | null;
  liquidity_locked: boolean | null;
  liquidity_lock_percentage: string | null;
  liquidity_lock_expiry: string | null;
  liquidity_top_pools: LiquidityPool[] | null;
  liquidity: LiquidityIntelligence | null;
  wallet_creator: string | null;
  wallet_deployer: string | null;
  wallet_owner: string | null;
  wallet_treasury: string | null;
  wallet_funding_source: FundingSourceType | null;
  wallet_funding_wallet: string | null;
  wallet_is_fresh_deployer: boolean | null;
  wallet_reputation_known_scam: boolean | null;
  wallet_reputation_phishing: boolean | null;
  wallet_reputation_sanctioned: boolean | null;
  wallet_reputation_exploit_related: boolean | null;
  wallet_reputation_confidence: ConfidenceLevel | null;
  wallet_lp_owner_is_creator: boolean | null;
  wallet_creator_owns_majority: boolean | null;
  wallet_exchange_funded_deployer: boolean | null;
  wallet_tornado_funded_deployer: boolean | null;
  wallet_treasury_is_multisig: boolean | null;
  wallet_risk_score: number | null;
  wallet_relationship_graph: WalletGraph | null;
  wallet_intelligence: WalletIntelligence | null;
  protocol_intelligence: ProtocolIntelligence | null;
  created_at: string;
}

export interface ScanJob {
  id: number;
  scan_type: ScanType;
  target_address: string;
  status: ScanJobStatus;
  risk_score: string | null;
  chain_id?: number | null;
  block_number?: number | null;
  rpc_endpoint?: string | null;
  created_at: string;
  updated_at: string;
  result: ScanResult | null;
}

export interface ChainInfo {
  chain_id: number;
  name: string;
  native_currency: string;
  explorer_url: string;
  testnet: boolean;
  supported: boolean;
}

export interface ChainListResponse {
  chains: ChainInfo[];
}

export interface ScanListItem {
  id: number;
  scan_type: ScanType;
  target_address: string;
  status: ScanJobStatus;
  risk_score: string | null;
  risk_level: RiskLevel | null;
  created_at: string;
}

export interface PaginatedScanResponse {
  items: ScanListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ScanSummaryResponse {
  total_scans: number;
  completed_scans: number;
  failed_scans: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  average_risk_score: number;
}

export interface ApiErrorBody {
  detail?: string | { msg: string; type: string }[];
  error_code?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body?: ApiErrorBody,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const TERMINAL_STATUSES: ScanJobStatus[] = ["completed", "failed", "cancelled"];
