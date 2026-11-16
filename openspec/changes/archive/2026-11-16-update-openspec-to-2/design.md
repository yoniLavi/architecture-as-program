# Design: OpenSpec 2.0 and strictly valid specs

## Decisions proposed

### 1. Restructure the specs in place, not through MODIFIED deltas

A MODIFIED delta must carry the whole requirement, so 37 of them would restate about 30,000
characters of spec to change none of its meaning, and a reviewer could not see what moved.
The standing specs are edited directly instead, one spec per commit, so that `git diff
--color-moved` shows each sentence leaving the requirement body and arriving in a scenario.

This departs from "specs change through deltas". The reason it is safe is that no
requirement changes; the reason it is stated is that the departure should not become a habit.
The change's one delta is the new `spec-workflow` requirement.

*Alternative considered:* 37 MODIFIED deltas. Rejected for the reason above, and because a
header changed by a split would need a RENAMED block as well (the lesson of
`openspec-rename-requires-renamed-block`).

### 2. How a long requirement is cut

In order of preference:

1. **Move conditions and cases into scenarios.** Most of the excess is "when X, then Y"
   written as prose, or a list of cases. Each becomes a `#### Scenario:` under the same
   requirement, and keeps its wording.
2. **Split** where a requirement states two behaviours. The new requirement goes directly
   after the old one, and its name says which half it is.
3. **Leave history out of the requirement.** A sentence that records why or when ("an
   adversarial review on 30 September found…") is not a requirement. It moves to a
   scenario's context line if the scenario needs it, and otherwise stays in the archived
   change that introduced it, which already holds it. Every such sentence is listed in the
   commit message, so the author can object to one.

A requirement name is not changed unless it is split, because open changes, tests and
`AGENTS.md` refer to requirements by name.

### 3. The comparison script

`scripts/check-spec-restructure.py` (stdlib-only, used during this change and then kept
under `scripts/` only if the author wants it). It takes a spec before and after. It extracts
every sentence containing `SHALL` or `MUST`, normalises whitespace, and fails if a sentence
present before is absent after.

What it cannot see, stated: a sentence moved under a scenario whose WHEN narrows it; two
sentences whose order carried meaning; a non-normative sentence that bounded a normative one
(the specs' equivalent of a hedge). Those rest on reading each diff, which is why the work is
one spec per commit.

### 4. `make spec-check` is opt-in

The corpus build needs no Node, and that is tested. The OpenSpec CLI is an npm package. So
the check is a Makefile target the author and each session run, and not a `make build` step
or a pre-commit hook. `openspec install` offers a standalone binary that runs without Node;
whether that is enough to put the check in pre-commit is open question 2.

### 5. The migration is taken as the tool gives it, then read

`openspec update --force` is run once, and its diff is read before the commit. Three things
are checked by hand, because the tool cannot know them:

- `CLAUDE.md` is a symlink to `AGENTS.md`, and the dry run lists both as "update". The
  symlink must survive, and the block must be written once.
- The managed block in `AGENTS.md` tells agents to open `openspec/AGENTS.md`, which the
  update deletes. Whatever replaces it must still tell a session to plan through OpenSpec.
- `openspec/AGENTS.md` holds two conventions this repository relies on and that the 2.0
  skills may not state: changes are validated with `--strict` before approval, and nothing is
  implemented before the author approves. If the skills do not carry them, they move into
  the repository's own `AGENTS.md`, under "Spec-driven development".

## Risks

- **Meaning drifts in a move.** See decision 3. The specs most exposed are `paper-corpus`
  (claim discipline for published papers) and `trust-typing`.
- **The 2.0 skills change how a session proposes work**, for example by a different artifact
  order or a default schema. The five open changes were written in the old shape. They
  validate today, and task 4.1 re-validates them after the migration. If 2.0 wants a
  different shape for a change in flight, that is reported and the open changes are left
  alone.
- **A capability first archived after this change gets a placeholder Purpose again.** Three
  open changes add new capabilities (`vertical-slice`, `node-generation`,
  `feed-triage-service`). Task 4.2 adds a line to each one's archive step.

## Open questions for the author

1. **In place, or by delta?** Decision 1 proposes in place. Say if the convention should
   hold even here.
2. **Should strict validation gate commits?** Proposed: no, opt-in. The alternative is a
   pre-commit hook that runs only when the `openspec` binary is on `PATH`, and skips
   otherwise, as the pandoc-gated tests do.
3. **Keep the comparison script?** It is only useful again if specs are restructured again.
   Proposed: delete it at archive, and leave it in the history.
4. **History sentences** (decision 2, rule 3). Proposed: they leave the requirement. If any
   should stay in the standing spec, the place is a scenario's context line.

## Answers (the author, 16 November 2026)

1. **In place.** As proposed.
2. **Gate commits.** Against the proposal: a pre-commit hook runs `make spec-check` when the
   `openspec` binary is on `PATH`, and skips otherwise. The author added that `make
   ui-check` should join pre-commit too unless it is very slow. It takes about 10 seconds,
   so it does, scoped to changes under `ui/` and skipped when `npm` is absent. Decision 4's
   reason still holds for `make build`: neither check is a build step, and the corpus still
   builds with no Node.
3. **Delete the script at archive.** As proposed.
4. **History sentences leave the requirement.** As proposed.
