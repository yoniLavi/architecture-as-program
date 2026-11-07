# An architect that writes graphs, and reviewers that check them: Paper 4's evidence

> **Status:** written 29 October 2026, from the author's decisions on
> `docs/paper-4-design-questions.md` (D1–D9, all recommendations accepted, plus the paid-API
> policy). Depends on `add-agentdojo-banking-harness`. No Paper 4 prose is in this change.

## Why

Paper 4 is the front half of the north star (`docs/ROADMAP.md`): a Product Owner's prompt →
an **architect** model authors a signal graph → **formal review** → an **independent AI
reviewer**. The survey (`docs/paper-4-survey/`) narrows the claim to what is new. The authority
artefact is **persisted**, **reviewed** before anything runs, and **determines the binaries**.
And the threat every surveyed pattern leaves out of scope is a pretext in the user's own prompt.
Paper 3 showed that a claimed approval moves these models.

## What Changes

- **The architect, in two stages** (D1). Stage one writes an abstract graph, without the
  capability catalogue. Stage two maps it to the narrowest library nodes and kinds. The
  architect sees only:
  - the prompt;
  - the catalogue, in stage two only;
  - structured validator verdicts.

  It never sees tool output. The validator runs in the loop, with a bounded number of
  repairs.
- **Grant rationales** (D2). Every `with` entry cites the span of the prompt that justifies
  it. A deterministic **link check** fails any grant with no link, which makes it part of the
  formal review.
- **The formal review** (step 3): the validator, the link check, and a **least-authority check**
  against hand-labelled minimal grants for each banking task (D6). The labels are drafted,
  approved by the author, and registered before any measured run.
- **The independent reviewer** (step 4; D3, D4):
  - It sees the prompt and a canonicalised graph only. A second verdict, given the
    architect's rationale, is reported apart.
  - It is tested before use on a pinned corpus of hand-widened graphs, and the run is refused
    if it misses too many.
  - Its model is chosen by a rule fixed in advance from Paper 3's registered data: the Claude
    model least moved by claimed approvals.
  - Every catch rate is reported beside how similar the architect and the reviewer are. The
    paper calls this *diversity*, not independence.
- **No run-time escalation** (D8). A missing grant fails the run and returns to the architect
  as a graph edit, which is reviewed again. The report gives an **autonomy** figure beside
  utility and attack success.
- **A registered experiment** (D5), as Paper 3's was: the pretexts verbatim, two channels (the
  Product Owner's prompt, and a document the architect is given), the cells, the model IDs,
  one primary outcome (a widening that both reviewers miss), and one confirmatory test. The
  author approves the pretexts and the registration before any trial.
- **A cross-family control, gated** (D4, under the paid-API policy). A small subset is
  reviewed by a different model family (DeepSeek, by API), only after the subscription results
  validate the approach, and only with the author's explicit approval of the spend. Keys come
  from the environment, and the spend is recorded.
- **A report**, `dist/architect.{md,json}`, rendered from committed records. The build calls no
  model. It gives utility, attack success and autonomy against the same-model baseline;
  widening and catches per reviewer; predictions against outcomes; and the registered run
  apart from anything exploratory.

**Not in this change:** Paper 4's prose (a later `add-paper-4` change); developers,
decomposition, escalation as a protocol, and minimisation (the back half); and human review
(steps 7–8).

## Impact

- **Specs:** a new `architect-pipeline` capability.
- **Code:**
  - `poc/architect/`: the architect, the link and least-authority checks, the reviewer, the
    registration, the harness and the report;
  - `poc/llm.py`: a second backend for the gated cross-family control. It is never used by a
    test or the build.
- **Cost:** the subscription first. Architect and reviewer calls are about 16 tasks × (1 +
  pretext conditions × 2 channels) × N per model, plus 144 task–injection pairs for security.
  The paid control waits for its gate.
- **Paper 2 is unchanged, and Paper 3 is deferred** (`docs/ROADMAP.md`).
