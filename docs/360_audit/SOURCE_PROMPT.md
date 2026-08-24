Act as a **principal software architect, senior full-stack engineer, AI/RAG engineer, PostgreSQL/data engineer, security reviewer, QA engineer, DevOps engineer, product engineer, documentation engineer, and technical interviewer**.

I need a **complete 360-degree evidence-based audit of this entire project** so that I can understand exactly:

- what this project is,
- what technologies it uses,
- why each technology is used,
- how every major component works,
- how data travels through the system,
- what database data is used,
- what AI/RAG architecture is implemented,
- what workflows exist,
- what is genuinely dynamic versus hardcoded,
- what is strong,
- what is weak,
- what is unfinished,
- what is risky,
- what is redundant,
- what is overengineered,
- what is underengineered,
- what can be improved,
- what should NOT be changed,
- what would make this project production-quality,
- and how I should explain the project clearly to interviewers.

This pass is an **AUDIT ONLY**.

# ABSOLUTELY DO NOT REFACTOR OR MODIFY THE PROJECT YET

Do not:

- reorganize directories,
- rename files,
- delete files,
- move components,
- rewrite frontend code,
- change APIs,
- change SQL,
- change schemas,
- change RAG behavior,
- change Ollama models,
- alter workflow logic,
- modify billing/tender code,
- install unnecessary packages,
- “clean up” code just because it looks old.

First establish evidence.

Any future modification must be based on the audit.

---

# GOLDEN RULE: NO HALLUCINATION

Every claim must come from actual evidence in:

- source code,
- configuration,
- SQL,
- database schema,
- API routes,
- React components,
- runtime scripts,
- package manifests,
- tests,
- logs,
- documentation,
- generated artifacts,
- or observed application/runtime behavior.

For important findings, cite:

```text
file path
class/function/component/route/table
relevant line or code area
why it proves the claim
```

If something cannot be verified, explicitly write:

```text
NOT VERIFIED
```

If something exists only in documentation but cannot be confirmed from code, write:

```text
DOCUMENTED BUT NOT VERIFIED IN IMPLEMENTATION
```

If something exists in source but has not been runtime-tested, write:

```text
IMPLEMENTED BUT NOT RUNTIME-VERIFIED
```

Never guess.

---

# IMPORTANT DOCUMENTATION RULE

Some project documents may be historical.

Determine which documentation is:

```text
CURRENT SOURCE OF TRUTH
HISTORICAL
STALE
PARTIALLY CORRECT
CONTRADICTORY
```

Do not treat old evaluation reports as current runtime evidence.

Cross-check documentation against the actual source code.

---

# PHASE 1 — PROJECT INVENTORY

Start by creating a complete project inventory.

Inspect:

```text
root files
Python source
React source
CSS
configuration
environment template
PowerShell/batch launchers
tests
database/migration code
billing artifacts
tender workflow files
RAG corpus logic
generated/runtime artifacts
documentation
```

Produce a project tree that distinguishes:

```text
SOURCE CODE
CONFIGURATION
DATA
MODEL ARTIFACTS
GENERATED OUTPUT
RUNTIME STATE
TESTS
DOCUMENTATION
LEGACY/HISTORICAL
```

For every major directory explain:

```text
What it contains
Why it exists
Whether it is required at runtime
Whether it is source or generated
Who/what depends on it
Whether it should remain where it is
```

Do not simply print `tree`.

Explain the architecture represented by the tree.

---

# PHASE 2 — TECHNOLOGY STACK

Identify the actual technology stack from manifests and code.

For every technology create:

```text
Technology
Where used
Why used
What problem it solves
What depends on it
Whether it runs locally/offline
Alternatives
Whether replacing it is justified
```

Cover at minimum:

```text
React
Vite
TypeScript
FastAPI
Python
PostgreSQL
pgvector
pgcrypto
Ollama
embedding model
generation model
CrossEncoder/reranker
PDF extraction libraries
OCR adapters
table extraction
XGBoost/billing artifacts
PowerShell launcher
pytest
ruff
```

