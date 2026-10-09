# Voided trials

Trials that were run and recorded, and are **not counted**, because the fault they
record was the harness's and not the model's. They are kept rather than deleted:
a trial that was thrown away is something a reader cannot check, and each of these
is evidence of how the instrument failed.

Nothing here is read by `results.json` or by the report.

## `heartbeat-incomplete-binding/` — 12 trials, 9 October 2026

The first twelve `Heartbeat` trials of the pilot (two repetitions, both arms,
three models). Eleven of the twelve failed their first attempt with the class
`signature`, and all twelve record at least one such failure.

**What happened.** `Heartbeat` is granted `HTTPClient<[…]>`, which maps to the
`http-client` interface. That interface has two functions, `get` and `fetch`
(`fetch` was added on the same day, for the feed-triage service). The models —
reasonably, since `fetch` is the one that reports a failed request as a value —
called `fetch`. The host adapter for `Heartbeat` bound only `get`, because the
hand-written body only calls `get`. So instantiation failed with *"function
implementation is missing"*.

**Why it is worse than a wrong count.** The host reported that failure the way it
reports every instantiation failure that is not out-of-memory: *"it imports a
capability it was not granted"*. The pipeline classed it `signature` and fed that
sentence back to the model as the reason its code had failed. Every model then
"corrected" a correct body, replacing `fetch` with `get`, and passed. The record
shows the models being told something false and acting on it.

**What changed.**

- Every adapter now binds every function of every interface it links
  (`poc/sandbox/nodes.py`, `poc/sandbox/feed_nodes.py`), not only those its
  hand-written body calls.
- The host distinguishes this failure: a missing function of a *granted*
  interface raises `IncompleteHostBinding`, never the ungranted-capability
  message (`poc/sandbox/host.py`).
- The pipeline treats it as a `HarnessFault`: the trial is abandoned, nothing is
  recorded, and the run stops (`poc/generation/pipeline.py`).

The sixty-two trials of the other five nodes recorded before the pilot was
stopped are unaffected — none of their interfaces has a function their adapter
left unbound — and are kept. The `Heartbeat` trials were re-run from the start.
