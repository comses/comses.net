# Airweave .cursor/rules Analysis

> Analysis of 20 `.mdc` rule files from the Airweave repository.
> Source: `.devcontext/airweave/.cursor/rules/`
> Date: 2026-03-02

---

## 1. The .mdc Format

Each rule file uses YAML frontmatter with three fields:

```yaml
---
globs: **/backend/**        # File patterns that trigger this rule
alwaysApply: false          # Whether to inject into every AI context
description: Optional text  # Human-readable purpose (rarely used)
---
```

**Key observations:**
- Only 1 of 20 files uses `alwaysApply: true` (the project overview)
- Glob patterns scope rules to relevant directories, reducing token waste
- Most files omit `description` — the H1 heading serves that purpose
- Some files have no frontmatter at all (relying on explicit invocation)

---

## 2. File-by-File Analysis

### Group 1: Architecture & Overview

#### `airweave-overview.mdc`
- **Globs:** `**/*` | **Always apply:** `true`
- **Purpose:** Establishes shared vocabulary and system mental model so the AI never misidentifies the codebase or its components.
- **Structure:** What is Airweave → Architecture → Technical Capabilities → Technology Implementation → For Developers
- **Key pattern:** Deliberately shallow and wide (~45 lines). Defines terms like "Monke", "Temporal workers", "ARF", "Qdrant" so the AI recognizes domain vocabulary. Technology choices (PostgreSQL, Qdrant, Redis) prevent the AI from suggesting alternatives.
- **Worth replicating:** The "base context" pattern — one cheap, always-loaded file that orients every interaction.

#### `sync-architecture.mdc`
- **Globs:** `**/sync/**` | **Always apply:** `false`
- **Purpose:** Documents the complete sync data-flow pipeline including concurrency model, component boundaries, and extension points.
- **Structure:** Core Principles → Component Deep Dive (9+ component cards) → Data Flow ASCII diagrams → Best Practices → Common Pitfalls
- **Key pattern:** Component card format (`### ComponentName` → Purpose → Fields → Key Methods). ASCII tree diagrams for 4 phases. "Why" annotations on non-obvious decisions (e.g., string markers instead of custom exceptions).
- **Worth replicating:** Inline code anchoring — every abstract claim backed by 5-15 line real code snippets.

#### `arf.mdc`
- **Globs:** none | **Always apply:** `false`
- **Purpose:** Minimal reference card for ARF storage — directory structure, key files, when capture happens.
- **Structure:** Directory tree → Key file paths → Usage trigger
- **Key pattern:** Only 28 lines. Demonstrates that not every rule needs to be exhaustive — compact reference cards work for simple subsystems.
- **Worth replicating:** Directory tree as schema — fastest way to communicate storage layout.

#### `mcp-server.mdc`
- **Globs:** `**/mcp/**` | **Always apply:** `false`
- **Purpose:** Documents dual-mode MCP server (stdio/HTTP) with session isolation, Redis-backed sessions, and auth.
- **Structure:** Deployment Modes comparison → Architecture Components → Redis Session Pattern (full code) → Auth Methods → Dev Guidelines
- **Key pattern:** Side-by-side comparison table for deployment modes. Full code block only where logic is non-trivial (Redis session management). Test file mapping removes ambiguity.
- **Worth replicating:** "Key Difference" bold callout blocks for critical architectural invariants.

### Group 2: Backend Core

#### `backend-rules.mdc`
- **Globs:** `**/backend/**` | **Always apply:** `false`
- **Purpose:** Master architectural overview for the entire backend — a "table of contents" rule.
- **Structure:** Core Layers (API → Service → Data Access → Domain) → Key Components → Data Flow traces → Style Rules → Code Principles → PostHog Analytics
- **Key pattern:** Numbered data-flow traces (HTTP in → auth → schema → handler → CRUD) give the AI the causal chain without reading code. Cross-references to other rule files rather than duplicating content.
- **Worth replicating:** The `short_name` global identifier convention called out as a system-wide invariant.

#### `api-layer.mdc`
- **Globs:** `**/api/**` | **Always apply:** `false`
- **Purpose:** Defines every convention for writing FastAPI endpoints — directory structure, auth, context injection, naming, error handling.
- **Structure:** ASCII directory tree → Endpoint Categories → Auth Methods (3 types) → Middleware Stack → Rate Limiter → Standard Endpoint Template → Naming Conventions → ✅/❌ CRUD Integration rules
- **Key pattern:** ✅/❌ anti-pattern callouts are binary and unambiguous. ApiContext inheritance chain documented to prevent wrong context types. Naming conventions as a lookup table (HTTP verb → method name).
- **Worth replicating:** The ✅/❌ format for do/don't rules. Naming convention tables.

