## ADDED Requirements

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
