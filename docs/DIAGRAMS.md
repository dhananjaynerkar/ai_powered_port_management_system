# Architecture diagrams

**Status: CURRENT SOURCE OF TRUTH**

The diagrams use Mermaid so they remain versioned text and render in GitHub and
most Markdown viewers.

## Overall architecture

```mermaid
flowchart LR
  Browser[React/Vite browser :5173] -->|HTTP-only session cookie| API[FastAPI API :8001]
  API --> Source[(PostgreSQL public.* PMS data)]
  API --> RAG[(PostgreSQL rag.* + pgvector)]
  API --> Views[(pms_doc / pms_vector views)]
  API --> Ollama[Local Ollama :11434]
  API --> Reranker[Local CrossEncoder reranker]
  API --> Billing[Billing runtime artifacts]
  API --> Tender[Tender JSON store + source exports]
```

## RAG pipeline

```mermaid
flowchart TD
  PDF[PDF corpus] --> Inspect[Inspect/profile pages]
  Inspect --> Strategy{Adaptive strategy}
  Strategy --> Native[Native extraction]
  Strategy --> OCR[OCR/Tesseract]
  Strategy --> Alt[Alternative parser]
  Strategy --> Table[Bounded table extraction]
  Native --> Pages[Pages + provenance]
  OCR --> Pages
  Alt --> Pages
  Table --> Pages
  Pages --> Chunks[Provenance chunks + ACL]
  Chunks --> Embed[bge-m3 1024-d embeddings]
  Embed --> Store[(rag.document/page/chunk)]
  Q[User question] --> Guard[Guardrail]
  Guard --> Retrieve[Lexical + pgvector retrieval]
  Store --> Retrieve
  Retrieve --> RRF[RRF + role ACL]
  RRF --> Rank[CrossEncoder rerank]
  Rank --> Gen[Local qwen completion]
  Gen --> Cite[Citation validation]
  Cite --> Answer[Answer + page sources]
```

## Authentication

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as FastAPI
  participant P as PMS public identity tables
  participant R as rag.user_session
  U->>A: POST authority/tenant login
  A->>P: Verify existing identity and active role
  A->>R: Store SHA-256 token digest + expiry
  A-->>U: HTTP-only portproject_session cookie
  U->>A: Protected request with cookie
  A->>R: Resolve principal and expiry
  A-->>U: Authorized response or 401/403
```

## Chat to agenda

```mermaid
flowchart LR
  Private[Private chat] --> Query[Grounded RAG answer]
  Query --> Sources[Real page citations]
  Sources --> Create[DO creates agenda draft]
  Create --> Version[v1 + evidence snapshot]
  Version --> NO[Submit to NO]
  NO -->|return| Revise[DO revision]
  Revise --> NO
  NO -->|submit| HO[HO review]
  HO -->|approve/reject| End[Final state]
```

## Billing flow

```mermaid
flowchart TD
  Form[Authority billing form] --> Rules[Rules/config endpoint]
  Form --> Prefill[Selected tenancy prefill]
  Prefill --> Inputs[Reviewed source + manual inputs]
  Inputs --> Model[XGBoost forecast artifact]
  Inputs --> Formula[Deterministic tax formula layer]
  Model --> Result[Forecast result + metadata]
  Formula --> Result
  Result --> Chat[Persist user-scoped chat/audit event]
```

## Tender flow

```mermaid
flowchart LR
  Plot[Eligible vacant plot export] --> LAC[LAC draft/approval]
  LAC --> Board[Board Note draft/approval]
  Board --> Calc[Finalize calculation]
  Calc --> Draft[Tender/RFP draft]
  Draft --> NIT[NIT approval]
  NIT --> Publish[PUBLISHED]
  Draft --> JSON[(tender_workflows.json)]
```

## Database ownership

```mermaid
flowchart TB
  PMS[Source PMS owner] --> Public[public.* tables]
  Portal[PortProject RAG] --> Rag[rag.* application state]
  Portal --> Views[pms_doc / pms_vector views]
  Public --> API[FastAPI read adapters]
  Rag --> API
  Views --> API
```
