# 4. API Endpoints

**Document:** ChainSentinel Public REST API  
**Version:** 1.0.0  
**Base URL:** `https://api.chainsentinel.io/v1`  
**Specification Format:** OpenAPI 3.1 (maintained in `packages/openapi/`)

---

## 4.1 API Design Principles

1. **RESTful resources** with predictable nouns and HTTP verb semantics
2. **Versioned URL prefix** (`/v1`) — breaking changes require new major version
3. **Cursor-based pagination** for all list endpoints (`?cursor=&limit=`)
4. **Idempotency-Key header** on all mutating POST/PATCH operations
5. **Consistent error envelope** across all endpoints
6. **HATEOAS links** in list responses for discoverability (optional Phase 2)

---

## 4.2 Authentication

### 4.2.1 Methods

| Method | Header | Use Case |
|--------|--------|----------|
| **API Key** | `Authorization: Bearer cs_live_...` | CI/CD, server-to-server |
| **JWT (User)** | `Authorization: Bearer eyJ...` | Dashboard, interactive use |
| **OAuth 2.0** | Authorization Code + PKCE | SSO integrations |

### 4.2.2 Scopes

| Scope | Permissions |
|-------|-------------|
| `projects:read` | List/get projects |
| `projects:write` | Create/update/archive projects |
| `deployments:read` | List/get deployments |
| `deployments:write` | Register/update deployments |
| `scans:read` | Get scan results |
| `scans:write` | Trigger scans |
| `findings:read` | List/get findings |
| `findings:write` | Update finding status |
| `risk:read` | Get scores and history |
| `alerts:read` | List alerts |
| `alerts:write` | Acknowledge/resolve alerts |
| `reports:read` | Download reports |
| `reports:write` | Generate/publish reports |
| `webhooks:write` | Manage webhook subscriptions |
| `admin:*` | Org admin operations |

---

## 4.3 Standard Response Envelope

### Success (single resource)

```json
{
  "data": { },
  "meta": {
    "request_id": "req_01HXYZ...",
    "timestamp": "2026-06-13T12:00:00Z"
  }
}
```

### Success (list)

```json
{
  "data": [ ],
  "pagination": {
    "cursor": "eyJpZCI6...",
    "has_more": true,
    "limit": 25
  },
  "meta": { "request_id": "...", "timestamp": "..." }
}
```

### Error

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable summary",
    "details": [
      { "field": "chain_id", "issue": "unsupported chain" }
    ]
  },
  "meta": { "request_id": "...", "timestamp": "..." }
}
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Successful GET/PATCH |
| 201 | Resource created |
| 202 | Async job accepted (scan, report) |
| 204 | Successful DELETE |
| 400 | Validation error |
| 401 | Missing/invalid auth |
| 403 | Insufficient scope or RLS denial |
| 404 | Resource not found |
| 409 | Conflict (duplicate deployment) |
| 422 | Semantic error (invalid state transition) |
| 429 | Rate limit exceeded |
| 500 | Internal error |

---

## 4.4 Rate Limits

| Tier | Requests/min | Burst | Scan jobs/hour |
|------|-------------|-------|----------------|
| Free | 60 | 10 | 5 |
| Pro | 600 | 50 | 50 |
| Enterprise | Custom | Custom | Custom |

**Headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`

---

## 4.5 Endpoint Reference

### 4.5.1 Health & Meta

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness probe |
| GET | `/ready` | None | Readiness (DB, Kafka connectivity) |
| GET | `/meta/chains` | Optional | Supported chain IDs and metadata |
| GET | `/meta/severity` | Optional | Severity/confidence enum definitions |

---

### 4.5.2 Organization & Users

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/org` | `projects:read` | Current organization profile |
| PATCH | `/org` | `admin:*` | Update org settings |
| GET | `/org/users` | `admin:*` | List org members |
| POST | `/org/users/invite` | `admin:*` | Invite user by email |
| DELETE | `/org/users/{user_id}` | `admin:*` | Remove member |
| GET | `/org/api-keys` | `admin:*` | List API keys (prefix only) |
| POST | `/org/api-keys` | `admin:*` | Create API key (secret shown once) |
| DELETE | `/org/api-keys/{key_id}` | `admin:*` | Revoke API key |
| GET | `/org/audit-logs` | `admin:*` | Query audit trail |

---

