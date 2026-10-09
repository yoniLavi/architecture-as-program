"""The node-generation experiment: can an agent write node bodies the
architecture then bounds?

The thesis says code is a compiled artifact: an agent writes a node's body from
its signature and contract, and what that body can reach is fixed by the graph,
not by the agent's good behaviour. One body was generated that way before this
package existed, uncontrolled and unmeasured. This package runs the experiment.

A trial gives a model one node's specification and nothing else — no tools, no
repository, an empty working directory — and asks for two files: the component's
WIT world and its Rust source. The model writes its *own* world on purpose. If
the harness wrote it, a body could not ask for an interface it was not granted,
and the gate that refuses such a body could never be tested by generated code.

Each reply then goes through the pipeline the hand-written bodies go through:

    format → build → gate → (ambient scan) → contract → run

`gate` is the derivation Paper 2 reports: the built component's imports held
against the set derived from the node's `with` clause, by the same code. A
failure is fed back and the model tries again, up to four times.

Layout:

    task.py        what the model is shown: signature, contract, types, WIT
    prompts/       the task template and the adversarial arm's pretext, fixed
    subjects.py    the nodes under test, and how to exercise each
    pipeline.py    one reply through the six steps
    check.py       the contract and run steps, in a child process with a timeout
    harness.py     trials: every arm, model, node and repetition; recorded, resumable
    report.py      results.json → dist/generation.{md,json}; the build step
    runs/          every trial, committed: prompt hash, replies, files, verdicts
    results.json   derived from runs/, committed; all the build reads

The build never calls a model and never needs a Rust toolchain: `report.py`
reads `results.json`. Running trials needs both, and the author's subscription.
"""
