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
predictions-and-outcomes, related-work, threats-to-validity, and conclusion sections. It SHALL include an
evaluation section whose figures and verdicts are drawn from the generated evaluation artifact rather than
hand-transcribed. It SHALL preserve the project's hedging discipline: a claim is stated in present tense only
where the artifact backs it.

The demonstrator paper SHALL carry the corpus's predictions-and-outcomes accounting of the frozen vision, in
condensed form: the protocol under which the vision was frozen at its last pre-build state, every prediction with its
verdict, and the design corrections the artifact forced. It SHALL position itself against the prior art for
LLM-agent security, including capability- and provenance-based defences against prompt injection, wherever it
claims prompt-injection attenuation.

#### Scenario: The demonstrator paper carries an artifact-sourced evaluation
- **WHEN** the demonstrator paper is built
- **THEN** it contains an evaluation section whose figures and verdicts come from the generated evaluation
  artifact

#### Scenario: The accounting has exactly one owner
- **WHEN** a reader looks for the predictions-and-outcomes accounting
- **THEN** it appears in the demonstrator paper, with every prediction of the frozen vision and its verdict,
  and no other paper restates it

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

### Requirement: No paper states that the artifact lacks a capability the artifact has
Every living paper SHALL describe the artifact's capabilities as they stand at build time, or
as they stood at a commit the paper names. A paper SHALL NOT state that the demonstrator lacks
a capability it has at the point the paper describes; where a capability exists but is weaker
than the corpus once anticipated, the paper SHALL state the *restriction* rather than the
absence.

A paper that names a commit SHALL say so once, where a reader orients, and SHALL name there
the capabilities built since that it does not report, so that its statements of absence read
as dated rather than current. This is how a paper reaches a fixed published state while the
repository keeps growing; it was adopted on 29 October 2026, when the demonstrator paper,
then awaiting publication, had been overtaken by work it does not report (node-local state,
fan-in, a generative contract mode, generated bodies at scale). The alternative, sweeping each
absence into a restriction, would have moved verdicts in the accounting on evidence the paper
does not present.

This closes the gap the corpus's other guards leave open. Interpolation prevents a *number*
from drifting and pinned verdicts prevent a *mechanism* from silently regressing, but a
sentence asserting an absence stays green forever after the thing is built. When a change adds
a capability, correcting every "the demonstrator has no X" claim in every living paper that
describes the artifact at build time is part of that change, not a later sweep.

This requirement rests on review and no check enforces it, which is recorded here because it
has already failed once undetected: the change that built principal binding left three passages
of the demonstrator paper (§2.3, and §2.5 twice, in its August 2026 numbering) calling the binding *undesigned*, and they were
found four days later by a tightening pass that had no mandate to look for them. The evaluation
harness guards only the *overstating* direction — a paper cannot claim what the artifact cannot
do, because the harness runs the artifact — and there is no artifact against which to decide
that a sentence understates. The sweep is therefore a step in any change that lands a
capability, and the absence of a check on it SHALL stay stated rather than assumed.

#### Scenario: A newly built capability is swept through the prose

- **WHEN** a change gives the artifact a capability a living paper previously described as
  absent, undesigned, or unbuilt, and that paper describes the artifact at build time
- **THEN** that change also replaces each such statement with the capability's actual
  restriction, in every such paper

#### Scenario: A paper dated to a commit

- **WHEN** a living paper names the commit it describes
- **THEN** it says so once, where a reader orients, and names the capabilities built since
  that it does not report
- **AND** its statements of absence and its accounting verdicts are read as of that commit

#### Scenario: An accounting verdict reflects the artifact

- **WHEN** the accounting records a prediction as *conditional* or *not attempted*
- **THEN** no evidence for that prediction exists in the artifact at the point the paper
  describes; a prediction the artifact has partial evidence for is recorded as *partial* with
  its restriction stated

#### Scenario: The understating direction is known to be unguarded

- **WHEN** the corpus's drift guards are described, in documentation or in a paper
- **THEN** the overstating direction is attributed to the evaluation harness and the
  understating direction to the per-change sweep, rather than both being left to look checked

### Requirement: No paper states a measured magnitude in its own hand
No paper in the corpus SHALL state the magnitude of a measured figure — "tens of microseconds",
"single-digit milliseconds" — as hand-maintained prose. A magnitude is a claim about a measurement
exactly as the figure is, and a hand-typed magnitude beside an interpolated figure is the same defect
as a hand-typed count beside an interpolated one: it stays green while the data moves underneath it.
Such a magnitude SHALL be interpolated from the evaluation artifact.

A later corpus paper that does not itself source a measurement SHALL cite the published paper that does
rather than state a magnitude in its own voice.

#### Scenario: A magnitude in the demonstrator paper is interpolated
- **WHEN** the demonstrator paper states the magnitude of a measured figure anywhere, including
  outside its evaluation section
- **THEN** that magnitude is interpolated from the evaluation artifact rather than typed

#### Scenario: The method paper cites rather than states a magnitude
- **WHEN** a later corpus paper (a methods paper, or a successor to the demonstrator) refers to the
  magnitude of a measurement the demonstrator paper sources
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

