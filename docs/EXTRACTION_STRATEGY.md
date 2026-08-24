# Extraction strategy

`PageQuality` derives character/word density, printable ratio, whitespace, replacement characters, repeated runs, and image presence. The score is a routing signal: HIGH (80+), ACCEPTABLE (55–79), POOR (1–54), and OCR_REQUIRED/FAILED (0). It is not a legal-text accuracy claim and must be calibrated against reviewed samples.

Native pages use PyMuPDF. Poor/image-only pages require OCR. No alternative parser or OCR provider is available in the project environment, so the system records the limitation rather than fabricating text. Hybrid documents can now take native and OCR paths page by page.