#### `crud-layer.mdc`
- **Globs:** `**/crud/**` | **Always apply:** `false` | **Description:** present
- **Purpose:** Documents inheritance hierarchy, access control model, transaction management, and invariants of the CRUD layer.
- **Structure:** 3 Base Classes (when to use each) → BaseContext → Unit of Work → Standard Operations → Access Control → 4 Implementation Examples → Best Practices → Key Invariants → Common Gotchas
- **Key pattern:** "Common Gotchas" section preemptively corrects exact AI errors. "Key Invariants" as numbered hard rules. Special cases documented explicitly (CRUDOrganization doesn't inherit from base).
- **Worth replicating:** Gotchas/invariants sections that directly address likely AI mistakes.

#### `auth-providers.mdc`
- **Globs:** `**/auth_providers/**` | **Always apply:** `false`
- **Purpose:** Documents auth provider abstraction for third-party credential managers, token refresh lifecycle, proxy detection.
- **Structure:** Directory tree → Provider Registration (decorator pattern) → Field Mappings → TokenManager → Credential Priority (1-2-3) → Database Schema → Proxy Authentication
- **Key pattern:** Explicit credential priority ordering (numbered highest to lowest). Auto-detection flow documented as emergent behavior invisible from code alone.
- **Worth replicating:** Priority orderings for resolution chains.

### Group 3: Frontend & UX

#### `frontend-rules.mdc`
- **Globs:** `**/frontend/**` | **Always apply:** `false`
- **Purpose:** Comprehensive reference for the entire frontend architecture — stack, structure, patterns, conventions.
- **Structure:** Tech Stack → Project Structure → API Layer → State Management (5 stores) → Auth Flow (provider hierarchy) → Component Patterns → Real-Time (SSE) → Routing → Development Patterns → Performance/Security
- **Key pattern:** Provider hierarchy diagram is high-signal, low-token. "5 stores, each with a named responsibility" table. "Always use relative paths" as a precise anti-hallucination guard. Longest file (~340 lines).
- **Worth replicating:** Store/state ownership tables. Provider hierarchy diagrams.

#### `form-validation.mdc`
- **Globs:** `**/frontend/**` | **Always apply:** `false`
- **Purpose:** Documents custom validation system — philosophy, components, field-name auto-detection, debounce, visual feedback.
- **Structure:** Philosophy (1 sentence) → Core Components → Validation Rules catalog → Usage patterns → Field Type Detection table → Timing values → Visual Feedback → Implementation Notes
- **Key pattern:** "Minimal, non-intrusive, no success messages" as a one-liner design contract. Field-name-to-validator mapping table doubles as routing specification. "No success states" decision prevents AI from adding green checkmarks.
- **Worth replicating:** Philosophy one-liners as design contracts at the top of rules.

#### `feature-flags.mdc`
- **Globs:** none | **Always apply:** `false`
- **Purpose:** Cross-cutting reference for feature flags — backend Python API and frontend TypeScript API in one file.
- **Structure:** Overview (DB table, org-level scoping) → Backend Enum + CRUD → Frontend Zustand pattern → Adding New Flags (3-step checklist)
- **Key pattern:** Combining backend and frontend in one file for cross-cutting concerns. Numbered "Adding New Flags" checklist as a workflow specification.
- **Note:** File content is duplicated (lines 1-55 repeated at 57-111) — authoring artifact.

#### `fern-docs-generation.mdc`
- **Globs:** `**/fern/**` | **Always apply:** `false`
- **Purpose:** Architecture guide for custom Fern documentation generator — AST parsing to MDX output.
- **Structure:** 4-phase flow (Discovery → Parsing → Generation → Output) → Parser details (3-tier fallback) → MDX escaping rules → File structure → Execution command
- **Key pattern:** Pipeline phases as top-level organizing principle. MDX escape rules as a bug-prevention checklist. Highest-value rule in group — documents bespoke tooling no pre-trained model could know.
- **Worth replicating:** Pipeline phase diagrams for any multi-step process.

### Group 4: Connectors & Integrations

#### `source-connector-implementation.mdc`
- **Globs:** none | **Always apply:** not specified (no frontmatter)
- **Purpose:** Comprehensive reference manual for building a production-ready source connector.
- **Structure:** Part 1: Entity Schemas → Part 2: Source Implementation → Part 3: OAuth Config → Part 3.5/3.75: Auth Config / Federated Search → Part 4: Advanced Topics → Part 5: Testing checklist (27 items)
- **Key pattern:** Negative example + positive example pairs (Common Mistake in red → correct pattern). Inline rationale comments in code (`# ✅ Enables "who" searches`). ⚠️ IMPORTANT/CRITICAL severity signaling. 27-item validation checklist.
- **Worth replicating:** Red/green example pairs. Self-audit checklists at the end.

#### `connector-development-end-to-end.mdc`
- **Globs:** none | **Always apply:** not specified (no frontmatter)
- **Purpose:** Master workflow guide sequencing all phases of connector development.
- **Structure:** Phase 1: Research → Phase 2: Implementation → Phase 3: E2E Testing → Phase 4: Debugging (issue-response pairs) → Phase 5: Production Checklist → Phase 6: Submission
- **Key pattern:** Phased structure with named checkpoints. Explicit human-AI boundary statements ("Inform the human... Wait for feedback"). Debugging as issue-response table, not generic advice.
- **Worth replicating:** Human-AI boundary markers. Phased workflow with checkpoints.

#### `connector-cursors.mdc`
- **Globs:** `**/sync/**,**/sources/**` | **Always apply:** `false`
- **Purpose:** Documents typed cursor system for incremental sync.
- **Structure:** Overview → Lifecycle (4-step numbered flow) → 3 Named Patterns (single, multiple, composite) → Complete Example → Best Practices → Responsibility Split
- **Key pattern:** Lifecycle diagram as entry point. Pattern taxonomy with named variants (complexity progression). "System does X / Sources do Y" responsibility split.
- **Worth replicating:** Named pattern variants at increasing complexity levels.

#### `integrations-yaml.mdc`
- **Globs:** `**/yaml/**` | **Always apply:** `false`
- **Purpose:** Documents all variants of OAuth YAML configuration with real-world examples.
- **Structure:** Annotated full schema → 7 provider examples (Gmail, Airtable, Excel, Word, Teams, Google Docs, Trello) → Template URLs (Zendesk) → Folder structure
- **Key pattern:** Abstract schema first, examples second. Real-world complete examples with actual OAuth endpoint URLs. Embedded explanation for non-obvious behavior (PKCE flow).
- **Worth replicating:** Schema-then-examples structure for configuration formats.

### Group 5: Infrastructure & Testing

#### `monke.mdc`
- **Globs:** `**/monke/**` | **Always apply:** `false`
- **Purpose:** Reference for the Monke E2E testing framework — architecture, terminology, conventions.
- **Structure:** Core Architecture → Test Flow (14-step lifecycle) → Bongos (abstract base class) → Configuration YAML → Auth → Content Generation → Verification (4 types) → CLI → Adding Connectors (5-step) → Common Pitfalls (4 failure patterns)
- **Key pattern:** Type-prefixed IDs for collision avoidance. Troubleshooting as first-class content (4 failure modes with problem/symptoms/solution).
- **Worth replicating:** Failure mode documentation with structured diagnosis.

#### `monke-testing-guide.mdc`
- **Globs:** none (no frontmatter)
- **Purpose:** Step-by-step implementation guide for building a complete Monke test with full boilerplate.
- **Structure:** Core Invariant (entity count matching) → 4 Required Files → Bongo Implementation (full skeleton) → Schemas + Generation → Config YAML → Verification Deep Dive → Best Practices (5 patterns) → Running Tests → Failure Modes → Checklist
- **Key pattern:** "Human Task" vs "AI Agent task" role separation labels. `{short_name}` template variable convention. Self-auditing count-matching invariant. Token-presence assertion pattern.
- **Worth replicating:** Role separation labels. Template variable conventions. Self-auditing patterns.

#### `search-module.mdc`
- **Globs:** `**/search/**,**/search.py` | **Always apply:** `false`
- **Purpose:** Comprehensive reference for the modular search architecture — HTTP endpoint to Qdrant query to analytics.
- **Structure:** Pipeline diagram → 7-step Request Flow → API Endpoints (4, with deprecation status) → Schemas → 9 Search Operations → Hybrid Search (RRF) → Federated Search (8-step) → Temporal Relevance (scoring formula) → Config Defaults → Provider Capability Matrix → 10 Critical Gotchas → Persistence → Best Practices → Module Structure → Quick Reference
- **Key pattern:** Pipeline architecture diagram before any code. 10 numbered gotchas as the highest-density mistake-prevention section. Provider capability matrix. Legacy schema migration field-mapping table.
- **Worth replicating:** Numbered gotchas. Capability matrices. Migration mapping tables.

#### `stripe-billing.mdc`
- **Globs:** `**/billing/**` | **Always apply:** `false`
- **Purpose:** Complete reference for Stripe billing — payment models, state transitions, webhooks, upgrade/downgrade matrix.
- **Structure:** Overview (2 modes, 3 principles) → Architecture → Data Model → 9 Endpoints → Monthly vs Yearly (with cent amounts) → Business Rules → 4 Orchestration Flows → 6 Webhook Events → 13-case Transition Matrix → Frontend Integration → Plan Limits → Operational Notes → Extensibility Checklist
- **Key pattern:** 13-case transition decision matrix as named examples. "DB is source of truth" as an explicit invariant when systems diverge. Amounts in cents with math shown (derivable, not magic numbers).
- **Note:** Content duplicated from line 216 onwards — authoring artifact.
- **Worth replicating:** Exhaustive transition matrices. Math shown for derived values.

---

## 3. Cross-Cutting Patterns

### 3.1 Structural Template

Most effective rules follow this meta-structure:

```
1. Overview (what the thing is, 1-3 sentences)
2. Architecture (which file owns which concern)
3. Data model / key types
4. API surface or usage patterns
5. Core algorithms or workflows
6. External system behavior / quirks
7. Common mistakes / gotchas
8. Extension procedure ("how to add X")
9. Quick reference / examples
```

### 3.2 What Makes Rules Effective for AI

| Technique | Effect | Used By |
|-----------|--------|---------|
| ✅/❌ anti-pattern callouts | Binary, unambiguous guidance | api-layer, crud-layer |
| Negative + positive example pairs | Teaches what NOT to do | source-connector, monke |
| Component cards (Name → Purpose → Fields → Methods) | Scannable reference | sync-architecture |
| ASCII directory trees | Navigate without searching | all backend/frontend rules |
| Named file paths for every component | Eliminates search time | all 20 files |
| Numbered gotchas | Highest-density mistake prevention | search-module (10), crud-layer (6) |
| Philosophy one-liners | Design contracts that prevent scope creep | form-validation |
| Pipeline/lifecycle diagrams | Mental model before code | sync, search, connectors |
| Template variables (`{short_name}`) | Generalize examples across instances | monke, connectors |
| "Human Task" labels | Role separation | monke-testing-guide |
| Priority orderings (1-2-3) | Resolution chain clarity | auth-providers |
| Self-audit checklists | AI validates its own output | source-connector (27 items) |

### 3.3 Glob Strategy

| Pattern | Scope | Files Using It |
|---------|-------|----------------|
| `**/*` + `alwaysApply: true` | Every file — base context | 1 file (overview) |
| `**/backend/**` | Broadest layer scope | 1 file (backend-rules) |
| `**/api/**`, `**/crud/**` | Narrower layer scope | 2 files |
| `**/specific-dir/**` | Subsystem scope | 8 files |
| `**/dir1/**,**/dir2/**` | Multi-directory scope | 2 files |
| No globs | Manual invocation only | 6 files |

Design principle: Broader rules are shallower (orientation). Narrower rules are deeper (implementation detail). Cross-cutting concerns often have no glob because no single pattern captures both backend and frontend.

### 3.4 Content Length Distribution

- **Minimal** (~30 lines): `arf.mdc` — simple subsystems need reference cards, not essays
- **Standard** (100-200 lines): Most rules — enough for architecture + examples + gotchas
- **Comprehensive** (300+ lines): `frontend-rules.mdc`, `source-connector-implementation.mdc`, `search-module.mdc` — complex subsystems with many conventions

### 3.5 Authoring Weaknesses Observed

- 2 files have duplicated content (copy-paste artifacts): `feature-flags.mdc`, `stripe-billing.mdc`
- 6 files have no frontmatter at all — reduces discoverability and auto-activation
- Most files omit the `description` field — minor issue since H1 serves the purpose
- No files contain explicit cross-reference links to related rules (relationships are implicit)

---

## 4. Gap Analysis: CoMSES.net-Specific Rules

### 4.1 Rules That Map to Airweave Equivalents (Rewrite Needed)

| # | Proposed File | Maps From | Key Differences |
|---|--------------|-----------|-----------------|
| 1 | `comses-overview.mdc` | `airweave-overview.mdc` | Django/Wagtail/Vue/ES7/PostGIS stack; 5 apps; hybrid rendering; Docker secrets; runit |
| 2 | `django-backend-rules.mdc` | `backend-rules.mdc` | Layered settings; Jinja2 primary; camelCase middleware; `read_secret()`; sync not async |
| 3 | `drf-api-layer.mdc` | `api-layer.mdc` | `CommonViewSetMixin`; dual HTML+JSON renderer; `RootContextHTMLRenderer`; view class hierarchy |
| 4 | `permissions-and-auth.mdc` | `auth-providers.mdc` | `ComsesObjectPermissionBackend`; guardian; `ComsesGroups` enum; allauth social |
| 5 | `vue-frontend-rules.mdc` | `frontend-rules.mdc` | Vue 3 + Bootstrap 5 (not React/Tailwind); multi-entry Vite; `useAxios`; CSRF from cookie |
| 6 | `django-vue-hybrid-rendering.mdc` | (split from frontend+backend) | `extractDataParams()`; `data-*` bootstrapping; only release editor uses Router+Pinia |
| 7 | `testing-patterns.mdc` | `monke.mdc` + guide | Django `TestCase`; Cypress E2E; permission test base; library test base |
| 8 | `elasticsearch-search.mdc` | `search-module.mdc` | ES 7 via Wagtail search; `index.Indexed` mixin; `max_result_window: 2500`; `ArchivedQueryHits` |

### 4.2 Fully Custom Rules (No Airweave Equivalent)

| # | Proposed File | Glob Pattern | What It Teaches the AI |
|---|--------------|-------------|----------------------|
| 9 | `wagtail-cms.mdc` | `**/home/**,**/*page*.py` | Page models, `NavigationMixin`, `content_panels`, StreamFields, snippets, `SiteSettings`, page tree |
| 10 | `peer-review-workflow.mdc` | `**/review/**` | `ReviewStatus` states, `PeerReviewEvent` log, tri-state invitation, `set_complete_status()` cascade, email templates |
| 11 | `bagit-archival.mdc` | `**/bagit/**,**/fs.py` | `StagingDirectories` (originals/sip/aip), `FileCategoryDirectories`, MIME validation, `X-Accel-Redirect` |
| 12 | `datacite-doi.mdc` | `**/datacite/**,**/doi*` | `DataCiteApi` wrapper, env-aware dry-run, `DataCiteRegistrationLog`, `codemeticulous` for CodeMeta/CFF |
| 13 | `discourse-sso.mdc` | `**/discourse/**` | HMAC-SHA256 handshake, `sanitize_username()`, return payload params, `create_discourse_user()` |
| 14 | `tag-curation.mdc` | `**/tag*/**` | `TagCleanup` staging, `TagMigrator`, `get_through_tables()`, ML clustering via `dedupe`, Wagtail admin hooks |
| 15 | `spam-moderation.mdc` | `**/spam*` | `ModeratedContent` mixin, honeypot `content` field, timing threshold (3s), `SpamCatcherSerializerMixin` |
| 16 | `invoke-operational-tasks.mdc` | `**/tasks.py,**/invoke*` | Borg backup, DB dump/restore, ES management, `docker-compose.yml` is generated never hand-edited |
| 17 | `conference-management.mdc` | `**/conference/**` | `ConferencePage`, `ConferenceSubmission`, `setup_conference` command, submission view email flow |

### 4.3 Airweave Rules to Drop (No CoMSES Equivalent)

These 10 airweave rules cover concepts absent from CoMSES.net:
- `sync-architecture.mdc` (Temporal workers)
- `arf.mdc` (raw format storage)
- `mcp-server.mdc` (MCP protocol)
- `source-connector-implementation.mdc` (connector framework)
- `connector-development-end-to-end.mdc` (connector workflow)
- `connector-cursors.mdc` (incremental sync cursors)
- `integrations-yaml.mdc` (OAuth YAML config)
- `fern-docs-generation.mdc` (Fern MDX generator)
- `crud-layer.mdc` (custom CRUD base classes — Django ORM handles this)
- `stripe-billing.mdc` (no billing in CoMSES)

`feature-flags.mdc` content can be folded into `django-backend-rules.mdc` (django-waffle is just middleware/decorator).

---

## 5. Summary Statistics

| Metric | Value |
|--------|-------|
| Total airweave rule files | 20 |
| Files with `alwaysApply: true` | 1 |
| Files with glob patterns | 12 |
| Files with no frontmatter | 6 |
| Files with duplicate content (bugs) | 2 |
| Proposed CoMSES rules (remapped) | 8 |
| Proposed CoMSES rules (custom) | 9 |
| **Total proposed CoMSES rules** | **17** |
| Airweave rules to drop | 10 |
