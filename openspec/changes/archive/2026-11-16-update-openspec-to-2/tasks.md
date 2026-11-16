# Tasks

Before any edit, check `git status`, and that no generation, architect or baseline run is in
progress. This change edits nothing under `poc/`, `scripts/` (but for one new script) or
`graphs/`, so the feed recorder may keep running.

## 0. Approval

- [x] 0.1 **The author approves this proposal** and answers `design.md`'s open questions
      (in place or by delta; whether the check gates commits; the script's fate; history
      sentences). Approved 16 November 2026; answers recorded in `design.md`. Q2 was
      answered against the proposal: the check gates commits, and `make ui-check` joins
      pre-commit too (tasks 3.2a, 3.2b)

## 1. The instruction files

- [x] 1.1 Record the starting point in the commit message: `openspec --version`,
      `openspec doctor`, and the totals of `openspec validate --all --strict` and
      `--archived`
- [x] 1.2 `openspec update --force`. Read the whole diff before staging anything
- [x] 1.3 Check by hand (design, decision 5): `CLAUDE.md` is still a symlink to `AGENTS.md`;
      the managed block is written once; the repository's own text in `AGENTS.md` is
      byte-identical outside the block. *As found: 2.0 writes no managed block at all; it
      removed the old one and left a blank first line, which was dropped. The symlink
      survived. Outside the block only the OpenSpec paragraph and the Build list changed
      (1.5, 3.2)*
- [x] 1.4 `openspec/config.yaml`, so that `openspec doctor` reports the root healthy. *The
      update asked for `openspec/project.md` to be migrated into it and then deleted. It
      was: its still-true content became `context`, and the rest was stale (it said the
      repo commits only when asked, and named Technical Note A)*
- [x] 1.5 Carry over what `openspec/AGENTS.md` held and the 2.0 skills do not: strict
      validation before approval, and no implementation before approval. Into `AGENTS.md`,
      "Spec-driven development", and into `config.yaml`'s rules
- [x] 1.6 Repoint every reference to `openspec/AGENTS.md` and to the `/openspec:*` commands:
      `AGENTS.md`, `METHODOLOGY.md`, `openspec/project.md`, `README.md`, `papers/README.md`.
      Archived changes are history and are left as written. Frozen and published papers are
      not touched. *Only `AGENTS.md` named them; `METHODOLOGY.md` gained the 2.0 sentence*
- [x] 1.7 `make build` green. Commit

## 2. The standing specs

One spec per commit. For each: restructure, run the comparison script, read the diff with
`--color-moved`, run `openspec validate <spec> --type spec --strict`, and list in the commit
message every sentence that left a requirement without arriving in a scenario.

- [x] 2.1 `scripts/check-spec-restructure.py` and its test: a dropped normative sentence
      fails; a moved one passes; a reworded one fails
- [x] 2.2 `architect-pipeline`: 2 requirements, and its Purpose
- [x] 2.3 `trust-typing`: 4 requirements, and its Purpose
- [x] 2.4 `evaluation`: 5 requirements
- [x] 2.5 `paper-corpus`: 9 requirements. The two that `add-paper-3` added on 16 November
      are among them. *One split, the only one in the change*
- [x] 2.6 `signal-graph-runtime`: 17 requirements
- [x] 2.7 `graph-inspector`: its Purpose
- [x] 2.8 `openspec validate --specs --strict`: 7 of 7 pass

## 3. The archive, and the check

- [x] 3.1 `2026-07-14-add-signal-graph-runtime` and
      `2026-08-01-update-papers-after-corpus-review`: read each unticked task, and annotate it
      with a dated note saying what became of it. Tick it only if the work was in fact done
      later, with the commit named. *The first was `[~]` (adjusted, and done as adjusted);
      the second was closed as not done in its change, and the note names `4916d49`, the
      archive of the merge that later cut Paper 2's length*
- [x] 3.2 `make spec-check`: `openspec validate --all --strict` and
      `openspec validate --archived`, failing on either. Listed in `AGENTS.md` under Build
- [x] 3.2a A pre-commit hook runs `make spec-check` when the `openspec` binary is on `PATH`
      and skips with a message otherwise (author, Q2). Added only once 3.3 is green, so it
      never blocks the commits that make it green
- [x] 3.2b A pre-commit hook runs `make ui-check` on changes under `ui/` (author, Q2; it
      takes ~10s), and skips with a message when `npm` is absent, so a clone without Node
      can still commit
- [x] 3.3 `make spec-check` green

## 4. The open changes

- [x] 4.1 Re-validate each with `--strict` after phase 1 and again after phase 2:
      `add-paper-4`, `add-vertical-slice`, `strengthen-generation-evidence`,
      `build-feed-triage-and-generation-experiment`. If 2.0 wants a different shape for a
      change in flight, report it and leave the change alone. *All valid both times; 2.0
      asked for no different shape*
- [x] 4.2 `add-vertical-slice`, `strengthen-generation-evidence` and
      `build-feed-triage-and-generation-experiment` each add a new capability. Add to each
      one's archive task: write the new spec's Purpose in the same commit, and run
      `make spec-check`. *None had an archive task, so each gained one*
- [x] 4.3 Any added requirement in an open change that is over 500 characters is restructured
      by the same rules, so that it does not fail the standing spec at archive. *None was*
- [x] 4.4 Repoint any reference in an open change's `tasks.md` to `openspec/AGENTS.md` or an
      `/openspec:*` command. *None existed*

## 5. Close

- [x] 5.1 `AGENTS.md` (the OpenSpec section, Key files, Build) and `METHODOLOGY.md` describe
      the 2.0 layout and the check
- [x] 5.2 Delete or keep the comparison script, as the author decided. *Deleted, with its
      test; it is in the history at `4cd94e1`*
- [x] 5.3 `make build` and `make spec-check` green. Archive, and write `spec-workflow`'s
      Purpose in the same commit
