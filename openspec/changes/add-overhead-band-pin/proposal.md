# Pin the overhead figure's magnitude, and make the confined tier survive a loaded machine

> **Backfilled.** This proposal was written after the work landed (`6f37391`), not
> before it. It is recorded because the change added requirements to three
> capabilities and the specs would otherwise carry no account of them; it is not an
> example of the workflow the corpus is meant to follow, and the review that
> prompted it is the reason it was written at all.

## Why

A full critical review of Paper 2 (`/review-proposal 2`) found the one figure that
escaped the corpus's interpolation discipline, and caught it mid-failure.

**A hand-typed magnitude beside an interpolated figure.** The corpus's rule is that
no evaluation number is transcribed by hand. "Tens of microseconds" was treated as
prose rather than as a figure, and typed by hand in three places in Paper 2 and once
in Paper 3. It is not prose: it is a claim about a measurement exactly as "23.1µs"
is. The first `make build` of the review session wrote **343.1µs** into
`dist/evaluation.json` and passed. Had the PDF shipped from it, the abstract, the
§4.3 table and the conclusion would have read "343.1 µs" while three sentences said
"tens of microseconds" — including §7.2's "the supported claim is that a crossing
costs tens of microseconds". Sampling put the excursion at roughly 1 build in 5–10.

**The figure had no build-failing pin, alone among the evaluation's figures.**
Corpus cases pin a verdict *and* a reason class; the derivation pins agreement in
both directions; the traces pin their structure. The crossing cost's only gate was
`within_envelope` (< 1ms), which hundreds of microseconds passes comfortably while
falsifying the paper's stated magnitude. The harness's own scope note claims every
figure is guarded against divergence; that was untrue of this one.

**And the confined tier could not be instantiated on a loaded machine.** Chasing the
above surfaced a second, unrelated fault. wasmtime's default engine reserves ~4GiB of
address space plus a 64MiB guard for each store, sized for a server running a few
long-lived guests. This tier builds a *fresh* store per node invocation, so it asked
for 4.06GiB per instantiation. The reservation is virtual and free until the machine
is loaded, at which point `mmap` refuses and instantiation fails — on a
deliberately-loaded machine, seven confined-tier tests failed this way. The symptom
was actively misleading: a resource failure lands in the same handler as an
unsatisfied import, so a busy machine reported what read as a capability error. A
security-relevant failure mode and a resource failure must not be indistinguishable.

## What Changes

- **Evaluation harness** — the crossing cost is pinned to a band (5–100µs). Because
  the excursions are transient, `measure_within_band()` re-measures rather than
  failing on the first one; a sustained excursion makes `main` refuse to write the
  artifact. The band is enforced where the artifact is *written*, not inside `run()`:
  the other pins guard properties, which must hold wherever the code runs, while this
  one guards a measurement, whose usability is a fact about the machine. A test that
  calls `run()` publishes no figure and should not fail on a busy laptop.
- **Derived magnitude** — `serialise()` emits `display.crossing_magnitude`, and the
  papers interpolate it. The band's ceiling *is* a decade boundary and the band is
  half-open there, so no measurement that passes the gate can name a decade other
  than the one the table shows. The prose and the figure cannot disagree.
- **Confined tier** — the engine is configured with a 32MiB memory reservation and a
  64KiB guard, with `memory_may_move` so the cap is not a correctness limit. That is
  two orders of magnitude above what any node here uses, and the crossing measurement
  is unmoved by it. Instantiation failures caused by host resource exhaustion are
  reported as such rather than as ungranted capabilities.
- **Papers** — §1.1's claim block drops the performance sentence, so the falsifiable
  central claim rests on the two artifact properties a reader can re-derive rather
  than on a differenced wall-clock quantity from one machine. §7.2 stops describing
  the fragility as a retired defect. §4's method note stops claiming a guard it did
  not have. Paper 3 §3.1 cites Paper 2 for the magnitude instead of stating it.
- **Tightening** — §3.5 loses ~190 words: the projection/tension discussion restated
  the host-tier-advisory limit the deduplication paragraph already makes, and "the
  tension appears to be ours alone" was a novelty claim resting on a documentation
  survey. Both pinned limits and the projection architecture are kept.

## Impact

- Affected specs: `evaluation`, `paper-corpus`, `signal-graph-runtime`
- Affected code: `poc/evaluate.py`, `poc/sandbox/host.py`, `poc/sandbox/bench.py`,
  `tests/test_poc_evaluate.py`
- Affected papers: `papers/02-demonstrator/proposal.typ`, `papers/03-method/proposal.typ`
- Affected docs: `AGENTS.md`
- Paper 1 is untouched (frozen); no errata arise from this review.
- Paper 2 remains 42pp against a low-to-mid-30s target; shedding a page wants ~450
  words and this recovers ~190 of them.