Do not list a technology unless it exists in the actual project.

---

# PHASE 3 — HIGH-LEVEL ARCHITECTURE

Reverse-engineer the actual architecture.

Produce a diagram such as:

```text
Browser
   ↓
React/Vite
   ↓
API
   ↓
FastAPI
   ├── Authentication
   ├── Dashboard
   ├── Tenant mappings
   ├── RAG
   ├── Agenda workflow
   ├── Billing
   └── Tender
        ↓
PostgreSQL / pgvector

FastAPI
   ↓
Ollama

FastAPI
   ↓
Reranker

FastAPI
   ↓
Local artifacts/files where applicable
```

But use actual architecture discovered in the project.

Explain the responsibility of every layer.

---

# PHASE 4 — COMPLETE DATA-FLOW ANALYSIS

Trace data end-to-end for every major use case.

Do not simply name modules.

Trace:

```text
USER ACTION
→ React handler
→ API request
→ FastAPI route
→ validation
→ authorization
→ service/function
→ database/model/file
→ processing
→ API response
→ React state
→ rendered UI
```

Create separate flows for:

```text
Authority login
Tenant login
Dashboard metrics
Tenant table
New conversation
Existing conversation
RAG question
Citation generation
Document ingestion
Document management
Agenda creation
Agenda handoff
Agenda AI thread
Billing forecast
Tender publication
Logout
```

For each flow identify:

```text
Frontend file/component
Endpoint
Backend function/service
Tables/data source
Writes performed
External/local dependencies
Failure states
Permission rules
```

---

# PHASE 5 — DATABASE AUDIT

Inspect the actual database access/migration/query code.

Document separately:

```text
public.*
rag.*
pms_doc.*
pms_vector.*
other persistence such as JSON
```

For every application-owned important table document:

```text
table name
purpose
key columns
primary key
foreign keys
indexes
vector indexes
write owner
read owner
retention/lifecycle
security implications
```

For source PMS tables document:

```text
which features read them
whether application modifies them
what identifiers are used
known missing/legacy data limitations
```

Explicitly distinguish:

```text
unique tenant
applicant
tenant-property mapping
tenancy
property
plot
agenda owner
portal user
```

Do not merge business concepts simply because they have similar names.

---

# PHASE 6 — DATA QUALITY AUDIT

Check actual handling of:

```text
NULL
N/A
missing identifiers
historical dates
duplicate records
invalid dates
default/sentinel values
multiple mappings
units
status mappings
schema inconsistencies
```

Determine whether UI/API terminology accurately represents the source data.

Check particularly whether dashboard totals and tenant-table totals describe:

```text
unique entities
mapping rows
active records
historical records
```

Flag any semantic inconsistency.

Do not “correct” historical source values without evidence.

---

# PHASE 7 — RAG SYSTEM DEEP AUDIT

This must be extremely detailed.

Trace:

```text
document
→ inspection
→ extraction
→ OCR decision
→ table processing
→ quality decision
→ chunking
→ embedding
→ persistence
→ query embedding
→ lexical retrieval
→ vector retrieval
→ ACL
→ fusion
→ reranker
→ parent context
→ context-budget construction
→ LLM
→ citation verification
→ answer
```

For every stage determine:

```text
implementation file
algorithm
configuration
input
output
data stored
failure behavior
validation
metric available
metric missing
```

---

# PHASE 8 — CHUNKING AUDIT

Answer specifically:

```text
Which chunking method is actually implemented?
Is it fixed-size, page-level, recursive, semantic, hierarchical, parent-child, etc.?
What chunk size is configured?
What overlap is configured?
Does it preserve page lineage?
Does it preserve headings?
Does it preserve tables?
Does it remove headers/footers?
Does it create parent context?
How are chunk IDs generated?
Where are chunks stored?
How are duplicate documents/chunks handled?
```

