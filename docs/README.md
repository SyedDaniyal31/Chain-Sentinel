# ChainSentinel Architecture Documentation

**Version:** 1.0.0  
**Audience:** Engineering, Security, and Platform teams

---

## Overview

ChainSentinel is a **blockchain security intelligence platform** combining on-demand contract/wallet scanning, runtime transaction analysis, risk evidence correlation, protocol discovery, and continuous monitoring.

Implementation lives under `backend/app/` — especially `app/blockchain/` (runtime, risk, protocol_scan, continuous) and `app/services/` (analyzers). This documentation covers system design and operations only.

---

## Documentation Index

| # | Document | Description |
|---|----------|-------------|
| 1 | [Folder Structure](./01-folder-structure.md) | Repository layout and conventions |
| 2 | [System Architecture](./02-system-architecture.md) | Topology, data flows, deployment |
| 3 | [Database Schema](./03-database-schema.md) | Relational model and retention |
| 6 | [Risk Scoring Engine](./06-risk-scoring-engine.md) | Scoring design and explainability |
| 8 | [Development Roadmap](./08-development-roadmap.md) | Phased delivery plan |
| 9 | [Local Development Setup](./09-local-development-setup.md) | Tool installation and verification |
| 10 | [Docker Architecture](./10-docker-architecture.md) | Local container topology |
| 11 | [GitHub Actions CI/CD](./11-github-actions-cicd.md) | Pipeline design |

**Live API reference:** run the backend and open `/docs` (OpenAPI) in non-production environments.

**Database operations:** [backend/docs/MIGRATIONS.md](../backend/docs/MIGRATIONS.md)

**Engine source code:**

| Package | Path |
|---------|------|
| Multi-chain & analyzers | `backend/app/blockchain/`, `backend/app/services/` |
| Runtime intelligence | `backend/app/blockchain/runtime/` |
| Risk engine | `backend/app/blockchain/risk/` |
| Protocol scan | `backend/app/blockchain/protocol_scan/`, `protocol_scheduler/` |
| Continuous monitoring | `backend/app/blockchain/continuous/` |

---

## Architectural Principles

1. **Security by design** — Least privilege, validated inputs, structured error handling
2. **Explainability** — Risk scores and findings trace to evidence artifacts
3. **Deterministic analysis** — Rule engines and analyzers produce reproducible outputs
4. **Chain-agnostic core** — EVM-first with chain registry abstraction
5. **Layered architecture** — API → services → blockchain engines

---

## Glossary

| Term | Definition |
|------|------------|
| **Scan job** | On-demand wallet or contract analysis request |
| **Risk evidence** | Normalized security signal with severity and score |
| **Watch** | Continuous monitoring subscription for a protocol root address |
| **Risk delta** | Posture change between two evidence snapshots |
| **Alert batch** | Deduplicated alerts generated from a risk delta report |