### Requirement: A revision preserves the hedging of the passage it revises
A revision of a passage stating an unproven property SHALL preserve that passage's hedging: the
conditional mood, and the tier restriction where a property holds only on the confined tier. Length
work SHALL NOT be paid for out of qualification. Where a rewrite cannot meet a length target without
weakening a hedge, the hedge SHALL win and the target SHALL be missed, because length is a target and
hedging is a claim.

This applies with most force to the demonstrator paper's design section, which describes intent inside
a paper otherwise written in the present tense, so a claim there reads as substantiated unless its mood
is deliberately kept conditional.

#### Scenario: A shortened passage keeps its qualification
- **WHEN** a passage stating an unproven property is rewritten shorter
- **THEN** every conditional marker and tier restriction it carried still qualifies the claim it
  qualified before

#### Scenario: A length target yields to a hedge
- **WHEN** a rewrite cannot reach its word target without weakening a hedge
- **THEN** the target is missed and the hedge is kept

### Requirement: The corpus states whether a discipline is checked or merely obliged
Where the corpus relies on a drafting discipline, it SHALL record whether that discipline is enforced by
a check or rests on review. A discipline believed to be checked when it is not is worse than one known
to rest on review, because a reader and an editor both stop looking. Where a guard exists over a
discipline that cannot be checked completely, no paper SHALL describe it as more than a regression
guard over the passages it pins.

#### Scenario: An unmechanised discipline is named as such
- **WHEN** the corpus relies on a discipline no check enforces
- **THEN** that is recorded as a review obligation rather than left to look like a guarantee

#### Scenario: A partial guard is not described as a complete one
- **WHEN** a paper or the corpus documentation refers to a guard over a drafting discipline
- **THEN** it states that the guard covers the passages it pins and not the property in general

### Requirement: A published frozen paper is served from its published artifacts
A frozen paper that has been published SHALL carry a machine-readable publication marker recording its
identifier, its record, its publication date, the source commit it was published from, the record's own
checksum of the published file, and a checksum for every artifact the corpus serves for it. The build SHALL
serve those stored artifacts rather than regenerate them, so that no shared build input — filter,
citation style, bibliography, or toolchain version — can alter what readers of a published paper receive.
The published PDF SHALL be the record's file byte-for-byte. The freeze guard SHALL fail the build if a
stored artifact is missing, differs from its recorded checksum, or is present but unlisted, or if the
published PDF no longer matches the record's checksum.

Derived web renderings of a published paper MAY be regenerated at most by a deliberate, author-approved
act recorded in the paper's errata record, and SHALL NOT change as a side effect of any other change.

#### Scenario: A shared build input changes
- **WHEN** a filter, citation style, bibliography entry, or toolchain version used by the living papers changes
- **THEN** the published paper's served PDF, Markdown, HTML, and figures are byte-identical to its stored
  artifacts, because the build copies rather than regenerates them

#### Scenario: A stored artifact is altered
- **WHEN** a stored artifact of a published paper differs from the checksum in its publication marker, is
  missing, or an unlisted file appears beside it
- **THEN** the freeze guard fails the build

#### Scenario: The served PDF is the record
- **WHEN** the corpus is built
- **THEN** the published paper's PDF has the checksum the publication record states for its file

### Requirement: A published paper cites no unpublished work
A paper that is published under a persistent identifier SHALL NOT cite work that has no published record.
A citation of work in preparation cannot be followed by a reader, and between two papers of the corpus it
creates a dependency that forces them to publish in an order neither can satisfy. Where a published paper
needs material that is not yet published, it SHALL state that material, or its absence, in its own voice.

#### Scenario: The paper is prepared for publication
- **WHEN** a corpus paper is stamped with its identifier for publication
- **THEN** every entry in its bibliography has a published record, and none is marked in preparation

### Requirement: Text quoted out of context states a measurement's magnitude, not one run's value
The demonstrator paper's abstract and conclusion SHALL state a single-machine measurement as its
interpolated magnitude rather than as the value one run produced. Those passages are the ones
quoted without their evaluation section — an archive record takes the abstract verbatim — so a
per-run value there becomes a fixed claim that the next build contradicts. The per-run value
SHALL remain in the evaluation section, beside the environment that produced it.

#### Scenario: The abstract names a magnitude
- **WHEN** the abstract or conclusion refers to the capability-crossing cost
- **THEN** it interpolates the magnitude from the evaluation artifact, and the per-run value
  appears only in the evaluation section

### Requirement: A claim about what architecture models do not do is scoped against the strongest precedent
No living paper SHALL state as universal that architecture models do not constrain the artifacts
built from them. Where a paper makes that contrast, it SHALL scope it, and the related-work
section SHALL cite and distinguish the strongest known precedent in which an architecture
description does determine authority — currently seL4's CAmkES and capDL, whose correspondence
is proved rather than tested — stating where that precedent is the stronger result.

#### Scenario: The contrast is scoped and the precedent is cited
- **WHEN** a reader reads the demonstrator paper's abstract, conclusion, or related work
- **THEN** the claim that architecture models describe but do not constrain is scoped, and
  CAmkES/capDL is cited with the difference and its greater strength stated
