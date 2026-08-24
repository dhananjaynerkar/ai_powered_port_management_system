# Capability gap analysis

Audit date: 2026-08-13. The project venv uses Python 3.13.14 and contains
PyMuPDF, Psycopg, pgvector, HTTPX, Pydantic settings, and pytest. It does not
contain OCR, table extraction, or an alternative PDF parser. `pdftoppm` is
available for rendering; Tesseract, `psql`, and table-extraction executables
are not. PostgreSQL TCP port 5432 is reachable. Ollama is installed but port
11434 was closed at audit time.

Smallest justified additions:

1. Tesseract plus `pytesseract` and Pillow: local CPU OCR for the 184 pages
   currently quarantined. Verify installed language packs before claiming
   Hindi/Marathi coverage.
2. `pdfplumber`: lightweight native-table inspection and extraction. It does
   not replace OCR for scanned tables.
3. `pypdf`: a low-cost independent text-extraction retry only; it is not an
   OCR solution.

No reranker, Graph RAG stack, cloud service, or second vector database is
justified before a baseline corpus ingestion and retrieval evaluation.
