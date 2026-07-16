# Methodology

This repository is a research program carried out incrementally, with a human
setting direction and an AI coding agent as the instrument. This document states
that division of authority plainly, because the repository's own thesis is that
honest attribution of AI contribution is preferable to ambiguity — and because
the process *is* part of what makes the work interesting.

## Division of authority

**The human is the principal investigator.** The author (Yoni Lavi) sets the
research scope, frames the questions, makes the design decisions, accepts or
rejects proposals, and is accountable for every claim the corpus makes. Nothing
here is autonomous research: no part of the program chooses its own goals,
decides what is true, or commits work without human approval.

**The AI agent is the instrument.** Claude (Anthropic) drafts prose, surveys and
cites prior work, writes and tests the demonstrator tooling, and executes the
change proposals — under the author's direction and subject to the author's
review. Where the agent produced a factual claim about prior work, it was
verified against primary sources; where it produced code, that code is covered
by the test suite and the build gate.

We make no claim of autonomous research, and this record would undermine itself
if we did: its credibility rests on the evidence trail below, which documents
human decisions being made and an instrument carrying them out.

## Spec-driven, and self-documenting

Work is driven through **OpenSpec** (`openspec/`). Non-trivial changes begin as a
written proposal — a `proposal.md` (why and what), a `design.md` (the decisions
and the alternatives weighed), spec deltas, and a `tasks.md` checklist — which is
validated and approved *before* implementation. This dogfoods the corpus's own
argument: that the primary artifact is structured *intent*, and the
implementation is the compiled consequence of it.

## The evidence trail

The longitudinal, human-directed-with-an-AI-instrument nature of this work is not
a claim to take on faith; it is recorded and inspectable:

- **`openspec/changes/`** — every substantive change as an approved proposal:
  the intent, the design rationale, the alternatives considered, and the task
  breakdown. Completed changes are retained under `openspec/changes/archive/`.
- **Git history** — each change lands as commits on `main` (trunk-based
  development), so the sequence of decisions and their execution is legible SHA
  by SHA.
- **The corpus** (`papers/`) — the founding vision is frozen as Paper 1, dated to
  when it was written, so the starting point of the program is a stable,
  citable document rather than a state reconstructable only from history. Later
  papers build on the shared, evolving research artifact and reference what came
  before. See `papers/README.md` for how the corpus is organised.
- **The tested artifact** (`graphs/`, `scripts/`, `poc/`, `tests/`) — the claims
  a paper makes about what is implementable are backed by tooling that builds and
  passes its tests on every commit and in CI, not by prose alone.

## What this is not

It is not a claim that an AI conducted research on its own. It is not a benchmark
of agent capability. It is a record of one way of working — a human directing an
AI instrument through a spec-driven process — kept honestly enough that a reader
can check the record against the result.
