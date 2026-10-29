# Paper 4: design questions for the author

29 October 2026. This document comes before any OpenSpec change. It records what the survey
of practice changed (`docs/paper-4-survey/`), and the decisions Paper 4 needs from the author.
Each decision has a recommendation. Paper 4 is the front half of the north star
(`docs/ROADMAP.md`): a Product Owner's prompt → an **architect** AI authors the graph →
**formal review** → an **independent AI reviewer** → (the developers, out of scope here).

## What the survey changed

**1. The claim narrows to what is actually new.** Planning before execution is established
practice:
- CaMeL's planner writes restricted code that an interpreter enforces;
- ACE (NDSS 2026) builds an abstract plan from trusted information, maps it to concrete apps,
  checks information flow statically, and isolates the apps;
- Conseca generates a per-task policy with human-readable rationales and enforces it
  deterministically;
- FIDES and its successor plan with information-flow labels on AgentDojo.

None of them, in what was surveyed, **persists** the authority artefact, has it
**independently reviewed** before anything runs, or **derives the binaries' import surfaces
from it**. Conseca comes nearest: its policies are "human-verifiable", but approval is
optional and unevaluated. That combination, and not "planning", is Paper 4's claim, scoped to
the survey.

**2. The threat every pattern leaves out is ours to measure.** The design-patterns paper says
plan-then-execute "does not prevent prompt injections contained in the user prompt". In our
flow, the Product Owner's prompt is the trusted input. A pretext in it, or in a document the
architect reads, aims at the architect, who could write a wider `with` clause. The reviewers
in steps 3 and 4 are the defence. Measuring whether they catch it is the new part, and
Paper 3 shows the attack is real: claimed approvals move these models.

**3. Same-family review weakens independence, and practice offers a disciplined way through.**
- A model prefers outputs it recognises as its own (Panickssery et al.).
- Errors correlate within a provider, and larger models correlate even *across* providers
  (Kim et al., ICML 2025). Changing family is not a full cure.
- AI Control shows a same-model monitor can still add safety (79% safety, against 62% for
  trusted monitoring, in its one setting), provided it is tested before use on planted
  defects and kept from colluding.
- A reviewer shown the generator's reasoning can be talked round ("CoT Red-Handed").

**4. Run-time escalation is the norm in practice, and the contrast to draw.** MCP's step-up
authorisation, Codex approvals and Claude Code prompts all grant authority mid-run. Claude
Code's own documentation says a Bash rule "isn't a security boundary".

## Decisions

**D1. How the architect authors the graph.**
- *Recommended:* in two stages, as ACE does. First an abstract graph written without the
  capability catalogue, then a separate mapping to the narrowest kinds that serve it. This
  costs one more model call, and shows *which stage* widens authority under a pretext.
- *Alternative:* one stage, with the catalogue shown from the start.

**D2. Every grant cites its justification.**
- *Recommended:* each entry in a `with` clause carries a rationale citing the span of the
  prompt that needs it, as Conseca does. A deterministic check then fails any grant with no
  link. This turns part of step 4 into step 3.

**D3. What the reviewer sees.**
- *Recommended:* the prompt and a canonicalised graph, never the architect's reasoning or
  the material it read; that is the primary verdict. A second verdict *with* the rationale is
  reported apart, to measure how far the rationale persuades.

**D4. Independence under the Claude-only rule.**
- *Recommended:* Claude reviews Claude, with three disciplines:
  - the reviewer is tested before use on a pinned corpus of hand-widened graphs;
  - it uses the Claude model least moved by pretexts in Paper 3's data;
  - every catch rate is reported beside the architect–reviewer similarity.

  The paper calls this **diversity, not independence**, and states it as a lower bound.
- *Question:* would a **small cross-family control** be acceptable? Your rule is no paid API.
  A local open-weights model, as the reviewer on a subset, stays within it. It would turn the
  biggest threat to validity into a measured one.

**D5. The threat model, registered like Paper 3's run.**
- *Recommended:* two channels:
  - a pretext in the Product Owner's prompt, which every surveyed pattern leaves out of scope;
  - a pretext in a document the architect is given, which is indirect.

  Pretexts, cells, primary outcome and one confirmatory test are committed before any trial.
  The primary outcome is a widening that both reviewers miss.

**D6. Ground truth for "unseen widening".**
- *Recommended:* hand-label the least authority each AgentDojo banking task needs, before the
  measured run, and register the labels. The spike's three graphs are a start. A
  deterministic check then flags every grant beyond the label. The labels are the author's
  judgement and will be published as such.

**D7. Scope and baselines.**
- *Recommended:* the banking suite only: 16 user tasks and 9 injection tasks, which the spike
  found all expressible.
- Report AgentDojo's utility and attack success, plus an **autonomy** figure: the share of
  consequential actions that run with no human prompt.
- Baselines are published numbers for CaMeL, FIDES and Progent, labelled as other models. No
  paid API means no re-run on the same model.
- *Question:* is a same-model undefended baseline worth building on `claude -p`? It needs a
  tool-calling pipeline element built from the CLI backend. It is feasible but not free.

**D8. No run-time escalation.**
- *Recommended:* a missing grant fails the run and returns to the architect as a graph edit,
  which goes back through steps 3 and 4. This is stated as the contrast with practice, and
  costs autonomy honestly.

**D9. The human stays out of steps 1–4 in the measured claim.**
- *Recommended:* yes. The claim is what *automated* review catches. Human review is step 8,
  and is measured later, with participants.

## What D1–D9 require (the C track, as needed)

From the spike:
- four new capability kinds, in the full vocabulary only: `Payments`, `ScheduledPayments`,
  `UserProfile`, and a never-granted `Credentials`;
- a host adapter from handles to AgentDojo's tool functions;
- a graph-backed pipeline element;
- a workaround for exclusive-branch merges.

Attenuation at routing points is *not* needed for the front half; it belongs to the back
half.

## A draft claim, for shape only

> From a task in natural language, an architect model authors a signal graph whose authority
> is reviewed before anything runs, first formally and then by a separate model, and the
> graph then determines each component's import surface. On AgentDojo's banking suite we
> report utility, attack success and autonomy. Under pretexts placed in the task and in what
> the architect reads, we report how often the architect widened authority, and how often
> each reviewer caught it.

## Cost, roughly

- Banking utility: 16 tasks.
- Security: 144 task–injection pairs.
- The pretext experiment: 16 tasks × pretexts × 2 channels × N.

All of it runs on the subscription, at low priority, resumable, like Paper 3's run.

## After the decisions

An OpenSpec change for Paper 4: proposal, design, and spec deltas for the planner, the
reviewers and the AgentDojo adapter. Then the registration. Then the thin vertical slice
(`docs/ROADMAP.md`) once the front half has a result.
