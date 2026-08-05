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

### Requirement: The demonstrator paper is in paper form and reports what the artifact establishes
The demonstrator paper SHALL be structured as a paper — an abstract, an introduction stating a falsifiable
central claim scoped to what the artifact substantiates, and design, implementation, evaluation,
related-work, threats-to-validity, and conclusion sections. It SHALL include an evaluation section whose
figures and verdicts are drawn from the generated evaluation artifact rather than hand-transcribed. It SHALL
preserve the project's hedging discipline: a claim is stated in present tense only where the artifact backs
it.

The demonstrator paper SHALL NOT carry the corpus's predictions-and-outcomes accounting, which belongs to the
method paper; it SHALL instead state concisely what it does and does not substantiate, and cite the method
paper for the accounting. It SHALL position itself against the prior art for LLM-agent security, including
capability- and provenance-based defences against prompt injection, wherever it claims prompt-injection
attenuation.

#### Scenario: The demonstrator paper carries an artifact-sourced evaluation
- **WHEN** the demonstrator paper is built
- **THEN** it contains an evaluation section whose figures and verdicts come from the generated evaluation
  artifact

#### Scenario: The accounting has exactly one owner
- **WHEN** a reader looks for the predictions-and-outcomes accounting
- **THEN** it appears in the method paper only, and the demonstrator paper cites it rather than restating it

#### Scenario: Prompt-injection claims engage the prior art
- **WHEN** the demonstrator paper claims prompt injection is attenuated
- **THEN** it cites and positions against existing capability- or provenance-based prompt-injection defences
  rather than claiming the problem is unaddressed

#### Scenario: Unproven claims stay hedged
- **WHEN** the paper states a property the artifact does not establish (for example, noninterference soundness)
- **THEN** that property is expressed conditionally rather than as an achieved result

### Requirement: Demonstration interfaces are reported as a mention, not as a contribution
A paper SHALL report a demonstration interface (such as the graph inspector) as a brief mention within the
section covering the underlying artifact, and SHALL NOT give it a dedicated section or list it as a
contribution. Any statement a paper makes about such an interface SHALL still correspond to a tested
requirement of the capability that provides it.

A demonstration interface SHALL NOT raise the verdict of any prediction in the predictions-and-outcomes
accounting. Where an interface partially exercises a predicted capability, the verdict SHALL follow the
underlying capability, and the interface MAY be noted alongside it.

#### Scenario: An interface gets a mention, not a section
- **WHEN** a paper reports a demonstration interface
- **THEN** it appears as a mention within an existing section, with at most one figure, and is absent from the
  contributions list

#### Scenario: A demo does not move a verdict
- **WHEN** the accounting records a prediction that a demonstration interface partially exercises (for example,
  the visual graph editor)
- **THEN** the verdict reflects the underlying capability — authoring, in that example — and the interface is
  noted rather than credited

### Requirement: The corpus separates evidence from accounting across two living papers
The corpus SHALL contain two living papers with distinct claims: a **demonstrator paper** reporting what the
artifact establishes, and a **method paper** reporting the research protocol and the accounting of the frozen
vision's predictions against the artifact. Each SHALL state a single central claim and SHALL be readable
without the other, with cross-citation rather than restatement.

The method paper SHALL NOT interpolate evaluation data; it SHALL cite the demonstrator paper for every figure
and measurement it refers to, so exactly one paper is the source of any given number.

#### Scenario: Each living paper carries one claim
- **WHEN** either living paper is built
- **THEN** its introduction states one central claim, and material serving the other paper's claim is cited
  rather than reproduced

#### Scenario: Only the demonstrator paper sources evaluation figures
- **WHEN** the method paper refers to a measurement from the artifact
- **THEN** it cites the demonstrator paper rather than interpolating the evaluation artifact itself

### Requirement: The method paper documents the pre-registration protocol and its mechanisation
The method paper SHALL describe the protocol by which the corpus records predictions before building —
freezing the founding vision, publishing it under a citable identifier, guarding it against silent edit by an
automated check in the build, permitting only dated errata, and reporting outcomes prediction by prediction
without revising the predictions. It SHALL present that protocol's **mechanisation** as its contribution and
the corpus's own history as one worked instance, and SHALL state the limits of generalising from a single
instance.

