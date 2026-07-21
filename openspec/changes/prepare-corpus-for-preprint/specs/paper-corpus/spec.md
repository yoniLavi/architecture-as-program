## MODIFIED Requirements

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
implementation-progress note). After such a revision the paper SHALL be re-frozen at the published commit and
SHALL be errata-only thereafter. The revision SHALL be recorded (in the paper's errata record), and the paper
SHALL NOT represent its revised text as byte-identical to the original freeze-point text where they differ.

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
