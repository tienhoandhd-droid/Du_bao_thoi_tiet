# CRAVE Heavy Document Download and Parse Strategy

## Purpose

This strategy prevents Drive downloads and document parsing from overloading
n8n while preserving fail-closed GMP evidence. It applies to future controlled
tests and the eventual authoritative 12-document corpus. It does not authorize
any bulk download, conversion, OCR, Supabase write or corpus import.

## Evidence basis

The R05-A03 metadata inventory contains 115 files with a metadata-reported total
size of 746,899,025 bytes:

| Tier | Size | Files | Total bytes |
|---|---|---:|---:|
| Light | `<= 1 MiB` | 49 | 19,299,814 |
| Medium | `> 1 MiB and <= 10 MiB` | 44 | 185,455,856 |
| Heavy | `> 10 MiB and <= 50 MiB` | 21 | 423,986,551 |
| Very heavy | `> 50 MiB` | 1 | 118,156,804 |

R05-A05 downloaded the smallest PDF, 120,542 bytes. The download completed, but
native PDF extraction returned 18 pages and zero text. This proves that file
size alone does not predict parse cost or quality; scan/OCR routing is required.

## Mandatory queue and concurrency controls

1. Process exactly one file per n8n execution.
2. Keep workflow concurrency at one for download/parse probes.
3. Select work from a deterministic manifest ordered by tier, size, Drive file
   ID and modified time.
4. Never use n8n pin data for binaries.
5. Use filesystem-backed binary mode and drop binary data from downstream output
   immediately after metrics/extraction.
6. Do not begin the next file until the current execution has reached a terminal
   state and its binary-retention condition is known.
7. Retry only transient Drive errors (`429`, `5xx`, connection reset) with capped
   exponential backoff. Do not retry parse-quality failures as network failures.

## Tier-specific execution policy

### Light: up to 1 MiB

- One file per execution.
- Download timeout: 60 seconds.
- Run native text extraction across the file.
- If page count is positive but characters per page are below 30, stop and mark
  `requires_ocr`; do not repeatedly run the same text parser.

### Medium: over 1 MiB through 10 MiB

- One file per execution; no parallel parse.
- Download timeout: 180 seconds.
- First pass extracts at most the first 20 pages for format/quality assessment.
- Full parse is allowed only when the sample has a usable text layer and the
  authoritative mapping/license gates are already satisfied.

### Heavy: over 10 MiB through 50 MiB

- One file per execution with an isolated execution ID.
- Download timeout: 600 seconds.
- Do not feed the whole document into a single n8n text item.
- First perform a page-window probe. A controlled page-streaming worker should
  process 10 pages at a time and write JSONL/text fragments to temporary storage,
  with checkpoints after every page window.
- Resume from the last completed page window rather than restarting the entire
  book after a transient failure.

### Very heavy: over 50 MiB or any archive

- Do not use the normal n8n download-and-extract path.
- Use a separately approved resumable download to controlled temporary disk.
- Require free temporary capacity of at least `2.5 x compressed file size` before
  start, plus an explicit per-run byte ceiling.
- ZIP/RAR files require a dedicated archive-safety gate: entry count cap,
  declared and actual uncompressed-size cap, path traversal rejection and nested
  archive rejection. Never unpack an unknown archive in an n8n Code node.
- A file larger than 50 MiB or an archive cannot enter full parse/OCR without a
  separate exact approval naming that file ID and byte budget.

## Parse-quality routing

Use the following probe sequence before full conversion:

1. Verify MIME, Drive ID, size and modified time against the approved manifest.
2. Download to temporary filesystem-backed binary storage.
3. Read PDF page count and metadata.
4. Run text-native extraction on a bounded page sample.
5. Route by evidence:
   - `success`: at least 500 characters, at least 100 words, replacement/control
     ratios at most 1%, and at least 100 characters per sampled page;
   - `partial`: at least 100 characters but below the success threshold;
   - `requires_ocr`: positive page count and fewer than 30 characters per page;
   - `failed`: unreadable file, invalid PDF, encrypted extraction block or no
     usable output.
6. OCR-required files use a separately approved OCR benchmark on selected pages
   before any full-document OCR.
7. Full conversion remains prohibited until document mapping, license,
   provenance and immutable-version evidence are known.

## OCR-safe design for scanned books

- Benchmark three representative pages: first content page, middle page and last
  content page; exclude blank covers when possible.
- Render at 150 DPI first. Increase to 200/300 DPI only when the benchmark shows
  a measurable quality gain.
- OCR in 10-page windows, concurrency one.
- Persist only per-page metrics and temporary text during the probe. Do not create
  document chunks or embeddings.
- Stop when the rolling failure rate exceeds 20%, the temporary byte ceiling is
  reached, or execution time exceeds the approved budget.
- The current local runtime exposes `pdfinfo` but not `tesseract`, `ocrmypdf`,
  `qpdf` or `mutool`; adding an OCR runtime is a separate tooling/change-control
  decision, not part of R05-A05.

## Idempotency and evidence

- Pre-import identity key: Drive file ID + modified time + metadata size.
- Final identity key: binary SHA-256 calculated outside n8n Code nodes after an
  approved download; n8n crypto remains prohibited.
- Every execution records workflow version, file ID, tier, expected/actual bytes,
  page count, parser, parse status, quality metrics, retry count and cleanup state.
- A failed or partial probe must never set `approved_for_ai_use`, hash verification,
  parse success, current-version linkage or embedding status.

## Recovery and cleanup

- A terminal parse failure preserves metrics but does not trigger automatic OCR
  or a larger download.
- Binaries are temporary and must not be copied into the repository.
- Future production execution retention and binary-pruning settings must be
  inspected and explicitly approved before bulk work.
- Resume manifests must be immutable per run; modifications create a new run ID.

## Current decision

The safest next benchmark is a three-page OCR test of the same lightweight PDF,
not a larger book. That benchmark requires separate approval and an approved OCR
runtime. Until then, BLK-004 remains open with stronger evidence: native parsing
is insufficient for at least one real Drive PDF.
