from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .database import migrate
from .experiments import run_table_experiment
from .ingestion import ingest
from .inspection import inspect_corpus
from .ocr import ocr_page
from .reporting import write_final_ingestion_report, write_strategy_decisions
from .retrieval import hybrid_search
from .settings import Settings


def _inspect(args: argparse.Namespace) -> None:
    profiles = inspect_corpus(Path(args.corpus), Path(args.output))
    print(f"inspected_documents={len(profiles)}")
    for classification, count in sorted(Counter(item.classification for item in profiles).items()):
        print(f"classification.{classification}={count}")
    print(f"report={Path(args.output).resolve() / 'corpus.json'}")


def _migrate(_: argparse.Namespace) -> None:
    settings = Settings()
    migrate(settings)
    print(f"migration=ok schema={settings.schema_name} database={settings.database_url.path.lstrip('/')}")


def _summary(args: argparse.Namespace) -> None:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    documents = report["documents"]
    print(f"report_documents={len(documents)}")
    print(f"duplicates={sum(1 for item in documents if item['duplicate_of'])}")
    print(f"ocr_or_advanced_review={sum(1 for item in documents if item['extraction_strategy'] not in {'NATIVE_PYMUPDF', 'SKIP_DUPLICATE'})}")


def _ingest(args: argparse.Namespace) -> None:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    from .inspection import PdfProfile

    result = ingest(Settings(), [PdfProfile(**item) for item in report["documents"]], dry_run=args.dry_run)
    print(f"documents_inserted={result.documents_inserted}")
    print(f"documents_skipped={result.documents_skipped}")
    print(f"chunks_inserted={result.chunks_inserted}")
    print(f"quarantined_documents={result.quarantined_documents}")
    print(f"failed_documents={result.failed_documents}")
    print(f"duration_ms={result.duration_ms}")


def _query(args: argparse.Namespace) -> None:
    results = hybrid_search(Settings(), args.question, args.limit)
    for result in results:
        print(json.dumps({"filename": result.filename, "page_number": result.page_number, "lexical_rank": result.lexical_rank, "dense_rank": result.dense_rank, "fused_score": result.fused_score, "text": result.chunk_text}, ensure_ascii=False))


def _final_report(args: argparse.Namespace) -> None:
    from .inspection import PdfProfile

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    profiles = [PdfProfile(**item) for item in report["documents"]]
    write_final_ingestion_report(profiles, Path(args.output), "MISSING" if not Path(".env").exists() else "CONFIGURED_NOT_VERIFIED")
    print(f"report={Path(args.output).resolve() / 'final-ingestion-report.json'}")


def _strategize(args: argparse.Namespace) -> None:
    from .inspection import PdfProfile

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    count, capabilities = write_strategy_decisions([PdfProfile(**item) for item in report["documents"]], Path(args.output), args.suffix)
    print(f"strategy_decisions={count}")
    print(f"ocr_available={capabilities.ocr_available}")
    print(f"table_extractor_available={capabilities.table_extractor_available}")
    print(f"alternative_parser_available={capabilities.alternative_parser_available}")


def _ocr_page(args: argparse.Namespace) -> None:
    result = ocr_page(Path(args.source), args.page)
    print(json.dumps({"character_count": len(result.text), "mean_confidence": result.mean_confidence, "quality_score": result.quality_score, "error": result.error, "text_preview": result.text[:200]}, ensure_ascii=False))


def _table_experiment(args: argparse.Namespace) -> None:
    from .inspection import PdfProfile

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    summary = run_table_experiment([PdfProfile(**item) for item in report["documents"]], Path(args.output), args.max_pages)
    print(json.dumps(summary))


def _evaluate_gold(args: argparse.Namespace) -> None:
    from .evaluation import run_gold_evaluation

    json_path, csv_path, payload = run_gold_evaluation(
        Settings(), Path(args.gold), Path(args.output), generate=not args.no_generation
    )
    print(f"questions={payload['question_count']}")
    print(f"completed={payload['completed_count']}")
    print(f"retrieval_failed={payload['retrieval_failed_count']}")
    print(f"generation_failed={payload['generation_failed_count']}")
    print(f"json={json_path.resolve()}")
    print(f"csv={csv_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Corpus-aware PDF inspection for portproject")
    commands = parser.add_subparsers(required=True)
    inspect_parser = commands.add_parser("inspect")
    inspect_parser.add_argument("corpus")
    inspect_parser.add_argument("--output", required=True)
    inspect_parser.set_defaults(handler=_inspect)
    migrate_parser = commands.add_parser("migrate")
    migrate_parser.set_defaults(handler=_migrate)
    summary_parser = commands.add_parser("summary")
    summary_parser.add_argument("--report", required=True)
    summary_parser.set_defaults(handler=_summary)
    ingest_parser = commands.add_parser("ingest")
    ingest_parser.add_argument("--report", required=True)
    ingest_parser.add_argument("--dry-run", action="store_true")
    ingest_parser.set_defaults(handler=_ingest)
    query_parser = commands.add_parser("query")
    query_parser.add_argument("question")
    query_parser.add_argument("--limit", type=int)
    query_parser.set_defaults(handler=_query)
    final_report_parser = commands.add_parser("final-report")
    final_report_parser.add_argument("--report", required=True)
    final_report_parser.add_argument("--output", default="artifacts")
    final_report_parser.set_defaults(handler=_final_report)
    strategy_parser = commands.add_parser("strategize")
    strategy_parser.add_argument("--report", required=True)
    strategy_parser.add_argument("--output", default="artifacts")
    strategy_parser.add_argument("--suffix", default="")
    strategy_parser.set_defaults(handler=_strategize)
    ocr_parser = commands.add_parser("ocr-page")
    ocr_parser.add_argument("source")
    ocr_parser.add_argument("--page", required=True, type=int)
    ocr_parser.set_defaults(handler=_ocr_page)
    table_parser = commands.add_parser("table-experiment")
    table_parser.add_argument("--report", required=True)
    table_parser.add_argument("--output", default="artifacts")
    table_parser.add_argument("--max-pages", type=int, default=40)
    table_parser.set_defaults(handler=_table_experiment)
    evaluate_parser = commands.add_parser("evaluate-gold", help="Measure the current pipeline against a reviewed golden set")
    evaluate_parser.add_argument("--gold", default="evaluation/rag_gold_v1.json")
    evaluate_parser.add_argument("--output", default="artifacts/evaluation/rag_baseline_v1")
    evaluate_parser.add_argument("--no-generation", action="store_true", help="Run retrieval metrics only")
    evaluate_parser.set_defaults(handler=_evaluate_gold)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
