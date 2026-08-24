# Testing and evaluation audit

## Existing test map

| Feature | Tests | Status |
| --- | --- | --- |
| Dashboard metrics/terminology/date quality | test_authority_metrics.py | PASS observed |
| Tenant filtering/pagination | test_tenant_pagination.py | PASS observed |
| Billing calculations/prefill | test_billing_service.py | PASS observed |
| Chat evidence payload | test_chat_payload.py | PASS observed |
| Migration/workflow schema | test_database_migration.py | PASS observed |
| Prompt/citation guardrails | test_guardrails.py | PASS observed |
| PDF inspection | test_inspection.py | PASS observed |
| Adaptive strategy | test_strategy.py | PASS observed |
| Corpus evaluation enumeration | test_live_corpus_evaluation.py | PASS observed |
| Tender workflow | test_tender_workflow.py | PASS observed |
| Frontend compile/build | web npm build | PASS observed |

The observed full suite was 31 passed.

## Missing or not verified

- Real browser auth/E2E for Authority, DO, NO, HO, and Tenant.
- Cross-role ACL adversarial retrieval fixtures.
- CORS/browser DELETE integration test.
- RAG Recall@K, MRR, NDCG, faithfulness, relevance, and citation accuracy on
  reviewed questions.
- OCR multilingual quality and table extraction ground truth.
- Concurrent agenda transition and tender JSON writer tests.
- Billing holdout accuracy and drift monitoring.
- Accessibility keyboard/screen-reader matrix.

## Recommended evaluation set

Create a reviewed question set linked to document IDs, page ranges, expected
answer facts, permitted role, and expected citations. Measure retrieval recall,
MRR, citation-page accuracy, answer faithfulness/relevance, and p50/p95 latency.
Do not create scores from synthetic guesses.

