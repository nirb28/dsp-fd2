## Design: Authentication, Authorization, and Audit Persistence (Control Tower + Front Door)

### 1) Scope and Goals
- **Control Tower (CT)**: Central authority for project manifests, module configuration, policy distribution, and governance.
- **Front Door (FD)**: Runtime ingress for client traffic to downstream AI services (RAG, inference, tools), enforcing **AuthN/AuthZ** and producing **auditable records**.
- **Gateway Audit Persistence**: FD (and/or the gateway layer in front of FD) must persist request/response evidence for compliance, forensic analysis, and non-repudiation—while respecting privacy and data minimization.

---

## 2) Actors and Trust Boundaries
- **External Client**: UI, service, automation, or agent calling the platform.
- **Front Door (FD)**: Application-level gateway (routing, orchestration, validations, policy calls).
- **Control Tower (CT)**: Policy/config management plane.
- **Downstream Services**: RAG server, model server, tool servers, etc.
- **Audit Store**: Append-friendly storage for audit events and optionally payload artifacts.
- **Identity Provider (IdP)**: Integrates with AD/GES.

---

## 3) Authentication (AuthN) Design

### 3.1 Supported AuthN Mechanisms
Recommended to support multiple mechanisms with a clear precedence order:

1. **JWT Bearer Tokens** (primary)
   - `Authorization: Bearer <token>`
   - Token validation checks:
     - signature (HS256/RS256, etc.)
     - `iss`, `aud`
     - `exp`, `iat` (+ leeway)
     - optional `nbf`
   - Token claims used downstream:
     - `sub` (principal id)
     - `roles` / `groups`
     - `scp` (scopes)
     - optional custom claims (e.g., `tenant`, `metadata_filter`)

### 3.2 Where AuthN Happens
Deployment patterns:

- **Pattern: FD-only AuthN**  
  FD validates token/key directly.  

---

## 4) Authorization (AuthZ) Design

### 4.1 Authorization Model
Use a layered model.

### 4.2 Policy Source of Truth (CT)
CT is responsible for:
- Defining **policy bundles** attached to manifests/modules:
  - allowed routes/actions
  - per-tenant constraints
  - allowed model/config names
  - data access constraints (labels, classification levels)
  - audit requirements (what to store, masking, retention)

CT distributes policies to FD (and optionally the gateway) via:
- periodic pull (FD polls CT)
- push on manifest changes (webhook/event)
- versioned policy bundles with signatures/checksums

### 4.3 Policy Enforcement Point (PEP)
- **PEP**: FD and/or gateway enforces allow/deny and applies obligations (masking, audit mode).


### 4.4 Authorization Flow (Typical Request)
1. Client calls FD (or gateway) with token.
2. AuthN validates token → principal + claims.
3. FD derives:
   - `tenant_id`
   - `roles/scopes`
   - requested resource (route, configuration name, model, tool)
4. FD evaluates policy:
   - allow/deny
   - obligations (e.g., “mask response fields”, “persist payload”, “redact PII”, “retain 30 days”)
5. FD forwards request to downstream with:
   - correlation id
   - principal context (minimized)
   - enforced filters (e.g., metadata filters merged with request filters)

---

## 5) Gateway Persistence of Request/Response for Audit

### 5.1 Audit Objectives
- **Traceability**: who did what, when, from where, against which resource.
- **Reproducibility** (bounded): enough evidence to reconstruct decisions without storing excessive sensitive data.
- **Non-repudiation**: tamper-evident logs and controlled access.
- **Compliance**: retention, legal hold, minimization, encryption, access logging.

### 5.2 What to Persist (Audit Event Schema)
Store **two layers**: (A) event metadata always, (B) payload artifacts conditionally.

**A. Always store (event metadata)**
- `timestamp`, `request_id` / `correlation_id`, `trace_id`
- `principal`: `sub`, `tenant`, `roles/scopes` (minimized)
- `client_ip`, `user_agent`
- `auth_context`: token issuer, key id, auth method, auth result
- `request`:
  - method, path, route id
  - query params (allowlist only)
  - selected headers (allowlist only)
- `authorization`:
  - policy version/hash
  - decision (allow/deny)
  - obligations applied
- `downstream`:
  - target service, upstream latency, retries
- `response`:
  - status code
  - response size
  - content-type
- `integrity`:
  - hash of payload artifact(s) if stored
  - signature/chain info if using tamper-evident log

**B. Conditionally store (payload artifacts)**
Controlled by policy and endpoint type:
- request body (raw or masked)
- response body (raw or masked)
- streaming transcripts (chunked capture) for LLM responses **only if allowed**
- attachments / documents references (usually store pointers + hashes, not full content)

### 5.3 Where Persistence Happens
Implementation:

- **FD persists (application-level audit middleware)**
  - Pros: full context (policy decisions, downstream routing), richer masking

### 5.4 Payload Handling: Masking, Minimization, and Streaming
- **Masking**: policy-driven redaction before persistence:
  - headers: `Authorization`, cookies always redacted
  - JSON body fields: `password`, `api_key`, `ssn`, `email` (configurable)
  - LLM prompts/completions: allow partial capture or hashed capture depending on sensitivity
- **Minimization**:
  - prefer storing **hashes** and **references** (document IDs, blob URIs) over raw content
  - store only an allowlist of headers/params
- **Streaming responses**:
  - store either:
    - final assembled text (if small and allowed), or
    - chunk hashes + timing, or
    - “transcript disabled” with metadata only  
  - ensure this does not materially increase latency; consider async write.

### 5.5 Storage Backends and Retention
- **Audit Event Store** (immutable/append-friendly):
  - Elasticsearch / OpenSearch index with ILM retention
  - or a WORM-capable object store for compliance exports
- **Payload Artifact Store**:
  - encrypted object storage (S3/Blob) with lifecycle rules
  - store `artifact_id`, `sha256`, `kms_key_id`, `retention_until`

Retention is policy-driven:
- default shorter retention for payloads (e.g., 7–30 days)
- longer retention for metadata (e.g., 90–365 days)
- legal hold overrides

### 5.6 Access Controls for Audit Data
- strict RBAC:
  - auditors can read
  - operators can read metadata but not payloads (optional)
  - developers typically denied in production
- all accesses to audit data are themselves audited

---

## 6) End-to-End Flows

### 6.1 Successful Request (JWT)
1. Client → FD: request with Bearer token
2. FD validates token (optional) and forwards
3. FD validates/trusts identity context
4. FD calls policy (embedded/external) → allow + obligations
5. FD forwards to downstream service
6. FD returns response
7. Audit persistence:
   - gateway writes edge event
   - FD writes enriched audit event + optional artifacts (async)

### 6.2 Denied Request (AuthZ)
1. AuthN succeeds, AuthZ fails (policy deny)
2. FD returns `403`
3. Audit persists:
   - decision + policy version + denied reason category (avoid leaking sensitive detail)

### 6.3 AuthN Failure
1. Token invalid/expired → `401`
2. Persist minimal audit event:
   - auth method, failure reason category, request metadata
   - never store raw token