Do not use generic RAG terminology unless the code proves it.

---

# PHASE 9 — EMBEDDING AUDIT

Determine:

```text
exact embedding model
runtime
endpoint
vector dimension
batch behavior
storage type
index type
similarity metric
dimension validation
failure handling
```

Explain why this embedding approach is suitable or unsuitable for the corpus.

Do not recommend another embedding model until the current implementation and evaluation evidence are understood.

---

# PHASE 10 — RETRIEVAL AUDIT

Analyze:

```text
lexical retrieval
dense vector retrieval
candidate limits
RRF
ACL filtering
reranking
parent-context construction
context token budget
query rewriting if any
metadata filtering
document filtering
```

Explain mathematically/conceptually how the retrieval pipeline ranks evidence.

Identify where recall may be lost.

Identify where precision may be lost.

---

# PHASE 11 — RERANKER AUDIT

Determine:

```text
model
location
input
candidate count
score handling
fallback behavior
startup dependency
runtime cost
```

Explain:

```text
why reranking is used
what improvement it is intended to provide
what happens when it fails
```

---

# PHASE 12 — GENERATION / LLM AUDIT

Determine:

```text
which model is default
which models are user-selectable
how Ollama is called
prompt structure
system instructions
context format
citation instructions
temperature/options
timeout
failure handling
```

Determine whether generated answers are:

```text
grounded
validated
retried
rejected when unsupported
```

Identify any pathway where hallucinated factual content could still reach the UI.

---

# PHASE 13 — CITATION AUDIT

Trace exactly how:

```text
retrieved chunk
→ page metadata
→ source
→ generated citation
→ validation
→ frontend citation
```

Determine:

```text
whether page references are real
whether sources can mismatch generated statements
whether citation validation checks every factual paragraph
whether source chips are clickable
whether duplicate citations are handled
```

Document known limitations.

---

# PHASE 14 — ACL / MULTI-ROLE RAG SECURITY

Audit:

```text
authority
tenant
DO
NO
HO
```

and all other actual roles.

Determine:

```text
what evidence each role can retrieve
where ACL is applied
whether filtering happens before or after vector search
whether unauthorized chunks can enter the LLM context
whether conversations are owner-scoped
whether API routes enforce permissions independently from frontend UI
```

Security must never depend only on hidden UI controls.

---

# PHASE 15 — DOCUMENT INGESTION QUALITY

Audit handling of:

```text
native text PDF
scanned PDF
mixed PDF
tables
multi-column layouts
bad extraction
duplicate PDF
unsupported PDF
encrypted PDF
very large PDF
low-quality OCR
```

Determine which capabilities are:

```text
fully operational
optional
unavailable
quarantined
```

Do not claim OCR works just because an adapter exists.

---

# PHASE 16 — RAG EVALUATION QUALITY

Determine what is ACTUALLY measured today.

Look for:

```text
Recall@K
Precision@K
MRR
NDCG
reranker metrics
citation accuracy
answer faithfulness
answer relevance
context precision
context recall
latency
token usage
retrieval timing
generation timing
```

Classify each metric:

```text
Measured
Implemented but not run
Historical only
Not implemented
```

If current RAG quality cannot be quantitatively proven, say so clearly.

Then propose an evidence-based evaluation set design using reviewed real documents/questions.

Do not invent evaluation scores.

---

# PHASE 17 — AUTHENTICATION & SECURITY AUDIT

Trace:

```text
login
password verification
legacy password behavior
rate limiting
session creation
cookie attributes
session storage
expiry
logout
role validation
authorization
CORS
SQL parameterization
secret storage
```

Threat-model at minimum:

```text
SQL injection
prompt injection
cross-tenant leakage
cross-role leakage
session theft
CSRF
XSS
credential exposure
unsafe file upload
path traversal
model prompt leakage
destructive requests
```

For every finding state:

```text
severity
evidence
realistic exploit condition
recommended remediation
```

