# Paper 3: agent-written components against the derived import gate

> **Status: proposed, 29 October 2026. Not approved. No paper text is written until it is.**
> The author settled three questions before scaffolding (`design.md`, "Decided"): Paper 3
> follows Paper 2 and cites it; it is generation-led; its budget is ~8,000 words.

## Why

Paper 2 ends on the experiment it could not run (§8): whether an agent-written body ever
reaches for authority its node was not granted, how often, and whether the gate derived from the
`with` clause is what stops it. That experiment has now been run and replicated under
registration (`strengthen-generation-evidence`, 27–28 October 2026). The result is the one the
roadmap names as the reason for the next paper. No paper reports it yet.

The evidence is in generated artifacts (`dist/generation.{md,json}`,
`dist/evaluation-feed.{md,json}`), so the paper can be written to the corpus's rules: every
figure interpolated, every limit stated where it bounds a claim.

## What Changes

- **A new living paper, `papers/03-generation/`**, ~8,000 words. Its lead claim: models given
  a node's signature alone did not reach for ungranted authority, whether asked or with the rule
  withheld. Told that authority had been approved, they reached for it, in a registered
  replication. The gate rejected every over-importing component, as a set comparison must,
  and the gate-off control shows nearly all of those would otherwise have shipped. The feed-triage
  service is the vehicle for nine of the fifteen nodes, and its hostile-feed corpus gets a short
  section. Operation and replays are stated as limits, not reported as results.
- **Paper 3 follows Paper 2.** It cites Paper 2 for the gate, the derivation, the tiers, and every
  Paper 2 magnitude, and restates none of them. It can be drafted now. It cannot be stamped
  before Paper 2 is published.
- **The citation rule becomes a check.** `scripts/check-corpus-citations.py` will fail the build
  if a paper carrying a DOI stamp cites a corpus paper that has no committed publication marker.
  Paper 2 passes today, because it cites only Paper 1. Today the rule rests on review, and it has
  failed under review once (the September cycle).
- **The generation report is brought up to its own evidence first.** Its opening and its closing
  "does and does not show" section still describe the run before registration ("two fixed
  pretexts", "the task tells the model the rule"). The registered run answers both. A paper must
  not quote an artifact that understates itself. The report also gains a `display` block, so
  neither typst nor pandoc formats a float in its own way (the confirmatory p-value).
- **The accounting stays in Paper 2.** Paper 3 restates no prediction of Paper 1 or its verdict.
  Whether Paper 2's v1.1 updates its rows once Paper 3 is published is a later decision; it may
  cite Paper 3 only then.

**Not in this change:** any edit to Paper 2's text or figures (the pin in
`tests/test_paper2_figures_pinned.py` stands); the model replays (held by the author for a
longer archive); a second model family; an AgentDojo number; routing-point attenuation; and any
upload, DOI reservation or other outward-facing act. Each of those needs an explicit go.

## Impact

- **Specs:** `paper-corpus`. It gains three requirements: the generation paper's form and claim
  discipline; its figures interpolated from the generation and feed artifacts; and no stamped
  paper citing an unpublished corpus paper.
- **Papers:** new `papers/03-generation/proposal.typ`. Paper 1 is frozen and Paper 2 is unchanged.
- **Build:** the `Makefile` gets Paper 3's targets (`dist/papers/03-generation/`, and the citable
  `lavi-<year>-<slug>.pdf`); `scripts/check-corpus-citations.py` is new, with tests;
  `scripts/check-hedges.py` gets pins for Paper 3 once it is drafted.
- **Code:** `poc/generation/report.py`, for the `display` block and the report's own understated
  sections. The registered run is complete, so no run is in progress to disturb, but this is
  still checked before editing.
- **Docs:** `citations.bib` (Paper 2's entry, reserved DOI), `papers/README.md`, `AGENTS.md`,
  `docs/ROADMAP.md` (M5 started), and `prepare-paper-2-publication/publication-checklist.md`
  (commit the publication marker at upload).
