## ADDED Requirements

### Requirement: The grants paper states its runs as exploratory
The grants paper SHALL label every result it reports as exploratory and unregistered, SHALL state counts and never rates, and SHALL NOT present a refused attack as a defence without the pinned limit that bounds it in the same paragraph.

#### Scenario: Provenance's refusals are cited
- **WHEN** the paper states that every attacker payment was refused
- **THEN** the same paragraph states that an injected value equal to a known payee is paid, and the cost to legitimate payments

### Requirement: The grants paper's figures are interpolated from its artifact
Every figure in the grants paper, counts of things in the data included, SHALL be interpolated from `dist/grants.json`, built from committed records by a step that calls no model; Paper 4's figures SHALL be cited from Paper 4, never typed.

#### Scenario: A record changes
- **WHEN** a committed record changes a figure the paper states
- **THEN** the rebuilt paper states the new figure, with no edit to its text

### Requirement: The grants paper is not stamped before Paper 4 is published
The grants paper SHALL NOT carry a DOI while Paper 4 has no publication marker, because a published paper cites no unpublished work.

#### Scenario: A stamp before Paper 4
- **WHEN** a DOI is added to the grants paper while Paper 4 has no `RECORD.json`
- **THEN** the corpus citation check fails the build
