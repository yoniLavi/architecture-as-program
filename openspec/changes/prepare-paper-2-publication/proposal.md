# Prepare Paper 2 for publication

## Why

A whole-project review on 28 September 2026, after eight weeks away, found Paper 2
substantively ready and the build green, but surfaced four defects that should not ship
under a DOI. A background survey of work since the July prior-art pass found nothing
that pre-empts the narrowed novelty claim, but found close convergence — including an
open-source CI check, merged two days earlier, that compares compiled components'
imports against a hand-written manifest — which argues for publishing now rather than
polishing further.

1. **A universal claim prior art falsifies.** The abstract opens "Architecture models
   describe what a system's components may do; they do not constrain it", and the
   conclusion repeats it. seL4's CAmkES has, for about a decade, compiled a component
   architecture description into a capDL capability distribution and *proved* the
   correspondence (Klein et al., CACM 2018, Theorem 4; Fernandez 2016). CAmkES was
   absent from the survey and from both papers. It is the obvious reviewer citation, and
   its link from model to authority is stronger than ours (a proof, not a test).
2. **A per-run figure in the abstract.** The abstract and the conclusion interpolate
   `crossing_us`, the exact crossing cost from one run (36.6µs in the review's build,
   ~25µs in August's). §7.2 says only the order of magnitude is supported, and the
   Zenodo record takes the abstract verbatim, so the record would fix a figure the next
   build contradicts.
3. **The lead claim's gate is shown firing only on a fabricated import list.** Table 1
   reports only agreeing rows; the one test of the failing direction constructs a
   `Derivation` by hand. The paper's own argument for putting the canonical graphs in
   the corpus (a validator that rejected everything would be worthless) applies in
   reverse: a gate never shown rejecting a real binary is weak evidence. A real
   over-importing binary already exists: `hostile_ungranted` has `ParseMessage`'s
   signature and additionally imports `kb-read`.
4. **Housekeeping.** The date line says August; the title-block note loses word
   spaces in the Markdown/HTML outputs; `docs/ROADMAP.md`'s "Start here" is dated
   1 August; three prior-art verification debts are now resolved and one survey
   finding (Filament's lattice) cuts the other way from what was expected.

## What Changes

- **Evaluation harness** — a *negative control* for the derivation: the real
  `hostile_ungranted` binary is held against `ParseMessage`'s `with` clause through the
  same code path as the agreeing rows, and pinned to be caught as an over-grant of
  exactly `aap:caps/kb-read`. If the gate stops catching it, the build fails. It is
  reported in the artifact and in `evaluation.json`, separately from the agreeing rows,
  so the agreement counts are unchanged in meaning.
- **Paper 2** —
  - Abstract and conclusion: the opening claim is scoped to architecture models in
    mainstream use, and the per-run crossing figure is replaced by its magnitude.
  - §4.1: the negative control is reported beside Table 1.
  - §6.2 gains CAmkES/capDL as the stronger precedent, with the difference stated
    (it generates and proves the capability distribution of a static seL4 system; we
    check independently compiled components, the case agent-authored bodies create).
  - §6.1 gains Language-Based Agent Control (Zhou, D'Antoni, Polikarpova 2026), the
    closest type-based sibling of the trust lattice, evaluated on AgentDojo against CaMeL.
  - §6.6 gains McCann's certified-purity gate (an import-section check against one
    global whitelist) and Wassette (source-verified: every component linked against all
    of WASI p2, permissions from a separate policy file).
  - Date line and title-block fix.
- **Paper 3** — date line; the lattice agenda item notes that Filament keeps the
  lattice user-defined.
- **Docs** — `docs/PRIOR-ART.md` debts resolved and new entries; `docs/ROADMAP.md`
  "Start here" refreshed; a publication checklist with the Zenodo metadata for the
  author's upload.

## Impact

- Affected specs: `evaluation`, `paper-corpus`; and, from the review rounds of 30 September
  after the merge, `signal-graph-runtime` (assembly validates a composition; the import-set
  requirement names the type vocabulary and per-node clocks) and `trust-typing` (the wiring
  requirement states its order against the flows-to convention, renamed from "flow-sensitive")
- Affected code: `poc/evaluate.py`, `tests/test_poc_evaluate.py`; and, from those rounds,
  `poc/graph.py` (cross-graph validation at assembly), `poc/sandbox/host.py`
  (`ungranted_imports`), `poc/demo.py`, and the inspector's walkthrough copy
- Affected papers: `papers/02-demonstrator/proposal.typ`, `papers/03-method/proposal.typ`
- Affected docs: `citations.bib`, `docs/PRIOR-ART.md`, `docs/ROADMAP.md`, `AGENTS.md`
- Paper 1 is untouched (frozen, errata-only); nothing here is an erratum to it — its
  vision-paper framing predates the CAmkES comparison and makes no survey claim about it.
- Publishing is **not** part of this change. The author uploads to Zenodo; the DOI is
  stamped into `citations.bib` and the title block in a follow-up commit.
