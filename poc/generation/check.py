"""The contract and run steps, in a child process.

A generated body is untrusted code in the plainest sense: it may loop for ever.
The confined tier bounds what it can *reach*, not how long it runs, and the
runtime's engine is deliberately not configured with fuel or epochs (that would
change the crossing cost Paper 2 measures). So the two steps that execute a
generated component run here, in a process of their own that the pipeline kills
at a deadline. A body that does not terminate fails its contract; it does not
hang the experiment.

    python -m poc.generation.check <Node> <component.wasm | -> [--gate-off]

Prints one JSON object. `-` evaluates the committed, hand-written artifact — the
reference the generated body's run is compared with. `--gate-off` links stand-ins
for every capability interface the node was *not* granted, so an over-importing
component instantiates; it then reports whether that component would have passed
everything, and how often it called what it was never given.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

from .. import contracts
from ..sandbox import host
from ..sandbox.feed_nodes import FEED_SANDBOX_REGISTRY
from ..sandbox.interfaces import (
    CLOCK,
    EVENT_EMITTER,
    HTTP_CLIENT,
    INFERENCE_LLM,
    KB_READ,
    NOTIFIER,
    RESPONSE_CHANNEL,
    STATE_READ,
    STATE_RW,
    TOOL_LLM,
)
from ..sandbox.nodes import SANDBOX_REGISTRY, heartbeat_sandbox
from ..values import Variant
from .subjects import BY_NODE, Subject, run_graph

ADAPTERS = {**SANDBOX_REGISTRY, **FEED_SANDBOX_REGISTRY, "Heartbeat": heartbeat_sandbox}

CLASS_CONTRACT = "contract"
CLASS_SIGNATURE = "signature"
CLASS_RUN = "run"


def _stand_ins(calls: dict[str, int]) -> dict:
    """A harmless implementation of every capability interface, each call
    counted against its interface. What the gate-off control links."""
    from wasmtime.component import Variant as WitVariant

    def counted(interface: str, result):
        def call(*args):
            calls[interface] = calls.get(interface, 0) + 1
            return result(*args) if callable(result) else result

        return call

    def moment():
        return host.record(seconds=0, nanoseconds=0)

    table = {
        INFERENCE_LLM: {"infer": "ok"},
        TOOL_LLM: {"generate": "done"},
        KB_READ: {"lookup": lambda *_: []},
        RESPONSE_CHANNEL: {
            "send": lambda *_: host.record(session="gate-off", delivered=True),
        },
        EVENT_EMITTER: {"emit": True},
        HTTP_CLIENT: {"get": "", "fetch": lambda *_: WitVariant("ok", "")},
        NOTIFIER: {"notify": True},
        STATE_READ: {"get": None},
        STATE_RW: {"get": None, "put": None, "delete": None},
        CLOCK: {"now": lambda *_: moment(), "resolution": lambda *_: moment()},
    }
    return {
        interface: {name: counted(interface, result) for name, result in functions.items()}
        for interface, functions in table.items()
    }


def _describe(value: object) -> str:
    text = repr(value)
    return text if len(text) <= 300 else text[:300] + "…"


def property_tests(subject: Subject) -> dict:
    """Run the body on every input its contract generates and check `ensures`."""
    adapter = ADAPTERS[subject.node]
    ensures = subject.predicates("ensures")
    inputs = subject.test_inputs()
    for value in inputs:
        args = value if subject.arity > 1 else (value,)
        try:
            output = adapter(*args, *subject.handles())
        except host.IncompleteHostBinding:
            # Not the body's fault, and never to be reported as one: see `main`.
            raise
        except host.SandboxTypeError as e:
            return _failed(CLASS_SIGNATURE, f"the export's signature is not the node's: {e}")
        except host.SandboxError as e:
            return _failed(CLASS_SIGNATURE, f"the component could not be called: {e}")
        except Exception as e:
            return _failed(
                CLASS_CONTRACT,
                f"the body failed on an input its contract admits.\n"
                f"input: {_describe(value)}\nerror: {type(e).__name__}: {e}",
            )
        payload = output.value if isinstance(output, Variant) else output
        try:
            contracts.check(ensures, payload, node=subject.node, kind="ensures")
        except contracts.ContractViolation as e:
            return _failed(
                CLASS_CONTRACT,
                f"{e}\ninput: {_describe(value)}\noutput: {_describe(payload)}",
            )
        except AttributeError as e:
            return _failed(CLASS_SIGNATURE, f"the output is not of the node's type: {e}")
    return {"ok": True, "inputs": len(inputs)}


def _failed(failure_class: str, detail: str) -> dict:
    return {"ok": False, "class": failure_class, "detail": detail}


def evaluate(subject: Subject, component: Path | None, gate_off: bool) -> dict:
    """Both steps for one component. The run step is skipped once the contract
    step has failed: a body that breaks its contract is not put into a graph."""
    calls: dict[str, int] = {}
    with contextlib.ExitStack() as stack:
        if component is not None:
            stack.enter_context(host.substituted({subject.component: component}))
        if gate_off:
            stack.enter_context(host.permissive(_stand_ins(calls)))
        contract = property_tests(subject)
        run: dict = {"ok": None}
        if contract["ok"]:
            try:
                run = {"ok": True, "orders": run_graph(subject)}
            except Exception as e:
                run = _failed(
                    CLASS_RUN, f"the graph did not run with this body: {type(e).__name__}: {e}"
                )
    return {"contract": contract, "run": run, "ungranted_calls": calls}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="poc.generation.check")
    parser.add_argument("node")
    parser.add_argument("component", help="path to a built component, or - for the committed one")
    parser.add_argument("--gate-off", action="store_true")
    args = parser.parse_args(argv)
    component = None if args.component == "-" else Path(args.component)
    try:
        result = evaluate(BY_NODE[args.node], component, args.gate_off)
    except host.IncompleteHostBinding as e:
        # The host adapter does not bind a function the body is entitled to call.
        # That is a defect in this harness. Reported as such, so that the pipeline
        # stops instead of charging it to the model and feeding it back as advice.
        result = {"harness_fault": str(e)}
    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