Distinguish local-only risk from external-deployment risk.

---

# PHASE 18 — FRONTEND AUDIT

Map actual frontend architecture.

Identify:

```text
application shell
authentication
Dashboard
Tenants
AI Assistant
Workflow
Billing modal
Tender modal
shared components
CSS architecture
splitters
responsive behavior
state management
API client logic
```

Specifically inspect whether large files are becoming maintenance risks.

Do NOT automatically split them.

Instead propose safe feature boundaries.

For every extraction recommendation state:

```text
component boundary
dependencies
risk
tests required before extraction
recommended priority
```

---

# PHASE 19 — UI/UX AUDIT

Audit from the perspective of:

```text
normal Authority user
Data Entry Operator
Nodal Officer
HOD
Tenant
administrator/developer
```

Check:

```text
information hierarchy
terminology
empty states
loading states
error states
permissions
disabled-state explanations
responsive design
100% browser zoom
accessibility
keyboard navigation
table usability
chat usability
workflow usability
citation visibility
```

Identify internal technical terms that should not be exposed to ordinary users.

Examples may include:

```text
raw enum names
RAG jargon
context capsule terminology
model names
database terminology
```

Only flag terms that actually exist.

---

# PHASE 20 — DASHBOARD AUDIT

Verify every KPI and chart.

For every metric answer:

```text
UI label
API field
SQL source
table(s)
aggregation
unit
business meaning
whether unique or mapping count
whether tests cover it
```

Look for semantic inconsistencies such as:

```text
tenant vs tenancy
status vs tenancy type
occupied vs approved
registered vs pending
acre/hectare/sq.m conversions
mapping count vs unique-entity count
```

Do not assume the UI label is correct merely because the query returns a number.

---

# PHASE 21 — TENANT TABLE AUDIT

Audit:

```text
data source
record meaning
search
filters
sorting
pagination
page-size
server/client responsibilities
historical dates
N/A handling
long values
permissions
performance
```

Determine whether the table represents:

```text
unique tenants
tenant-property mappings
applicants
tenancies
```

and ensure documentation uses the correct term.

---

# PHASE 22 — WORKFLOW / AGENDA AUDIT

Reverse-engineer the actual state machine.

Produce:

```text
state
owner role
allowed actions
target state
required recipient
conditions
database writes
audit/history writes
```

Trace:

```text
private cited chat
→ agenda draft
→ DO
→ NO
→ HO
→ approval/rejection/return
```

Use actual implemented roles/states.

Explain:

```text
who can create an agenda
why citations are required
how official versions work
how context/evidence snapshots work
how ownership changes
why chats become undeletable when workflow-linked
```

---

# PHASE 23 — BILLING FORECAST AUDIT

Trace end-to-end:

```text
UI
→ tenancy selector
→ prefill
→ source tables/files
→ rates
→ model artifact
→ prediction
→ formula layer
→ chat
→ audit
```

Document:

```text
model type
training data
runtime artifact
features
target
formula layer
runtime dependencies
manual inputs
source-backed values
fallback logic
validation
writes
```

Determine whether current model quality is actually known.

Separate:

```text
ML prediction
business formula calculation
```

Do not call a calculation an ML prediction if it is deterministic.

---

# PHASE 24 — TENDER PUBLICATION AUDIT

Trace:

```text
eligible plot
→ source evidence
→ checklist
→ proposal inputs
→ calculations
→ LAC
→ workflow state
→ board note
→ tender
→ publication
```

Determine:

```text
what is sourced
what is manually entered
what is calculated
what is approved
what is persisted
what is generated
```

Audit JSON workflow persistence and concurrency implications.

Do not recommend PostgreSQL migration without explaining benefit, cost, migration risk, and deployment requirement.

---

# PHASE 25 — API AUDIT

Generate an endpoint map.

For every route document:

```text
method
path
authentication
authorization
request
response
service
database/file dependencies
writes
errors
frontend consumer
tests
```

Identify:

