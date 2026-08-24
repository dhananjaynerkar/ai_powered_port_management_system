from psycopg import connect

from portproject_rag.settings import Settings


def test_evaluation_matrix_enumerates_every_currently_indexed_document() -> None:
    """Evaluate corpus eligibility from live state instead of a fixed filename list."""
    settings = Settings()
    with connect(settings.database_url.unicode_string()) as connection, connection.cursor() as cursor:
        cursor.execute(f"""SELECT d.document_id, d.original_filename,
            COUNT(DISTINCT c.chunk_id) AS chunks,
            COUNT(DISTINCT c.chunk_id) FILTER (WHERE c.search_vector IS NOT NULL) AS lexical_hits,
            COUNT(DISTINCT e.chunk_id) FILTER (WHERE e.embedding IS NOT NULL) AS dense_hits,
            COUNT(DISTINCT c.chunk_id) FILTER (WHERE length(c.chunk_text) > 0) AS rerank_eligible,
            COUNT(DISTINCT c.chunk_id) FILTER (WHERE c.page_number > 0) AS citation_grounded,
            COUNT(DISTINCT a.chunk_id) FILTER (WHERE a.acl_roles IS NOT NULL) AS acl_covered
            FROM {settings.document_schema_name}.document_record d
            LEFT JOIN {settings.vector_schema_name}.document_chunk c ON c.document_id=d.document_id
            LEFT JOIN {settings.vector_schema_name}.chunk_embedding e ON e.chunk_id=c.chunk_id
            LEFT JOIN {settings.vector_schema_name}.chunk_acl a ON a.chunk_id=c.chunk_id
            WHERE EXISTS (SELECT 1 FROM {settings.vector_schema_name}.document_chunk indexed WHERE indexed.document_id=d.document_id)
            GROUP BY d.document_id, d.original_filename ORDER BY d.original_filename""")
        matrix = cursor.fetchall()

    assert matrix, "The live indexed corpus is empty."
    for document_id, filename, chunks, lexical, dense, rerank, citations, acl in matrix:
        assert document_id is not None and filename
        assert chunks > 0, f"{filename}: no chunks"
        assert lexical == chunks, f"{filename}: lexical coverage mismatch"
        assert dense == chunks, f"{filename}: dense coverage mismatch"
        assert rerank == chunks, f"{filename}: rerank eligibility mismatch"
        assert citations == chunks, f"{filename}: exact-page citation coverage mismatch"
        assert acl == chunks, f"{filename}: ACL coverage mismatch"
