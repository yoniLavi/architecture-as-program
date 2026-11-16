# spec-workflow Specification

## Purpose
How the repository keeps its own specifications sound: every standing spec and open change
validates strictly, every archived change passes the archive lint, and one command checks both,
run before each commit wherever the OpenSpec CLI is installed and never needed by the corpus
build.

## Requirements

### Requirement: Standing specs and changes validate strictly
Every standing spec and every open change SHALL pass `openspec validate --strict`, and every
archived change SHALL pass the archive lint. The repository SHALL provide one command that runs
both checks and fails if either does, and a pre-commit hook SHALL run it wherever the
`openspec` binary is on `PATH`. The corpus build SHALL NOT depend on it.

#### Scenario: A requirement outgrows the limit
- **WHEN** a requirement's text before its first scenario exceeds the validator's limit
- **THEN** the check fails and names the spec and the requirement
- **AND** the fix moves text into scenarios or splits the requirement, and drops no
  normative sentence

#### Scenario: A new capability is archived
- **WHEN** a change that adds a capability is archived
- **THEN** the new spec's Purpose is written in the same commit, and the check passes

#### Scenario: The corpus is built without the OpenSpec CLI
- **WHEN** `make build` runs on a machine with no `openspec` binary
- **THEN** the build passes