```text
duplicate aliases
version inconsistencies
unused routes
missing validation
inconsistent errors
```

Do not remove compatibility routes during this audit.

---

# PHASE 26 — CONFIGURATION AUDIT

Document every meaningful configuration group:

```text
database
schemas
ports
Ollama
models
retrieval
reranking
chunking
embedding
session
security
ingestion
billing
tender
```

Classify settings:

```text
required
optional
safe default
dangerous default
local-development only
production-sensitive
```

Never include secret values.

---

# PHASE 27 — RUNTIME / OPERATIONS AUDIT

Trace actual startup:

```text
launcher
→ port checks
→ backend
→ migration
→ AI initialization
→ readiness
→ frontend
```

Document:

```text
5173
8001
5432
11434
```

only if these are confirmed by source.

Explain:

```text
/health
/health/ready
```

and what failure at each dependency looks like.

---

# PHASE 28 — DEPENDENCY AUDIT

Check:

```text
Python packages
Node packages
optional training packages
unused dependencies
duplicate libraries
version conflicts
security-sensitive dependencies
generated package-lock
editable installation
```

Do not remove anything just because static search does not immediately show usage.

Classify:

```text
runtime
development
training-only
optional
apparently unused — requires verification
```

---

# PHASE 29 — TEST AUDIT

Map all tests to features.

Create a matrix:

```text
Feature
Unit test
Integration test
Live test
UI/E2E test
Missing coverage
```

Cover:

```text
auth
dashboard
tenants
ingestion
retrieval
citation validation
ACL
chat
workflow
billing
tender
security
frontend
```

Identify critical behavior with no automated regression protection.

---

# PHASE 30 — OBSERVABILITY AUDIT

Check:

```text
logs
audit events
startup logs
API errors
AI latency
retrieval timing
generation timing
handoff events
billing audits
tender events
```

Determine what an operator can diagnose when something fails.

Recommend improvements only where an actual observability gap exists.

---

# PHASE 31 — PERFORMANCE AUDIT

Identify likely bottlenecks based on actual architecture.

Check:

```text
database queries
vector search
lexical search
reranker
Ollama generation
embedding calls
dashboard queries
tenant pagination
large React rendering
billing
tender PDFs
```

Do not optimize without evidence.

Classify:

```text
measured bottleneck
likely bottleneck
not measured
```

---

# PHASE 32 — FAILURE-MODE ANALYSIS

For every major subsystem answer:

```text
What if PostgreSQL is unavailable?
What if Ollama is unavailable?
What if reranker fails?
What if embedding model is missing?
What if corpus has no evidence?
What if citation validation fails?
What if invalid workflow transition occurs?
What if tender JSON is corrupted?
What if billing artifact is missing?
What if UI loses backend connection?
```

Document graceful degradation and missing handling.

---

# PHASE 33 — MAINTAINABILITY AUDIT

Identify:

```text
large files
god modules
tight coupling
duplicate code
duplicate CSS
raw SQL concentration
cross-feature dependencies
magic strings
status duplication
configuration duplication
legacy compatibility code
generated files mixed with source
```

For every recommendation give:

```text
Evidence
Benefit
Risk
Effort
Tests required
Whether to do now or later
```

No speculative “clean architecture” rewrite.

---

# PHASE 34 — FILE STRUCTURE AUDIT

Judge the current structure before proposing a new one.

Create:

```text
CURRENT STRUCTURE
GOOD AS IS
SHOULD EVENTUALLY MOVE
GENERATED OUTPUT
LEGACY/HISTORICAL
HIGH-RISK TO MOVE
```

Then propose a **future target structure**, but DO NOT apply it.

For each proposed move explain:

```text
why
dependency impact
import/path impact
runtime impact
test requirement
migration sequence
```

---

# PHASE 35 — DOCUMENTATION AUDIT

Identify:

```text
current docs
historical docs
missing docs
duplicate docs
contradictory docs
stale docs
```