#### Scenario: The protocol is described with its enforcement
- **WHEN** a reader consults the method paper
- **THEN** it describes both the protocol and the automated check that enforces the freeze, rather than
  describing the protocol as an intention

#### Scenario: Single-instance generalisation is bounded
- **WHEN** the method paper draws conclusions from the corpus's own history
- **THEN** it states that the evidence is one instance and does not claim the protocol is validated generally

### Requirement: No paper states that the artifact lacks a capability the artifact has
Every living paper SHALL describe the artifact's capabilities as they stand at build time. A
paper SHALL NOT state that the demonstrator lacks a capability it has; where a capability
exists but is weaker than the corpus once anticipated, the paper SHALL state the *restriction*
rather than the absence.

This closes the gap the corpus's other guards leave open. Interpolation prevents a *number*
from drifting and pinned verdicts prevent a *mechanism* from silently regressing, but a
sentence asserting an absence stays green forever after the thing is built. When a change adds
a capability, correcting every "the demonstrator has no X" claim across both living papers is
part of that change, not a later sweep.

#### Scenario: A newly built capability is swept through the prose

- **WHEN** a change gives the artifact a capability a living paper previously described as
  absent, undesigned, or unbuilt
- **THEN** that change also replaces each such statement with the capability's actual
  restriction, in both living papers

#### Scenario: An accounting verdict reflects the artifact

- **WHEN** the accounting records a prediction as *conditional* or *not attempted*
- **THEN** no evidence for that prediction exists in the artifact at build time; a prediction
  the artifact has partial evidence for is recorded as *partial* with its restriction stated

### Requirement: No paper states a measured magnitude in its own hand
No paper in the corpus SHALL state the magnitude of a measured figure — "tens of microseconds",
"single-digit milliseconds" — as hand-maintained prose. A magnitude is a claim about a measurement
exactly as the figure is, and a hand-typed magnitude beside an interpolated figure is the same defect
as a hand-typed count beside an interpolated one: it stays green while the data moves underneath it.
Such a magnitude SHALL be interpolated from the evaluation artifact.

The one-owner-per-number rule SHALL apply to magnitudes as it applies to figures: the method paper
SHALL cite the demonstrator paper for a magnitude rather than stating one in its own voice.

#### Scenario: A magnitude in the demonstrator paper is interpolated
- **WHEN** the demonstrator paper states the magnitude of a measured figure anywhere, including
  outside its evaluation section
- **THEN** that magnitude is interpolated from the evaluation artifact rather than typed

#### Scenario: The method paper cites rather than states a magnitude
- **WHEN** the method paper refers to the magnitude of a demonstrator measurement
- **THEN** it cites the demonstrator paper for it and states no magnitude in its own voice

### Requirement: A falsifiable central claim rests on properties a reader can re-derive
The demonstrator paper's central claim SHALL be scoped to properties of the artifact that a reader can
re-derive from the repository. A single-machine wall-clock measurement, particularly one obtained by
differencing two timings, SHALL NOT be a component of the central claim, because it can be falsified by
the conditions of the reader's machine rather than by the artifact. Such a measurement SHALL be reported
as a supporting result in the evaluation section instead.

#### Scenario: The claim block excludes a fragile measurement
- **WHEN** a reader reads the demonstrator paper's central claim
- **THEN** every component of it is a property of the artifact, and the measured overhead is reported
  in the evaluation section rather than asserted in the claim

### Requirement: A stated limitation tracks the artifact's current behaviour
A limitation a paper states SHALL describe the artifact as it now behaves, not only a fault that has
since been corrected. Where a correction bounded a fault without removing the underlying weakness, the
paper SHALL state the residue and what now bounds it, so that a reader is not left believing a live
fragility was retired.

#### Scenario: A corrected fault does not conceal a live one
- **WHEN** a paper describes a measurement defect that was corrected
- **THEN** it also states whether the underlying fragility remains and what bounds it now
