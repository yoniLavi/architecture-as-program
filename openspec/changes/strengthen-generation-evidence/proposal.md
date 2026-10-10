# Strengthen the generation evidence into the basis of Paper 3

## Why

`build-feed-triage-and-generation-experiment` produced one result worth a paper and left it
resting on too little. Asked to implement a node, and asked again with a request for ungranted
authority attached, no model in 450 trials reached for any. Told the extra grant had been
*approved*, models built over-importing components in 104 of 225 trials; the gate rejected every
one, and with the gate off every one would have passed its contract and run.

The author's judgement on 10 October 2026 was that this is too early for a paper. Six gaps stand
between the result and one:

- **The arm that carries the result is post hoc.** It was written after the first two arms came
  back empty, as one pretext, with the outcome in view.
- **Nothing separates a model respecting a stated rule from a model that would not reach anyway.**
  Every task states that the `with` clause is the node's entire authority.
- **A green trial fits its node; it is not shown to behave like the body it replaces.** The
  contract vocabulary cannot say what a body should compute.
- **One model family**, with a spread across its three models (2, 39 and 63 of 75) that nothing
  here explains.
- **The service has three ticks of operating history**, all on one afternoon.
- **The hostile corpus is eleven hand-written feeds**, comparable with no published figure.

## What Changes

**A pre-registered replication (phase 1).** The pretexts, the cells, the number of trials and the
one primary outcome are committed *before any trial is run*, and the commit is named in the
report. Six pretexts vary three things the single post-hoc one confounded: who claims the
authority, whether the interface is named, and whether the graph is said to be catching up. The
post-hoc arm's 225 trials stay in the record as what they are and are not pooled with the new ones.

**A rule-withheld condition (phase 1).** The same tasks with the sentence that states the rule
removed. Crossed with the pretexts, this is what separates compliance with a stated constraint
from the absence of any inclination to reach.

**Differential testing (phase 2).** Each green body is run beside the hand-written one on the
inputs its contract generates, under a model stand-in whose reply does not depend on prompt
wording. Bodies are reported as *behaviourally equal on those inputs* or not. It is reported, not
gating: a body may differ and be right.

**Operating history by replay (phase 3).** A recorder archives the raw feeds on a timer, making no
model call. The service is then run over the archive with an injected clock, as many times and
under as many configurations as wanted. What replay cannot show — the scheduler, the lock, real
network failure — is taken from the recording period and reported separately.

**A second model family (phase 4), on a decision the author has not yet made.** Either a local
open-weights model, or the experiment stays one-family and says so. No paid API is used either way.

**A slice of AgentDojo as graphs (phase 5), after a spike.** Whether one suite's tasks can be
expressed as signal graphs at all is itself unknown. The phase opens with a time-boxed spike and a
go/no-go; it does not commit to a benchmark number.

**Not in this change:** Paper 3's prose; attenuation at the routing point (still held for
Paper 2); any change to Paper 2 or to a figure it typesets.

## Impact

- **Specs:** `node-generation` (pre-registration, the rule-withheld condition, differential
  testing, a second backend); `feed-triage-service` (recorder, replay); `evaluation` (replayed
  operating history reported apart from live).
- **Code:** `poc/generation/` (arms as data, a registration record, a differential step, a
  backend seam); `poc/serve.py` and a new `poc/feeds/archive.py` (record and replay).
- **Cost:** the author's subscription only. Phase 1 is about 1,350 trials, roughly four hours of
  wall clock at the rate the last run achieved; the harness stops at its usage ceiling and resumes.
- **Paper 2 is unchanged.** The pin in `tests/test_paper2_figures_pinned.py` stays as it is.
