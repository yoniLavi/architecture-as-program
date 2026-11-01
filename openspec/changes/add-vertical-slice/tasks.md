# Tasks

Every session working on this change first checks the feed recorder (standing task 0.3 of
`strengthen-generation-evidence`) and `git status`. Long runs go at low priority. Edit
nothing a run imports while it runs.

## 0. Approval

- [x] 0.1 **The author approves this proposal** and answers the five questions in `design.md`
      (1 November 2026: every recommendation taken; recorded in `design.md`)

## 1. Steps 2 and 3: the custom node and the shadow link check

- [x] 1.1 The `Custom` library entry: role, signature and clause, no body; the library check;
      the catalogue's wording, which says when to use it. In `SLICE_CATALOGUE` only, so the
      registered run's hashed text is unchanged (a test now holds it reproducible); `author`
      takes a `custom` flag, not a catalogue, so no content can arrive by it. Holds a reader's
      `DBHandle`, `LLMClient<inference>`, or a banking writer kind; may not discharge trust;
      its output is `Untrusted` if it reads the bank or any untrusted input
- [ ] 1.2 The scope-binding link check, in shadow mode, replayed over the registered
      records. Reported, never enforced

## 2. Step 4: the chosen reviewer candidate(s)

- [ ] 2.1 As the author chose in 0.1. If behaviour is shown, the writers' possible values come
      from the predictions' taint analysis

## 3. Step 5: the developer and escalation

- [ ] 3.1 The developer step, using Paper 3's pipeline for custom nodes, held to the gate
- [ ] 3.2 Escalation as a graph edit request, reviewed again by steps 3 and 4. Never text
      that grants anything
- [ ] 3.3 The pretext condition, if chosen

## 4. Steps 6–8

- [ ] 4.1 The crude minimiser and its report
- [ ] 4.2 The human-review page, and a committed verdict file per graph
- [ ] 4.3 **The author's verdicts**, steps 7 and 8

## 5. The run and its findings

- [ ] 5.1 The slice on the chosen tasks, recorded whole
- [ ] 5.2 `dist/slice.md` from the records; a findings entry in `docs/ROADMAP.md`
- [ ] 5.3 Then, by the author's sequence: update Paper 3 and the Paper 4 proposal, then a
      final pass to publish Paper 3
