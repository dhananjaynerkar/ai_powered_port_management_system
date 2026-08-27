# 00 — audit baseline

**Audit date:** 2026-08-24  
**Target:** target checkout (local path redacted)
**Audit mode:** local-only, read-only verification unless a pre-existing
automated test uses an isolated temporary fixture.

## Repository and source baseline

- The target directory does **not** contain its own `.git` directory.
- `git rev-parse --show-toplevel` resolves to `C:/Users/15dha`, a parent
  checkout containing unrelated user files. No target commit or clean target
  worktree can therefore be asserted.
- The source inventory observed during the audit was 29 Python files under
  `src/` and one TypeScript/TSX application entrypoint under `web/src/`.
- The target was not compared or merged with AI PMS; that reference project
  remains outside this audit's mutation scope.

## Runtime baseline

| Component | Observed | Evidence |
|---|---|---|
| Python | 3.13.14 | `.venv\\Scripts\\python.exe --version` |
| Node | v22.22.3 | `node --version` |
| npm | 10.9.8 | `npm --version` |
| Ollama | 0.31.1 | `ollama --version` |
| PostgreSQL | 17.10 on x86_64-windows | read-only `SELECT version()` |
| PostgreSQL database | `portproject` on `127.0.0.1:5432` | `Settings` + connection |
| API | `127.0.0.1:8001` | `portproject_rag.server` listener and `/health` |
| React/Vite | `127.0.0.1:5173` | Vite listener and `/` |
| Ollama API | `127.0.0.1:11434` | listener and installed model list |

The active listener owners were: Vite `node.exe` PID 4740, PostgreSQL PID
6804, target API PID 19172, and Ollama `ollama.exe` PID 5484. PIDs are
diagnostic evidence only and may change on restart.

## Model/configuration baseline

- Embedding model: `bge-m3`.
- Embedding dimension: 1024.
- Primary generation model: `qwen3.5:4b`.
- Fallback model: configured as `qwen3.5:4b`, with fallback disabled.
- Reranker: `BAAI/bge-reranker-v2-m3`, CPU mode.
- PostgreSQL extensions: `pgcrypto 1.3`, `vector 0.8.5`; the `vector`
  extension is also available to the server.
- Ollama models installed at audit time: `bge-m3:latest`, `phi3:latest`,
  `qwen3.5:4b`, `llama3-chatqa:latest`, `qwen3:4b`, `qwen3.5:9b`, and
  `phi3:mini`.

Secret values were not printed or copied into this report. `.env` exists and
is ignored by `.gitignore`; only its key names were inspected.

## Corpus/database baseline

The application-facing projection (`pms_doc`/`pms_vector`) reports:

- 48 indexed documents
- 1 pending document
- 1,476 pages across indexed documents
- 3,399 chunks
- 3,399 non-null vectors
- 1024 dimensions for all checked vectors

The underlying `rag` tables contain 49 document rows and 1,474 page rows; the
single document without chunks accounts for two pending pages. This is why
the application projection correctly reports 48 indexed documents and 1
pending document.

Read-only referential checks found zero orphan chunks, zero orphan pages, zero
chunks without embeddings, zero wrong-dimension vectors, zero orphan chat
messages, zero orphan agenda messages, and zero invalid session-expiry
invariants. One document has no chunks and is therefore pending extraction.

## Database/domain baseline

The live dashboard query returned 2,770 plot records and total land of
4,383,038.68 sq.m (438.30 ha). It also returned:

- status `A` / Approved: 4,057,052.65 sq.m (405.71 ha)
- status `RG` / Registered: 135,138.75 sq.m (13.51 ha)
- status `V` / Verified: 65,847.28 sq.m (6.58 ha)
- `is_vacant = true`: 1,030,814.67 sq.m (103.08 ha)

The last two values are not equivalent and are intentionally recorded as an
acceptance gap. The current API derives land occupancy from `RG` first and
then `is_vacant`, while the status breakdown uses `plot.status`; a product or
domain owner must decide which concept the UI should call “vacant.”

The tenant page is backed by 3,841 rows in
`public.applicant_property_mapping`, not a canonical tenant master count. The
terminology query found 3,839 tenancy identifiers, 3,841 mapping applicant
IDs, 3,072 matched applicant profiles, 769 orphan mapping rows, and 2 missing
tenancy identifiers. Lifecycle classification returned 3,189 Running, 651
Expired, and 1 Unclassified mapping records.

## Verification limitations

- No authorized Authority/NO/DO/HO/Tenant credentials were supplied for this
  audit. No login attempt, password guessing, account creation, or auth
  bypass was performed.
- No isolated production-like database clone or approved workflow fixture was
  supplied. Valid/invalid workflow transitions, concurrent ownership, live
  chat generation, deletion, billing API mutation, tender persistence, and
  backup/restore were not executed.
- A direct local retrieval smoke attempt did not complete within the command
  runner window while local embedding/reranker startup was occurring; it was
  recorded as unverified, not as a fabricated answer-quality result.
- Browser visual checks at every requested viewport were not claimed. The
  production build and static responsive CSS were inspected, but an
  authenticated browser session is still required for final UX acceptance.
