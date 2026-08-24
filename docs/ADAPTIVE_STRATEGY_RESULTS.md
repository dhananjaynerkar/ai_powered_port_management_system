# Adaptive strategy results

The v2 strategy run reevaluated all 1,504 pages after local capabilities were acquired. It detected Tesseract 5.4 through an explicit executable search, with `eng` and `osd` language data only; `pdfplumber`; and `pypdf`.

| Outcome | Before | After | Interpretation |
|---|---:|---:|---|
| Quarantine | 184 | 0 selected as final plan | 148 image-only pages select OCR; 36 poor-native pages select parser retry. Execution still validates output. |
| OCR-page plan | 0 | 148 | A sampled scanned page returned 2,684 characters, quality 100, and mean OCR confidence 95.06. This is one sample, not corpus-wide validation. |
| Structured-table plan | 0 | 488 candidates | Capability is present; each page still requires measured table extraction before persistence. |

Table experiment: 12 of 399 signalled pages were sampled under a bounded budget. `pdfplumber` found one or more tables on 8 pages, but only 4 pages produced a usable multi-column row representation. It remains an opportunistic table strategy with a raw-page-context fallback. The unbounded experiment exceeded a two-minute limit, so production table extraction must stay budgeted.
