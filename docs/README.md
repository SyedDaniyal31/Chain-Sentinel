# ChainSentinel Architecture Documentation

**Version:** 1.0.0  
**Status:** Draft — Architecture Baseline  
**Audience:** Engineering, Security, Product, and Platform teams  
**Classification:** Internal — Architecture Specification

---

## Overview

ChainSentinel is a **blockchain security intelligence platform** that unifies static analysis, on-chain monitoring, threat intelligence, risk quantification, and AI-assisted reporting into a single operational surface for security teams, auditors, and protocol operators.

This documentation set defines the **target architecture** for ChainSentinel v1. It is intentionally implementation-agnostic: it specifies contracts between components, data models, and operational boundaries without prescribing language-specific code.

---

## Document Index

| # | Document | Description |
|---|----------|-------------|
| 1 | [Folder Structure](./01-folder-structure.md) | Monorepo layout, service boundaries, and naming conventions |
| 2 | [System Architecture](./02-system-architecture.md) | High-level topology, data flows, deployment, and cross-cutting concerns |
| 3 | [Database Schema](./03-database-schema.md) | Relational model, indexing strategy, retention, and multi-tenancy |
| 4 | [API Endpoints](./04-api-endpoints.md) | REST API surface, auth model, webhooks, and rate limits |
| 5 | [Smart Contract Architecture](./05-smart-contract-architecture.md) | On-chain attestation, registry, and optional billing primitives |
| 6 | [Risk Scoring Engine](./06-risk-scoring-engine.md) | Scoring dimensions, pipelines, calibration, and explainability |
| 7 | [AI Report Generation](./07-ai-report-generation.md) | LLM pipeline, RAG, guardrails, and human review workflow |
| 8 | [Development Roadmap](./08-development-roadmap.md) | Phased delivery plan, milestones, and success criteria |
| 9 | [Local Development Setup](./09-local-development-setup.md) | Tool installation, verification, and performance tuning |
| 10 | [Docker Architecture](./10-docker-architecture.md) | Local container topology and commands |
| 11 | [GitHub Actions CI/CD](./11-github-actions-cicd.md) | Pipeline design and branch protection |
| 12 | [30-Day Roadmap](./12-30-day-roadmap.md) | Learning-by-building plan for new developers |

---

## Architectural Principles

1. **Security by design** — Assume breach; enforce least privilege, encryption at rest and in transit, and immutable audit trails.
2. **Explainability over black boxes** — Every risk score and AI-generated finding must trace to evidence and reproducible inputs.
3. **Chain-agnostic core** — Abstract chain-specific logic behind adapters; support EVM first, extend to Solana, Cosmos, and others.
4. **Event-driven decoupling** — Ingestion, analysis, scoring, and notification are independently scalable async pipelines.
5. **Deterministic analysis, probabilistic synthesis** — Static analyzers and rule engines produce deterministic outputs; LLMs synthesize narrative only from verified artifacts.
6. **Tenant isolation** — Multi-tenant data partitioning at the database and object-store layer with organization-scoped API keys.

---

## Glossary

| Term | Definition |
|------|------------|
| **Project** | A logical container for contracts, scans, and alerts belonging to one protocol or engagement |
| **Deployment** | A specific contract instance at an address on a given chain |
| **Finding** | A normalized security issue from any analyzer or monitor |
| **Risk Score** | A composite, time-varying numeric assessment with dimensional breakdown |
| **Attestation** | An on-chain anchor of a scan/report content hash |
| **Intel Feed** | External threat data (exploit DB, sanctioned addresses, MEV patterns) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-06-13 | Architecture Team | Initial baseline |
