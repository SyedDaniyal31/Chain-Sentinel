# 1. Folder Structure

**Document:** ChainSentinel Repository Layout  
**Version:** 1.0.0

---

## 1.1 Design Rationale

ChainSentinel uses a **monorepo with service-oriented packages**. This layout:

- Keeps shared types, protobuf/OpenAPI specs, and domain models in one place
- Enables independent deployment of ingestion, analysis, and API tiers
- Separates **off-chain platform code** from **on-chain attestation contracts**
- Mirrors how security platforms at ConsenSys Diligence and Trail of Bits organize tooling: analyzers as plugins, core as orchestration

---

## 1.2 Root Layout

```
ChainSentinel/
├── docs/                              # Architecture & runbooks (this directory)
├── packages/                          # Deployable services & shared libraries
│   ├── shared/                        # Cross-cutting types, utils, constants
│   ├── proto/                         # gRPC / protobuf definitions (internal RPC)
│   ├── openapi/                       # OpenAPI 3.x specs (public REST)
│   │
│   ├── api-gateway/                   # Public REST + GraphQL edge
│   ├── auth-service/                  # Identity, orgs, RBAC, API keys
│   ├── project-service/               # Projects, deployments, metadata CRUD
│   │
│   ├── ingestion/                     # Block/tx/log ingestion orchestrator
│   │   ├── block-listener/            # Chain head subscription workers
│   │   ├── tx-decoder/                # ABI-aware transaction decoding
│   │   └── log-indexer/               # Event log normalization
│   │
│   ├── analyzer/                      # Static & dynamic analysis orchestration
│   │   ├── orchestrator/              # Scan job scheduling, DAG execution
│   │   ├── adapters/                  # Slither, Mythril, Foundry, custom rules
│   │   └── normalizer/                # Finding normalization to CS schema
│   │
│   ├── risk-engine/                   # Scoring pipelines & calibration
│   │   ├── rules/                     # Deterministic rule definitions (YAML/JSON)
│   │   ├── models/                    # ML model artifacts & feature extractors
│   │   └── explainer/                 # Score breakdown & evidence linking
│   │
│   ├── intel-service/                 # Threat intel ingestion & enrichment
│   ├── monitor-service/               # Real-time alert evaluation
│   ├── report-service/                # Report lifecycle & PDF/HTML rendering
│   ├── ai-pipeline/                   # LLM orchestration, RAG, guardrails
│   ├── notifier/                      # Email, Slack, PagerDuty, webhooks
│   └── admin-console/                 # Internal ops UI (optional Phase 2+)
│
├── contracts/                         # On-chain attestation & registry
│   ├── src/                           # Solidity (EVM) source
│   ├── script/                        # Deployment scripts
│   ├── test/                          # Foundry/Hardhat tests
│   └── deployments/                   # Per-network deployment manifests
│
├── infrastructure/                    # IaC & platform config
│   ├── terraform/                     # Cloud resources (VPC, RDS, EKS, etc.)
│   ├── kubernetes/                    # Helm charts / Kustomize overlays
│   ├── docker/                        # Dockerfiles per service
│   └── local/                         # docker-compose for dev stack
│
├── tools/                             # CLI & developer utilities
│   ├── chainsentinel-cli/             # `cs` CLI for scans, reports, CI
│   └── ci-templates/                  # GitHub Actions / GitLab CI snippets
│
├── tests/                             # Cross-service integration & E2E
│   ├── integration/
│   ├── e2e/
│   └── fixtures/                      # Sample contracts, ABIs, golden files
│
├── .github/                           # CI/CD workflows
├── Makefile                           # Common dev commands
├── turbo.json                         # Monorepo build orchestration (optional)
└── README.md                          # Project overview & quickstart pointer
```

---

## 1.3 Package Internal Convention

Each service under `packages/` follows a consistent internal layout:

```
packages/<service-name>/
├── cmd/                    # Entrypoints (main)
├── internal/               # Private implementation (not imported externally)
│   ├── config/
│   ├── domain/             # Domain entities & business logic
│   ├── repository/         # DB / cache access
│   ├── handler/            # HTTP/gRPC handlers
│   └── worker/             # Background job consumers
├── pkg/                    # Public packages (if any)
├── migrations/             # Service-owned DB migrations (if applicable)
├── Dockerfile
├── go.mod / package.json   # Language-specific manifest
└── README.md               # Service-specific runbook
```

---

## 1.4 Shared Libraries (`packages/shared/`)

```
packages/shared/
├── domain/                 # Canonical domain types (Finding, RiskScore, etc.)
├── chains/                 # Chain adapter interfaces & EVM implementation
├── crypto/                 # Hashing, signing helpers (no key storage)
├── events/                 # Event envelope schemas (Kafka/NATS topics)
├── observability/          # Logging, metrics, tracing conventions
└── validation/             # Input validation schemas
```

---

## 1.5 Documentation Layout (`docs/`)

```
docs/
├── README.md                       # Index (this tree's entry point)
├── 01-folder-structure.md
├── 02-system-architecture.md
├── 03-database-schema.md
├── 06-risk-scoring-engine.md
├── 08-development-roadmap.md
├── 09-local-development-setup.md
├── 10-docker-architecture.md
├── 11-github-actions-cicd.md
└── diagrams/                       # Source files (optional)
```

---

## 1.6 Contracts Layout (`contracts/`)

```
contracts/
├── src/
│   ├── core/
│   │   ├── ChainSentinelRegistry.sol
│   │   ├── AttestationAnchor.sol
│   │   └── SubscriptionManager.sol
│   ├── interfaces/
│   └── libraries/
│       └── MerkleProofLib.sol
├── script/
│   └── Deploy.s.sol
├── test/
└── deployments/
    ├── mainnet/
    ├── sepolia/
    └── arbitrum/
```

---

## 1.7 Naming Conventions

| Artifact | Convention | Example |
|----------|------------|---------|
| Services | kebab-case directories | `risk-engine` |
| Kafka/NATS topics | dot-separated, versioned | `cs.scan.completed.v1` |
| DB tables | snake_case, plural | `risk_scores` |
| API paths | kebab-case, RESTful | `/v1/projects/{id}/deployments` |
| Env vars | SCREAMING_SNAKE | `CS_DATABASE_URL` |
| Feature flags | snake_case | `ai_report_beta_enabled` |

---

## 1.8 Boundary Rules

| Rule | Rationale |
|------|-----------|
| Services MUST NOT import each other's `internal/` packages | Prevents tight coupling |
| Cross-service communication via API, events, or shared `domain` types only | Stable contracts |
| Analyzer adapters MUST NOT write directly to production DB | All writes through orchestrator |
| LLM pipeline MUST NOT call chain RPC directly | Isolation & auditability |
| Contracts repo subtree is independently versioned and audited | Supply chain security |

---

## 1.9 Environment-Specific Overlays

```
infrastructure/kubernetes/
├── base/                   # Common manifests
├── overlays/
│   ├── dev/
│   ├── staging/
│   └── production/
└── secrets/                # Sealed secrets / external secret refs (not plaintext)
```

---

## 1.10 Related Documents

- [System Architecture](./02-system-architecture.md) — How these packages interact at runtime
- [Development Roadmap](./08-development-roadmap.md) — Which packages ship in each phase
