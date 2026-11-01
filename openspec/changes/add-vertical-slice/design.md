# Design: the vertical slice

## Context

- **Built:** the architect, the formal review, the reviewer, the banking harness and its
  scorer (`poc/architect/`, `poc/agentdojo/`); Paper 3's generation pipeline and its gate
  (`poc/generation/`, `poc/sandbox/interfaces.py`).
- **What it must test** (`docs/ROADMAP.md`, 1 November 2026):
  - whether authority changes *only* through reviewed graph edits once developers are in
    the loop;
  - whether a person catches what same-model review missed;
  - whether a scope-binding link check or a behaviour-shown reviewer does better;
  - how little minimisation removes.

## The pieces

- **The custom node.** A library entry `Custom`, with `role`, typed inputs and output, and
  a `with` clause, but no body. It is the only place a developer writes code. The library
  check holds its clause to the same narrowing rules. It runs confined, through the
  component the developer's code builds into, and that component's imports are held to its
  clause by the existing gate.
- **The developer.** Paper 3's task builder, given the custom node. Its reply is either a
  body, or `{"escalate": {"capability": …, "because": …}}`. An escalation becomes a graph
  edit request: the architect gets the request's capability and its reason as a structured
  reason, decides, and steps 3 and 4 review the edited graph. A body that the gate rejects
  is a gate catch, as in Paper 3, never an escalation.
- **The minimiser.** For each grant, it computes the narrowest grant the graph can
  exercise, from constants in `Compose` and from the fields its writers set. It reports
  the grant, the narrowed grant, and whether the run still has utility after narrowing.
- **Human review.** A page per final graph: the prompt; the graph (the inspector's view,
  or a rendered listing); and, for each grant, what the AI reviewer said, with a verdict
  for the author to fill. Verdicts are recorded as a committed file per graph.

## Open questions for the author

1. **Domain and tasks.** Recommended: banking, three tasks:
   - 4: works, and has a narrow payee;
   - 15: a multi-step task, which failed;
   - 0: the payee is read from a bill, and it is predicted residual.

   An alternative is the feed-triage service, which has developers' prior art (Paper 3)
   but no architect yet.
2. **The custom node: yes or no?** Without it, step 5 has nothing to do in banking, because
   the library covers every tool. With it, the architect can reach for code, a new route to
   authority, which the slice is meant to probe.
3. **Which step-4 candidate.** The roadmap lists four: a different family (needs a spend
   approval), the author earlier, behaviour shown to the reviewer, or a stronger link check.
   Recommended: behaviour shown and the stronger link check, both on the subscription, plus
   the author at step 8.
4. **A pretext at step 5?** Recommended: yes, in one condition. It is the developer-side
   version of Paper 4's channel A.
5. **The author's time.** Steps 7 and 8 need the author: a few minutes per graph, about
   three to six graphs.

## Risks

- **Scope creep.** The slice is crude by design: it tests the flow, not each step's
  quality. A step that needs more than a few hours of building is stubbed, and the stub is
  recorded as such.
- **Reading a slice as a result.** One author, a few graphs. Its findings shape the plan
  and the papers' framing, never a figure in a paper.