Determine which file should be the source of truth for:

```text
architecture
setup
operations
API
RAG
database
workflow
billing
tender
testing
security
deployment
interview explanation
```

Do not rewrite documentation yet.

Create the recommended documentation architecture first.

---

# PHASE 36 — INTERVIEWER EXPLANATION

Create an interview-ready explanation containing:

```text
30-second explanation
2-minute explanation
5-minute explanation
deep technical explanation
```

Answer:

```text
What problem does the system solve?
Who uses it?
What is the architecture?
Why FastAPI?
Why React?
Why PostgreSQL?
Why pgvector?
Why Ollama?
Why hybrid retrieval?
Why reranking?
How do you prevent hallucination?
How do you protect tenant/role data?
How does agenda workflow work?
How does billing work?
How does tender publication work?
What engineering challenges did you solve?
What are the current limitations?
What would you improve next?
```

Do not exaggerate features.

---

# PHASE 37 — FEATURE MATURITY MATRIX

Create a table for every major feature:

```text
Feature
Implemented
Runtime verified
Automated tests
Security reviewed
Documented
Production ready
Known limitations
```

Use statuses:

```text
YES
PARTIAL
NO
NOT VERIFIED
```

Never infer `YES`.

---

# PHASE 38 — PRODUCTION READINESS SCORECARD

Assess separately:

```text
Architecture
Code organization
RAG quality
Data correctness
Security
Authentication
Authorization
Database
Reliability
Observability
Testing
Frontend UX
Accessibility
Performance
Documentation
Deployment
Backup/recovery
```

Give a score only when evidence exists.

For every score give justification.

Do not give a meaningless overall 95/100 score.

---

# PHASE 39 — TECHNICAL DEBT REGISTER

Create a technical debt table:

```text
ID
Finding
Evidence
Severity
User impact
Engineering impact
Risk if ignored
Recommended action
Effort
Dependencies
Priority
```

Use:

```text
P0 Critical
P1 High
P2 Medium
P3 Low
```

---

# PHASE 40 — IMPROVEMENT OPPORTUNITY MATRIX

Separate improvements into:

```text
MUST FIX
SHOULD FIX
NICE TO HAVE
DO NOT CHANGE NOW
REQUIRES BUSINESS DECISION
REQUIRES PRODUCTION DECISION
```

For each improvement provide:

```text
Problem
Evidence
Why improve
Expected benefit
Risk
Complexity
Files affected
Testing required
```

---

# PHASE 41 — DO NOT OVERENGINEER

Explicitly identify improvements that sound impressive but are unnecessary for this project.

Examples may include:

```text
microservices
Kubernetes
graph RAG
agent framework
Kafka
Redis
LangChain/LlamaIndex migration
cloud vector DB
complex state management
```

Do not mark these unnecessary automatically.

Evaluate each only if relevant.

Explain why the current simpler architecture may be preferable.

---

# PHASE 42 — “WHAT SHOULD WE ADD?” SECTION

Based only on verified gaps, answer:

```text
What functionality is genuinely missing?
What quality controls are missing?
What evaluation is missing?
What observability is missing?
What documentation is missing?
What security work is missing?
What UX is missing?
What testing is missing?
```

Do not propose features merely to make the project bigger.

The goal is:

```text
better
clearer
safer
more maintainable
more explainable
more trustworthy
```

not more complicated.

---

# PHASE 43 — “WHAT SHOULD WE DELETE?” SECTION

Identify candidates only.

Categories:

```text
definitely generated
obsolete documentation
duplicate artifacts
unused compatibility code
duplicate CSS
dead frontend components
unused API aliases
old reports
runtime logs/cache
```

DO NOT delete anything.

Require evidence before recommending deletion.

---

# PHASE 44 — FINAL ROADMAP

Produce a phased roadmap.

Use:

```text
Phase 0 — Verify correctness
Phase 1 — Critical fixes
Phase 2 — Testing/evaluation
Phase 3 — Maintainability
Phase 4 — UX
Phase 5 — Production hardening
Phase 6 — Optional enhancements
```