### 4.5.3 Projects

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/projects` | `projects:read` | List projects |
| POST | `/projects` | `projects:write` | Create project |
| GET | `/projects/{project_id}` | `projects:read` | Get project |
| PATCH | `/projects/{project_id}` | `projects:write` | Update project |
| DELETE | `/projects/{project_id}` | `projects:write` | Archive project |
| GET | `/projects/{project_id}/summary` | `projects:read` | Aggregated stats (findings, score, alerts) |

**POST `/projects` body:**

```json
{
  "name": "Acme DeFi Protocol",
  "description": "Core lending contracts",
  "tags": ["defi", "lending"],
  "default_chain_ids": [1, 42161],
  "settings": {
    "auto_scan_on_push": true,
    "default_tools": ["slither", "chainsentinel-rules"]
  }
}
```

---

### 4.5.4 Deployments

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/projects/{project_id}/deployments` | `deployments:read` | List deployments |
| POST | `/projects/{project_id}/deployments` | `deployments:write` | Register deployment |
| GET | `/deployments/{deployment_id}` | `deployments:read` | Get deployment |
| PATCH | `/deployments/{deployment_id}` | `deployments:write` | Update metadata |
| DELETE | `/deployments/{deployment_id}` | `deployments:write` | Stop monitoring |
| POST | `/deployments/{deployment_id}/verify` | `deployments:write` | Trigger explorer verification check |
| GET | `/deployments/{deployment_id}/abi` | `deployments:read` | Get stored ABI |
| PUT | `/deployments/{deployment_id}/abi` | `deployments:write` | Upload/update ABI |

**POST deployment body:**

```json
{
  "chain_id": 1,
  "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "name": "LendingPool V2",
  "contract_type": "proxy",
  "source_repo_url": "https://github.com/acme/contracts",
  "source_commit": "a1b2c3d4",
  "metadata": {
    "compiler": "0.8.24",
    "optimizer_runs": 200
  }
}
```

---

### 4.5.5 Scans

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/deployments/{deployment_id}/scans` | `scans:read` | List scans |
| POST | `/deployments/{deployment_id}/scans` | `scans:write` | Trigger scan (async, 202) |
| GET | `/scans/{scan_id}` | `scans:read` | Get scan status & metadata |
| GET | `/scans/{scan_id}/findings` | `findings:read` | List findings for scan |
| GET | `/scans/{scan_id}/artifacts` | `scans:read` | Presigned URLs for raw output |
| POST | `/scans/{scan_id}/cancel` | `scans:write` | Cancel running scan |

**POST scan body:**

```json
{
  "scan_type": "static",
  "tools": ["slither", "mythril", "chainsentinel-rules"],
  "source": {
    "type": "git",
    "url": "https://github.com/acme/contracts",
    "commit": "a1b2c3d4",
    "path": "src/LendingPool.sol"
  },
  "options": {
    "exclude_dependencies": true,
    "timeout_seconds": 600
  }
}
```

**Scan status response:**

```json
{
  "data": {
    "id": "scan_uuid",
    "status": "completed",
    "tools": ["slither"],
    "finding_counts": {
      "critical": 0,
      "high": 2,
      "medium": 5,
      "low": 3,
      "informational": 8
    },
    "content_hash": "0x...",
    "started_at": "...",
    "completed_at": "..."
  }
}
```

---

### 4.5.6 Findings

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/projects/{project_id}/findings` | `findings:read` | List findings (filterable) |
| GET | `/findings/{finding_id}` | `findings:read` | Get finding detail |
| PATCH | `/findings/{finding_id}` | `findings:write` | Update status |
| GET | `/findings/{finding_id}/evidence` | `findings:read` | List evidence items |
| GET | `/findings/{finding_id}/history` | `findings:read` | Status change history |

**Query filters (list):** `severity`, `status`, `category`, `deployment_id`, `scan_id`, `q` (full-text)

**PATCH finding body:**

```json
{
  "status": "false_positive",
  "comment": "Protected by upstream access control in BaseVault"
}
```

---

### 4.5.7 Risk Scores

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/deployments/{deployment_id}/risk` | `risk:read` | Current risk score snapshot |
| GET | `/deployments/{deployment_id}/risk/history` | `risk:read` | Time-series scores |
| GET | `/projects/{project_id}/risk/summary` | `risk:read` | Aggregated project risk |
| POST | `/deployments/{deployment_id}/risk/recalculate` | `risk:read` | Force re-score (async) |
| GET | `/deployments/{deployment_id}/risk/explain` | `risk:read` | Full factor breakdown |

**Risk snapshot response:**

```json
{
  "data": {
    "composite_score": 67.4,
    "severity_band": "high",
    "dimensions": { },
    "top_factors": [
      {
        "id": "open_critical_findings",
        "label": "1 open critical finding",
        "contribution": 28.5,
        "evidence_refs": ["finding_uuid"]
      }
    ],
    "model_version": "2.1.0",
    "calculated_at": "2026-06-13T11:45:00Z"
  }
}
```

---

### 4.5.8 Alerts & Rules

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/projects/{project_id}/alert-rules` | `alerts:read` | List alert rules |
| POST | `/projects/{project_id}/alert-rules` | `alerts:write` | Create rule |
| GET | `/alert-rules/{rule_id}` | `alerts:read` | Get rule |
| PATCH | `/alert-rules/{rule_id}` | `alerts:write` | Update rule |
| DELETE | `/alert-rules/{rule_id}` | `alerts:write` | Delete rule |
| GET | `/projects/{project_id}/alerts` | `alerts:read` | List triggered alerts |
| GET | `/alerts/{alert_id}` | `alerts:read` | Get alert detail |
| POST | `/alerts/{alert_id}/acknowledge` | `alerts:write` | Acknowledge |
| POST | `/alerts/{alert_id}/resolve` | `alerts:write` | Resolve with note |

