# Chunking strategy

Current executable chunks are paragraph-preserving and page-anchored. Their target is derived per document from measured average page text and bounded by environment settings. Table pages must become title/context plus structured columns/rows and row chunks only after a validated table extractor is available. Repeated headers/footers stay intact until review proves they are boilerplate.