For every task give:

```text
priority
reason
files/subsystems
estimated complexity
risk
required validation
```

---

# REQUIRED OUTPUT FILES

Create an audit directory such as:

```text
docs/360_audit/
```

Do NOT overwrite existing documentation during this audit.

Generate:

```text
00_EXECUTIVE_SUMMARY.md
01_PROJECT_OVERVIEW.md
02_PROJECT_STRUCTURE.md
03_TECH_STACK_AND_WHY.md
04_ARCHITECTURE.md
05_END_TO_END_DATA_FLOWS.md
06_DATABASE_AND_DATA_MODEL.md
07_DATA_QUALITY.md
08_RAG_PIPELINE_DEEP_DIVE.md
09_CHUNKING_EMBEDDING_RETRIEVAL.md
10_GENERATION_CITATIONS_GUARDRAILS.md
11_AUTH_SECURITY_PERMISSIONS.md
12_FRONTEND_UI_UX.md
13_DASHBOARD_AND_TENANTS.md
14_WORKFLOW_AGENDA.md
15_BILLING_FORECAST.md
16_TENDER_PUBLICATION.md
17_API_REFERENCE_AUDIT.md
18_CONFIGURATION_AND_OPERATIONS.md
19_TESTING_AND_EVALUATION.md
20_PERFORMANCE_AND_OBSERVABILITY.md
21_FAILURE_MODES.md
22_MAINTAINABILITY_AND_TECH_DEBT.md
23_DOCUMENTATION_AUDIT.md
24_PRODUCTION_READINESS.md
25_IMPROVEMENT_MATRIX.md
26_RECOMMENDED_ROADMAP.md
27_INTERVIEW_DEFENSE_GUIDE.md
28_EVIDENCE_INDEX.md
```

Also create:

```text
360_AUDIT_MASTER_REPORT.md
```

that links to all of them.

---

# EVIDENCE INDEX

`28_EVIDENCE_INDEX.md` is extremely important.

For every major conclusion list:

```text
Conclusion
Evidence file
Function/class/route/table
Why this evidence supports the conclusion
Confidence
```

Use confidence:

```text
HIGH
MEDIUM
LOW
NOT VERIFIED
```

---

# FINAL MASTER REPORT STRUCTURE

`360_AUDIT_MASTER_REPORT.md` should answer, in this order:

```text
1. What is this project?
2. What problem does it solve?
3. Who uses it?
4. What technologies does it use?
5. Why were they chosen?
6. What is the architecture?
7. What data does it use?
8. How does data flow?
9. How does RAG work?
10. How does security/isolation work?
11. How does workflow work?
12. How does billing work?
13. How does tender work?
14. What is already strong?
15. What is incomplete?
16. What is risky?
17. What is technically weak?
18. What is unnecessarily complex?
19. What is missing?
20. What should be improved?
21. What should NOT be changed?
22. What should be done first?
23. What would make it production ready?
24. What should I explain in an interview?
25. What evidence proves every major claim?
```

---

# VALIDATION BEFORE FINISHING

Where possible run existing non-destructive checks such as:

```text
Python tests
lint
frontend build
health/readiness inspection
OpenAPI/route inspection
schema inspection
```

Use the project's supported environment.

Do not run destructive migrations or modify production/source data merely for the audit.

If authenticated UI testing cannot be performed because credentials are unavailable:

```text
state this explicitly
```

Do not simulate successful authentication.

---

# VERY IMPORTANT FINAL INSTRUCTION

At the end DO NOT start implementing the recommendations.

Stop after the audit.

I want to review the evidence and improvement roadmap before modifying the project.

The objective of this task is not to make the project look more complicated.

The objective is to understand the project completely and determine the **smallest set of high-value, evidence-backed changes that would make it more correct, reliable, maintainable, explainable, testable, secure, and production-ready.**