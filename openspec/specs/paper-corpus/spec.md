# paper-corpus Specification

## Purpose
Define how the repository organises its written outputs as a longitudinal corpus of papers backed by a single
shared research artifact: where papers live and build, how a frozen paper stays faithful to the state it
records, how citation hygiene spans the corpus, and how the research methodology is documented.
## Requirements
### Requirement: Papers live in a per-paper corpus over a shared artifact
The repository SHALL organise its written outputs as a corpus of papers under a top-level `papers/`
directory, one sub-directory per paper, while the shared research artifact (graphs, scripts, runtime, tests,
and bibliography) SHALL remain at the repository root and back every paper. A paper's directory SHALL contain
its document sources; no paper SHALL require another paper's sources to build.

#### Scenario: A paper builds from the corpus
- **WHEN** the build runs
- **THEN** each paper under `papers/` produces its own output under `dist/papers/<id>/`
- **AND** the shared artifact at the repository root is used by the living paper(s) without being duplicated
  into their directories

#### Scenario: The bibliography is shared
- **WHEN** any paper cites a work
- **THEN** the citation resolves against the single top-level `citations.bib`

### Requirement: The founding vision paper is frozen and self-contained
The corpus SHALL contain the founding vision as a frozen paper that reflects the repository's state before the
executable demonstrator existed, dated as that document dated itself at the freeze point. A frozen paper SHALL
be self-contained with respect to its inputs: it SHALL carry its own copies of the figures and figure sources
it references as of the freeze, and its build SHALL read only those, so that later evolution of the shared
artifact cannot alter it.

A frozen paper SHALL be changed only by dated errata, never by silent rewriting, with a single exception: a
frozen paper MAY undergo **one editorial-and-metadata revision for the purpose of publication** (for example,
posting it as a preprint). That revision SHALL change no **prediction, hedge, or argument** of the paper —
none added, removed, strengthened, or weakened — and SHALL be otherwise limited to typographic, grammatical,
phrasing, formatting, and publication-metadata changes, correction of factually wrong details that would
otherwise be errata, and removal of incidental material that is out of place for the paper's scope (such as an
implementation-progress note).

The single publication revision SHALL be considered concluded only when the paper is actually published.
Publication-day changes that cannot exist before the publication venue's record exists — the DOI or identifier
of the record the paper is published under, and its licence statement — together with rendering-legibility
fixes to pinned figure sources, MAY be applied as the concluding step of that same single revision, even when
preparation and conclusion land as separate commits (for example because the publication venue changed between
them). Each step SHALL be recorded in the paper's errata record, the paper SHALL be re-frozen at the final
published commit, and it SHALL be errata-only thereafter. The paper SHALL NOT represent its revised text as
byte-identical to the original freeze-point text where they differ.

#### Scenario: The frozen paper does not drift with the shared artifact
- **WHEN** the shared artifact changes after the freeze (for example, a canonical graph gains new content)
- **THEN** the frozen paper's rendered figures are unchanged, because it builds only from its own pinned
  inputs

#### Scenario: A correction to a frozen paper is recorded as errata
- **WHEN** a correction to a frozen paper is required
- **THEN** it is recorded as a dated erratum rather than an in-place rewrite of the frozen text

#### Scenario: A one-time editorial revision for publication preserves every prediction
- **WHEN** a frozen paper is editorially revised for publication as a preprint
- **THEN** the revision changes only typography, phrasing, formatting, publication metadata, and incidental
  out-of-scope material, adding, removing, strengthening, or weakening no prediction, hedge, or argument
- **AND** the paper is re-frozen at the published commit and is errata-only thereafter
- **AND** the revision is recorded, and the paper does not present its revised text as identical to the
  original freeze-point text where the two differ

#### Scenario: The publication revision concludes at the actual publication event
- **WHEN** the paper is published and its record's DOI exists only at publication time
- **THEN** stamping that DOI and licence into the title block, and fixing a rendering-legibility defect in a
  pinned figure source, are the concluding step of the same single publication revision, not a second revision
- **AND** the concluding step changes no prediction, hedge, or argument, is recorded in the errata record, and
  the paper is re-frozen at the published commit and errata-only thereafter

### Requirement: Citation hygiene accounts for the whole corpus
The citation checks SHALL treat the corpus as a whole: a bibliography entry SHALL be considered used if any
paper cites it, and each paper's cross-references SHALL still be validated individually so a broken reference
in one paper fails the build.

#### Scenario: An entry used by only one paper is not flagged as orphaned
- **WHEN** an entry in the shared bibliography is cited by one paper but not another
- **THEN** the orphaned-entry check does not flag it

#### Scenario: A broken reference in one paper fails the build
- **WHEN** a paper contains a cross-reference that does not resolve
- **THEN** that paper's build fails

### Requirement: The research methodology is documented honestly
The repository SHALL document its research methodology in a top-level record that states the division of
authority — human-directed, AI-executed, spec-driven through OpenSpec — and points to the git history and
change proposals as the evidence trail. The record SHALL NOT claim autonomous research.

#### Scenario: The methodology record states the division of authority
- **WHEN** a reader consults the methodology record
- **THEN** it identifies the human as the director who sets scope and decisions and the AI agent as the
  instrument that executes them, and references the git history and `openspec/changes/` as evidence

### Requirement: The demonstrator paper is in paper form and positions against the vision
The demonstrator paper SHALL be structured as a paper — an abstract, an introduction stating a falsifiable
central claim scoped to what the artifact substantiates, and design, implementation, evaluation, related-work,
research-agenda, and conclusion sections. It SHALL include an evaluation section whose figures and verdicts
are drawn from the generated evaluation artifact rather than hand-transcribed. It SHALL position itself against
the frozen vision paper by stating, for the vision's predictions, which the demonstrator substantiates and
which remain conditional, citing the vision as the archived original. It SHALL preserve the project's hedging
discipline: a claim is stated in present tense only where the artifact backs it.

#### Scenario: The demonstrator paper carries an artifact-sourced evaluation
- **WHEN** the demonstrator paper is built
- **THEN** it contains an evaluation section whose figures and verdicts come from the generated evaluation
  artifact

#### Scenario: The demonstrator paper distinguishes substantiated from open predictions
- **WHEN** a reader consults the demonstrator paper
- **THEN** it references the frozen vision paper and states which of the vision's predictions are substantiated
  by the artifact and which remain conditional

#### Scenario: Unproven claims stay hedged
- **WHEN** the paper states a property the artifact does not establish (for example, noninterference soundness)
- **THEN** that property is expressed conditionally rather than as an achieved result

### Requirement: The demonstrator paper reports the inspector without overclaiming the editor prediction

The demonstrator paper SHALL report the graph inspector in its implementation section and SHALL update the predictions-and-outcomes accounting to record the visual-editor/tooling prediction as at most **partially** substantiated, stating in the same passage that the inspector views and runs graphs but does not author them, and that graph authoring from the UI remains open in the research agenda. Any paper statement about the inspector's behavior SHALL correspond to a tested requirement of the `graph-inspector` capability.

#### Scenario: The verdict stays bounded

- **WHEN** the paper's §5 accounting describes the tooling prediction after the inspector lands
- **THEN** the verdict is partial, the inspector-not-editor restriction appears with it, and no passage upgrades the visual-editor prediction to substantiated

#### Scenario: Paper claims about the inspector are backed

- **WHEN** the paper asserts a behavior of the inspector (rendering from canonical sources, server-side execution, taint visibility)
- **THEN** that behavior is pinned by a requirement and test in the `graph-inspector` capability, in the same claims-backed-by-artifact discipline as §3 and §4
