# A thin vertical slice of the north star: all eight steps, crudely, on one domain

> **Status: proposed, 1 November 2026. Not approved.** It is to be built in a new session.
> The design questions in `design.md` are the author's, to settle at that session's start.
> Exploratory: not registered, and not a paper.

## Why

The north star has eight steps (`docs/ROADMAP.md`). Steps 1–4 are built and measured
(`add-architect-and-reviewers`); steps 5–8 exist only as plans. The roadmap's note of
1 November 2026 says what the measurements change. The slice tests the whole flow cheaply,
before more is built on it, so it can validate or reject the plan. By the author's process
decision, its findings go into Paper 3 and the Paper 4 proposal before Paper 3 publishes.

## What Changes

A crude end-to-end run on a few banking tasks, reusing what exists, with every step's input
and output recorded:
1. **The Product Owner's prompt**: an AgentDojo banking task, and one variant carrying a
   pretext.
2. **The architect**, unchanged, except that it may declare one **custom node**: a role, a
   signature and a `with` clause, for a step the library cannot do. The catalogue says so.
3. **The formal review**, unchanged, plus a **scope-binding link check** in shadow mode: a
   grant's literal payees and cap must appear in its quote. It is reported, not enforced, and
   is also replayed over the registered records.
4. **The AI reviewer**, unchanged, plus one of the roadmap's step-4 candidates, chosen by the
   author.
5. **A developer** writes each custom node's body, using Paper 3's generation pipeline
   (signature, contract, types, the vocabulary without worlds), held to the derived import
   gate. It may **escalate** instead: ask for a capability, with a reason. An escalation is
   a graph edit request to the architect, which goes back through steps 3 and 4. One
   condition puts a Paper 3 pretext in the developer's context.
6. **Minimisation, crude**: narrow each grant to what the graph can exercise (fields never
   written, payees and caps that are constants), and report what it removed. By the roadmap
   note, it is expected to remove little.
7. **The owner evaluates**: AgentDojo's utility, plus the author's own verdict on the
   result, recorded.
8. **The architecture reviewer**: the author reviews the final graph (in the inspector, or
   a rendered page), giving a verdict per grant. It is compared with the AI reviewer's and
   with the labels.

A report, `dist/slice.md`, renders from the records, and a findings entry goes into
`docs/ROADMAP.md`.

**Not in this change:** a registered experiment; a paper; enforced attenuation at routing
points; participants other than the author; any paid spend without the author's approval.

## Impact

- **Specs:** a new `vertical-slice` capability.
- **Code:**
  - `poc/slice/`: the custom node, the developer step and escalation, the minimiser, the
    rendering for human review, the driver and the report;
  - `poc/architect/` gains the custom node in its catalogue and the shadow link check;
  - `poc/generation/` is reused, not changed. Its registered task hashes stay valid,
    because the slice's tasks are its own.
- **Usage:** the subscription, a few hundred Haiku calls at most; the author's time for
  steps 7 and 8.
