# Move the repository to OpenSpec 2.0 and make its specs validate strictly

> **Status: proposed, 16 November 2026. Not approved. Nothing is migrated until it is.**

## Why

The installed CLI is already OpenSpec 2.0.0, the latest release. The repository is not: its
instruction files are the pre-2.0 layout, and its standing specs fail strict validation.
Measured on 16 November 2026 (`80f34ac`):

- `openspec doctor` reports the root **unhealthy**: there is no `openspec/config.yaml`.
- `openspec update --dry-run --force` plans 19 file changes. It deletes `openspec/AGENTS.md`
  and the three `.claude/commands/openspec/*.md` commands, adds six skills under
  `.agents/skills/` and `.claude/skills/`, and rewrites the managed block in `AGENTS.md`.
- `openspec validate --all --strict` fails 6 of 7 standing specs, on warnings only:
  - **37 requirements are longer than 500 characters** before their first scenario
    (signal-graph-runtime 17, paper-corpus 9, evaluation 5, trust-typing 4,
    architect-pipeline 2). The longest is 2,268 characters.
  - **3 specs still carry the placeholder Purpose** that `openspec archive` writes
    (architect-pipeline, graph-inspector, trust-typing).
- `openspec validate --archived` fails 2 archived changes, each with one unticked task
  (`2026-07-14-add-signal-graph-runtime`, `2026-08-01-update-papers-after-corpus-review`).

The five open changes validate strictly today. But a change proposed against a spec that
fails is validated against a moving floor, and the archive of `add-paper-3` showed the cost:
its delta was approved clean in October and "has issues" in November, with no edit between.

## What Changes

- **Instruction files move to the 2.0 layout** by `openspec update --force`, reviewed as a
  diff before it is committed. `openspec/config.yaml` is added, so `doctor` reports healthy.
  The repository's own `AGENTS.md` text outside the managed block is not touched, and every
  place that points a reader at `openspec/AGENTS.md` is repointed.
- **The 37 long requirements are restructured, not shortened.** Each keeps a statement under
  500 characters with its `SHALL`. The rest moves into scenarios of the same requirement or
  into a new requirement beside it. No normative sentence is dropped, weakened or reworded
  beyond what the move needs. A script compares the normative sentences before and after
  and must report none missing.
- **The three placeholder Purposes are written**, each from what its spec actually holds.
- **The two archived changes' open tasks are annotated**, not ticked: each gets a dated note
  saying why it was left, so the archive lint passes without claiming work that was not done.
  If the lint needs a tick, the note says the task was closed as not done.
- **A check keeps it that way**: `make spec-check` runs `openspec validate --all --strict`
  and `openspec validate --archived`. It is opt-in, like `make ui-check`, because the CLI
  needs Node and the corpus build must not.
- **The open changes are updated** where the migration touches them (`tasks.md`, phase 4).

**Not in this change:**
- any change to what a spec requires. This is format and tooling;
- any paper, figure, graph, harness or test of the artifact;
- adopting 2.0's stores, worksets or custom schemas;
- raising or disabling the 500-character limit. If it turns out to be configurable, that is
  reported to the author as an option and not taken.

## Impact

- **Specs:** a new capability, `spec-workflow`, with one requirement (strict validity, and
  the opt-in check). Six standing specs are restructured in place.
- **Files:** `openspec/config.yaml` (new); `.agents/skills/`, `.claude/skills/` (new);
  `openspec/AGENTS.md` and `.claude/commands/openspec/` (deleted); `AGENTS.md` (managed
  block, and its pointers); `Makefile` (`spec-check`); `METHODOLOGY.md` and
  `openspec/project.md` if they name the old files.
- **Risk:** a restructuring that changes a requirement's meaning. The specs hold the papers'
  claim discipline, so the comparison script and a read of each moved passage are the
  guard, and `design.md` says what the script cannot see.
