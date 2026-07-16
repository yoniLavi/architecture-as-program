## ADDED Requirements

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
artifact cannot alter it. A frozen paper SHALL be changed only by dated errata, never by silent rewriting.

#### Scenario: The frozen paper does not drift with the shared artifact
- **WHEN** the shared artifact changes after the freeze (for example, a canonical graph gains new content)
- **THEN** the frozen paper's rendered figures are unchanged, because it builds only from its own pinned
  inputs

#### Scenario: A correction to a frozen paper is recorded as errata
- **WHEN** a correction to a frozen paper is required
- **THEN** it is recorded as a dated erratum rather than an in-place rewrite of the frozen text

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
