# Tasks

## 1. The published artifacts

- [x] 1.1 Store the Zenodo PDF byte-for-byte; check its MD5 against the record's
- [x] 1.2 Render the Markdown/HTML once more with the "Note on process" kept; confirm the
      diff against the current web copies is that note and nothing else
- [x] 1.3 Store the web copies, stylesheet and the three referenced figure SVGs
- [x] 1.4 Write `PUBLISHED.json` with DOI, record, date, source commit, record MD5, and
      per-artifact SHA-256

## 2. The build and the guard

- [x] 2.1 Makefile: Paper 1 targets copy from `published/`; no typst or pandoc over Paper 1
- [x] 2.2 `check-freeze.py`: verify the marker (missing, altered, unlisted artifact; PDF MD5)
- [x] 2.3 Tests for each failure path, and that the real marker passes
- [x] 2.4 Pre-commit: exempt the published PDF from the size cap; widen `check-freeze`'s
      trigger to the marker and artifacts

## 3. Records

- [x] 3.1 `ERRATA.md`: dated note that the web copies were restored and frozen
- [x] 3.2 `papers/README.md` and `AGENTS.md`: frozen vs published, and what each guards

## 4. Verification

- [x] 4.1 `make clean && make build` green; `dist/papers/01-vision/` byte-equal to `published/`
- [x] 4.2 The Zenodo-named PDF in `dist/` has the record's MD5
- [x] 4.3 Pre-commit green; `openspec validate mark-published-papers --strict`

## 5. Found in the doing

- [x] 5.1 The filter's centred-note branch (added the same day in `prepare-paper-2-publication`)
      wrapped the note in `Strong`, bolding the whole paragraph in HTML; it now passes the
      paragraph through as written. Fixed before the web copies were frozen, and it also
      corrects Papers 2 and 3
- [x] 5.2 The fixers `trailing-whitespace`, `end-of-file-fixer` and `mixed-line-ending` exclude
      `published/`, since they would rewrite checksummed files on commit
