# Maintainability and technical debt

## Debt register

| ID | Finding | Severity | Evidence | Action |
| --- | --- | --- | --- | --- |
| TD-01 | React behavior is concentrated in main.tsx. | P2 | About 2,511 lines observed. | Extract tested feature boundaries incrementally. |
| TD-02 | Shared and feature CSS is concentrated in styles.css. | P2 | About 5,458 lines observed. | Introduce stable tokens/layers before moving selectors. |
| TD-03 | API routes and feature orchestration share api.py. | P2 | Route inventory and models are in one module. | Add contract tests before router extraction. |
| TD-04 | Tender state is JSON, not transactional database state. | P2 | TenderWorkflowService data path. | Business/deployment decision before migration. |
| TD-05 | API and package versions differ. | P3 | FastAPI app 0.2.0 vs package 0.1.0. | Establish release version policy. |
| TD-06 | Source identity has legacy password fallback. | P1 | auth.py external login functions. | Source-system security decision. |
| TD-07 | RAG quality scores are not current. | P2 | Evaluation tests enumerate corpus but do not prove answer quality. | Build reviewed evaluation set. |

## Proven redundancy candidates

Generated web/dist, caches, logs, and TypeScript metadata are reproducible
outputs and are ignored going forward. They were not deleted.

Older documents contain historical baseline reports. They should be marked
historical, not deleted, because they preserve decision evidence.

No source module or compatibility route is proven safe to remove.

## Overengineering check

Microservices, Kubernetes, Kafka, Redis, graph RAG, agent frameworks, cloud
vector databases, and wholesale LangChain/LlamaIndex migration are not justified
by current evidence. They would add operational boundaries before current
evaluation/security gaps are closed.

