# S4 result: proofs of resource bounds

*Task 5.3 of `explore-specified-architecture`, 18 November 2026.*
- *The proof is `Proofs.respond_holds` in `s3/lean/Proofs.lean`, against
  `Statements.respond_spec`. `s3/check.sh` accepts it.*
- *The trace check is `trace_check.py`, with its results in `trace_check.json`.*

## What was proved

`respond_spec` is about GenerateResponse's tool loop, and it quantifies over every
`Host`. A `Host` is the model and the knowledge base, at any state and with any
behaviour, so the statement covers every model, however it adapts to what it has seen.
Whenever a run completes:
- there are at most 3 model calls and at most 3 lookups, so at most 6 crossings;
- there are no more lookups than model calls. This is a count, not an order.
  `Statements.lean`'s docstring says "no lookup without a model call before it", which
  is stronger than the `Prop` it describes. The statement is pinned, so the gap is
  recorded here and in `s3/RESULT.md`, not edited away;
- a refused tool is never the granted one.

The bound is an ordinary lemma about a list, because the core returns its crossings as
data (the survey's route). It needed no cost semantics and no resource library.

## Checked against the artifact

The shipped component was run unchanged, `poc/sandbox/wasm/node_generate_response.wasm`.
It was driven by every four-reply script over {text, call the granted tool, call
another tool}: 81 scripts. The host counted and logged each crossing in order.

| scripts | max crossings | proved bound | excesses | sequences ≠ core log | bound reached |
|---|---|---|---|---|---|
| 81 | 6 | 6 | 0 | 0 | yes |

- **No excess.** An excess would have indicted the shell or the trusted base. None
  occurred.
- **Every crossing sequence equals the core's log,** so the proved function and the
  shipped one agree on every input checked here. The core is also held to the shipped
  control flow in `s3/cores/tests/differential.rs`.
- **The bound is tight.** Three granted-tool calls in a row reach six crossings.

## The combined guarantee, and where it stops

The design proposed multiplying a proved count by an enforced cost per call. Here that
gives two things:
- **Proved:** at most 3 model calls, for every model.
- **Enforced:** a `Calls` budget (S1) is exact. A `Tokens` budget is enforced as "no
  call starts once spent", which can overrun by one call's output.

So the end-to-end token bound is the sum of the outputs of at most 3 calls. That sum is
bounded only if each call is capped. The CLI backend sets no per-call output cap today,
so **the product the design describes is not yet available on that backend.** S1's
`Tokens` budget gives "N plus one call" instead, and the proof lowers the number of calls
that can start to at most three.

**Instruction counts are not proved.** Fuel bounds them at run time, deterministically
and with an overshoot of one check interval (S1). No surveyed tool produces a certificate
a gate could check for them (`docs/PRIOR-ART.md` §23).

## Limits

- **One node.** Its loop has a constant bound. A node whose bound depends on its input
  (a per-item loop) would need the bound stated as a function of length; the same route
  applies.
- **The trusted base:**
  - the `run` shell that turns the core's choices into host calls (here the shipped
    body, which the differential test and the trace check tie to the core);
  - Charon and Aeneas;
  - the WIT bindings.

## Recommendation: fold into the S3 change, not a change of its own

A call bound is one more conjunct in a node's generated statement, proved with the rest.
The run-time half is S1's `Calls` budget. If both land, the proposed change should:
- generate a `Calls` budget from a proved bound when the bound is smaller than the
  declared one, never the reverse;
- name a per-call output cap as the missing piece for a proved token bound.
