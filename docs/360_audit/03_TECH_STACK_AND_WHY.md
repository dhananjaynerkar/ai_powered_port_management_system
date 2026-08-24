# Technology stack and rationale

| Technology | Evidence | Why it is used | Replacement decision |
| --- | --- | --- | --- |
| Python 3.12+ | pyproject.toml | Backend, ingestion, database, tests, and CLI ecosystem. | No replacement justified. |
| FastAPI | api.py | Typed HTTP routes, validation, dependency-based auth, and OpenAPI. | Keep unless service scale requires a separate boundary. |
| React 19 | web/package.json and main.tsx | Stateful role-aware portal UI. | Keep; existing UX depends on it. |
| Vite 7 | web/package.json/vite.config.ts | Local development and production bundling. | Keep for current single UI. |
| TypeScript | web/package.json/main.tsx | Compile-time UI contract checks. | Keep. |
| PostgreSQL | database.py and SQL routes | Existing PMS source data plus transactional portal state. | Keep; source system already uses it. |
| pgvector | database.py and retrieval.py | Embedding storage and cosine vector search in the same database. | Keep while corpus scale and ACL locality favor it. |
| pgcrypto | database.py | UUID generation and application migration support. | Keep as database extension. |
| Ollama | settings.py, api.py, ingestion.py, generation.py | Local embedding, completion, and model discovery. | Keep for local-only requirement; production hosting decision remains. |
| bge-m3 | Settings default and ingestion | 1024-dimensional local embeddings for multilingual/document retrieval. | Do not replace without measured evaluation. |
| Qwen configured model | settings.py and local model route | Local answer generation with user-selectable installed completion models. | Do not change without latency/quality evidence. |
| CrossEncoder reranker | retrieval.py | Reorders lexical+dense candidates for precision. | Keep; startup cost is documented. |
| PyMuPDF/pdfplumber/pypdf | ingestion and extraction modules | PDF inspection, text extraction, and bounded table handling. | Keep; current adaptive strategy relies on capability checks. |
| pytesseract/Pillow | ocr.py | Optional local OCR adapter. | Availability must be verified per machine. |
| ReportLab | tender_document_pdf.py | Draft tender/LAC/board-note PDFs. | Keep for current generated-document requirement. |
| XGBoost artifact evaluator | billing/prediction_service.py | Runs exported model JSON without requiring xgboost at runtime. | Keep; training dependency remains optional. |
| PowerShell | start_app.ps1 | Windows process/port checks and local launcher. | Keep for target environment. |
| pytest/Ruff | pyproject.toml and tests | Regression tests and static quality checks. | Keep and expand coverage. |

## Runtime versus optional dependencies

Core runtime dependencies are declared in pyproject.toml. Billing training
packages (numpy, pandas, scikit-learn, xgboost) are optional; runtime billing
evaluates an exported JSON artifact. This distinction is evidenced by the
optional dependency group and BillingPredictionService.

## Local/offline boundary

The application is designed around local PostgreSQL and Ollama endpoints. No
cloud embedding or generation fallback is configured. The reranker may load
local model weights through its configured runtime; external model download
behavior is an operational concern, not proof of cloud inference.