**Example alert rule:**

```json
{
  "name": "Critical finding on mainnet",
  "rule_type": "finding_severity",
  "conditions": {
    "severity_gte": "critical",
    "chain_ids": [1],
    "status": ["open"]
  },
  "actions": {
    "channels": ["slack", "email"],
    "webhook_ids": ["wh_uuid"]
  },
  "cooldown_seconds": 3600
}
```

---

### 4.5.9 Reports

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/projects/{project_id}/reports` | `reports:read` | List reports |
| POST | `/projects/{project_id}/reports` | `reports:write` | Request report generation (202) |
| GET | `/reports/{report_id}` | `reports:read` | Get report metadata |
| GET | `/reports/{report_id}/sections` | `reports:read` | Get report sections |
| PATCH | `/reports/{report_id}/sections/{section_key}` | `reports:write` | Human edit section |
| POST | `/reports/{report_id}/publish` | `reports:write` | Publish after review |
| GET | `/reports/{report_id}/download` | `reports:read` | Presigned PDF/HTML URL |
| POST | `/reports/{report_id}/attest` | `reports:write` | Anchor hash on-chain (202) |

**POST report body:**

```json
{
  "report_type": "risk_assessment",
  "title": "Q2 2026 Risk Assessment — Acme Lending",
  "template_id": "risk_assessment_v2",
  "scope": {
    "deployment_ids": ["dep_uuid_1", "dep_uuid_2"],
    "include_resolved_findings": false,
    "date_range": { "from": "2026-01-01", "to": "2026-06-13" }
  },
  "options": {
    "ai_enhanced": true,
    "require_human_review": true,
    "include_executive_summary": true
  }
}
```

---

### 4.5.10 Webhooks

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/webhooks` | `webhooks:write` | List webhooks |
| POST | `/webhooks` | `webhooks:write` | Create webhook |
| PATCH | `/webhooks/{webhook_id}` | `webhooks:write` | Update |
| DELETE | `/webhooks/{webhook_id}` | `webhooks:write` | Delete |
| POST | `/webhooks/{webhook_id}/test` | `webhooks:write` | Send test event |

**Webhook payload signature:** `X-ChainSentinel-Signature: sha256=...` (HMAC-SHA256 of raw body)

**Subscribable events:**

- `scan.completed`
- `finding.created`
- `finding.status_changed`
- `risk.score_updated`
- `alert.triggered`
- `report.completed`
- `report.published`

---

### 4.5.11 Intelligence (Read-Only)

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/intel/lookup` | `findings:read` | Lookup address/selector/CVE |
| GET | `/intel/feeds` | `findings:read` | List active intel feeds & versions |

**GET `/intel/lookup?type=address&value=0x...&chain_id=1`**

---

### 4.5.12 Real-Time (SSE)

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/stream/alerts` | `alerts:read` | Server-Sent Events for org alerts |
| GET | `/stream/risk/{deployment_id}` | `risk:read` | Live risk score updates |

---

## 4.6 CI/CD Integration Endpoints

Designed for GitHub Actions / GitLab CI:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ci/scan` | Scan from git ref; returns pass/fail gate |
| GET | `/ci/scan/{scan_id}/gate` | Policy evaluation result |

**Gate response:**

```json
{
  "data": {
    "passed": false,
    "policy": "no-critical-open",
    "violations": [
      { "finding_id": "...", "severity": "critical", "title": "..." }
    ]
  }
}
```

---

## 4.7 GraphQL (Optional — Phase 3)

Single endpoint: `POST /graphql`

Primary use cases: dashboard aggregations, nested project → deployments → findings queries.

REST remains canonical for integrations; GraphQL is a read-optimized convenience layer.

---

## 4.8 Related Documents

- [System Architecture](./02-system-architecture.md) — Service mapping
- [Database Schema](./03-database-schema.md) — Entity definitions
- [Smart Contract Architecture](./05-smart-contract-architecture.md) — Attestation endpoint behavior
