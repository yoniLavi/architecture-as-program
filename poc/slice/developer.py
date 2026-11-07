"""The developer (north-star step 5, task 3.1): a model writes a `Custom` node's body.

**What it is shown** (`task_text`), Paper 3's way: the node's signature and `with`
clause, the role the architect gave it, the shapes of its inputs and output, the
interfaces its clause grants, the export, the fixed crate, and the `aap:caps` package
(general and banking interfaces) **without any world**, so that its own world, and an
ungranted import, are its to write. Never a bank value, never the task prompt: the
role is what the architect asked of the node, as the architect wrote it.

**What it may return**: two files, or a request for authority,
`{"escalate": {"capability": …, "because": …}}` (3.2). A body the gate rejects is a
gate catch, as in Paper 3, never an escalation.

**The pipeline** (`evaluate`), reusing Paper 3's pieces (`poc/generation/pipeline.py`:
reading the reply, the ambient scan) and its gate (`poc/sandbox/interfaces.py`):

    format    the reply was neither two fenced files nor an escalation
    build     the crate did not compile into a component
    gate:<i>  the component imports a capability interface its clause does not grant
    run       the graph, run on the task's clean environment with this component
              confined, failed at this node (its own error, or its output off schema)

Two departures from Paper 3, both recorded rather than hidden:
* **No contract step.** The architect writes no `requires`/`ensures` for a `Custom`
  node, so there is nothing to check one against. A stub, stated.
* **Under-importing does not fail.** Paper 3 fails a body that leaves a granted
  interface unused. Here an unused grant is recorded (`unused_grants`): it is a
  minimisation finding about the graph, not a fault in the body.

A run-time refusal at a crossing is fed back as a reason class from the measured
run's fixed table (`poc/architect/measure.py`), never its message. A failure at
another node is not the developer's: it is recorded, and the body stands.

Building needs Rust with `wasm32-unknown-unknown` and `wasm-tools`; running needs
`wasmtime` and AgentDojo. Nothing here runs in `make build`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..agentdojo.library import (
    RECORDS,
    LibraryError,
    check_record,
    compact,
    custom_schema,
    strip_output,
)
from ..architect.mapping import SHAPES
from ..generation import pipeline as p3
from ..generation import task as p3task
from ..graph import REPO_ROOT
from ..sandbox.interfaces import TYPES, interfaces_for_node

HERE = Path(__file__).resolve().parent
PROMPT = HERE / "prompts" / "developer.md"
BANKING_WIT = REPO_ROOT / "poc" / "sandbox" / "wit" / "banking.wit"
_LIB_WORLDS_MARKER = "// ── The node library's components"
BUILD_ROOT = REPO_ROOT / "var" / "slice" / "build"

MAX_ATTEMPTS = 3

CARGO_TOML = """[package]
name = "generated_node"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
wit-bindgen = "0.59"
serde_json = "1"

[profile.release]
opt-level = "s"
lto = true
panic = "abort"
strip = true

[workspace]
"""

BODY = "body"
ESCALATED = "escalated"
FAILED = "failed"


# ── The task ────────────────────────────────────────────────────────


def banking_package() -> str:
    """banking.wit's interfaces with their doc comments: no library worlds, no `//`."""
    head = BANKING_WIT.read_text().split(_LIB_WORLDS_MARKER)[0]
    kept = [ln for ln in head.splitlines() if not ln.lstrip().startswith("//") or
            ln.lstrip().startswith("///")]  # fmt: skip
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip() + "\n"


def _shape_of(graph: dict, node: dict, t: str) -> str:
    """A data input's shape, by its type: a known record, a list of transactions, or
    the fields the upstream node that emits it names."""
    name = strip_output(t)
    if name == "TransactionList":
        return "a list of " + _fields(SHAPES["Transaction"])
    if name in SHAPES:
        return _fields(SHAPES[name])
    if name in RECORDS:
        return _fields(RECORDS[name])
    for e in graph["data_edges"]:
        if e["to"] != node["name"]:
            continue
        src = next(n for n in graph["nodes"] if n["name"] == e["from"].split(".")[0])
        fields = src.get("params", {}).get("fields")
        if strip_output(src["output"]) == name and isinstance(fields, dict):
            if src["uses"] == "Compose":  # its fields are expressions, not types
                return _fields({k: "value" for k in fields})
            return _fields({k: str(v) for k, v in fields.items()})
    return "a JSON value"


def _fields(fields: dict[str, str]) -> str:
    return "{" + ", ".join(f'"{k}": {v}' for k, v in fields.items()) + "}"


def node_of(graph: dict, name: str) -> dict:
    return next(n for n in graph["nodes"] if n["name"] == name)


def task_text(graph: dict, node_name: str, pretext: str | None = None) -> str:
    """What the developer is shown for `node_name`, and only that."""
    node = node_of(graph, node_name)
    caps = set(graph["capabilities"])
    data = [i for i in node["inputs"] if i not in caps]
    granted = interfaces_for_node(node, graph["capabilities"])
    fields = {
        "signature": p3task.signature(graph, node_name),
        "role": node.get("params", {}).get("role", ""),
        "inputs": "\n".join(
            f"{i}. `{t}`: {_shape_of(graph, node, t)}" for i, t in enumerate(data, 1)
        )
        or "(none)",
        "output": _fields(custom_schema(node)),
        "granted": "\n".join(f"- `{i}`" for i in granted) or "- (none: it holds no capability)",
        "cargo": CARGO_TOML.strip(),
        "package": p3task.caps_package().strip(),
        "banking": banking_package().strip(),
    }
    text = PROMPT.read_text()
    for key, value in fields.items():
        text = text.replace(f"<<{key}>>", value)
    if pretext:
        text += "\n" + pretext.strip() + "\n"
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


# ── The reply ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Escalation:
    capability: str
    because: str

    def as_dict(self) -> dict:
        return {"capability": self.capability, "because": self.because}


_JSON = re.compile(r"\{.*\}", re.S)


def escalation(reply: str) -> Escalation | None:
    """A reply that is a request for authority, or None. Checked before the files,
    and only when the reply holds no ```rust block, so code that mentions the word
    is still read as code."""
    if re.search(r"```(rust|rs)\b", reply):
        return None
    m = _JSON.search(reply)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    esc = obj.get("escalate") if isinstance(obj, dict) else None
    if not isinstance(esc, dict) or not isinstance(esc.get("capability"), str):
        return None
    return Escalation(esc["capability"].strip(), str(esc.get("because") or "").strip()[:500])


# ── Build and gate ──────────────────────────────────────────────────


def build(files: dict[str, str], crate: Path) -> tuple[Path | None, str]:
    """Paper 3's crate, with `serde_json` and the banking interfaces beside caps."""
    if crate.exists():
        shutil.rmtree(crate)
    (crate / "src").mkdir(parents=True)
    (crate / "wit" / "deps" / "caps").mkdir(parents=True)
    (crate / "Cargo.toml").write_text(CARGO_TOML)
    (crate / "src" / "lib.rs").write_text(files["lib.rs"])
    (crate / "wit" / "world.wit").write_text(files["world.wit"])
    (crate / "wit" / "deps" / "caps" / "caps.wit").write_text(p3task.caps_package())
    (crate / "wit" / "deps" / "caps" / "banking.wit").write_text(banking_package())
    target = BUILD_ROOT / "target"
    cargo = ["cargo", "build", "--release", "--offline", "-j", str(p3.CARGO_JOBS),
             "--color", "never", "--target", p3.TARGET,
             "--manifest-path", str(crate / "Cargo.toml")]  # fmt: skip
    try:
        done = subprocess.run(cargo, capture_output=True, text=True, check=False,
                              env=p3._clean_env(target), timeout=p3.CARGO_TIMEOUT_S)  # fmt: skip
    except subprocess.TimeoutExpired:
        return None, f"the build did not finish within {p3.CARGO_TIMEOUT_S}s"
    if done.returncode != 0:
        return None, p3._compiler_errors(done.stderr)
    core = target / p3.TARGET / "release" / "generated_node.wasm"
    component = crate / "node.wasm"
    wrapped = subprocess.run(["wasm-tools", "component", "new", str(core), "-o", str(component)],
                             capture_output=True, text=True, check=False)  # fmt: skip
    if wrapped.returncode != 0:
        return None, f"the module could not be made a component: {wrapped.stderr.strip()[:2000]}"
    return component, ""


def gate(component: Path, graph: dict, node_name: str) -> tuple[list[str], list[str]]:
    """(over-imported, unused) capability interfaces, against the node's clause."""
    from ..sandbox import host

    derived = set(interfaces_for_node(node_of(graph, node_name), graph["capabilities"]))
    actual = set(host.imports_of(component)) - {TYPES}
    return sorted(actual - derived), sorted(derived - actual)


# ── The confined body ───────────────────────────────────────────────


class CustomNodeError(LibraryError):
    """A `Custom` node's own failure: its `Err`, or an output off its schema."""


def _entry_for(cap: str) -> str:
    """The library entry whose host binding serves `cap`'s interface."""
    if cap.startswith("DBHandle<"):
        return "ReadFile"
    if cap.startswith("LLMClient<"):
        return "Extract"
    if cap.startswith("Payments<"):
        return "ScheduleTransaction" if cap.rstrip(">").endswith("recurring") else "SendMoney"
    if cap.startswith("ScheduledPayments<"):
        return "UpdateScheduledTransaction"
    if cap.startswith("UserProfile<"):
        return "UpdateUserInfo"
    raise LibraryError(f"a Custom node may not hold {cap}")


def body(graph: dict, node_name: str, component: Path) -> Callable[..., Any]:
    """The confined body of a `Custom` node: the developer's component, linked to the
    handles its clause grants and to nothing else."""
    from ..agentdojo.confined import _caps
    from ..sandbox.host import Sandbox, substituted

    node = node_of(graph, node_name)
    caps = set(graph["capabilities"])
    held = [i for i in node["inputs"] if i in caps]
    n_data = len(node["inputs"]) - len(held)
    schema = custom_schema(node)
    params = compact({"node": node_name, "role": node.get("params", {}).get("role", ""),
                      "fields": schema})  # fmt: skip
    artifact = f"slice_custom_{node_name}"

    def run(*args: Any) -> Any:
        data, handles = args[:n_data], args[n_data:]
        bindings: dict[str, dict[str, Callable[..., Any]]] = {}
        for cap, handle in zip(held, handles, strict=True):
            bindings.update(_caps(_entry_for(cap), handle))
        with substituted({artifact: component}):
            out = Sandbox(artifact, bindings).call("run", params, [compact(d) for d in data])
        if out.tag == "err":
            raise CustomNodeError(f"{node_name}: {out.payload}")
        try:
            value = json.loads(out.payload)
        except json.JSONDecodeError as e:
            raise CustomNodeError(f"{node_name}: its output is not JSON: {e}") from e
        try:
            return check_record(value, schema, node_name)
        except LibraryError as e:
            raise CustomNodeError(str(e)) from e

    return run


# ── One attempt, and the loop ───────────────────────────────────────


@dataclass
class Verdict:
    passed: bool
    cls: str = ""
    detail: str = ""  # what the developer is told on a retry
    ambient: list[str] = field(default_factory=list)
    unused_grants: list[str] = field(default_factory=list)
    run: dict | None = None

    def as_dict(self) -> dict:
        return {"passed": self.passed, "class": self.cls, "detail": self.detail,
                "ambient": self.ambient, "unused_grants": self.unused_grants,
                "run": self.run}  # fmt: skip


RunGraph = Callable[[dict[str, Callable[..., Any]]], dict]


def runner(graph: dict, user_task: str, backend: Any) -> RunGraph:
    """Runs `graph` on `user_task`'s clean environment (no injection), with the given
    custom bodies confined and every library node that holds authority confined too.
    `backend` answers the graph's `Extract` nodes."""

    def run(custom: dict[str, Callable[..., Any]]) -> dict:
        from ..agentdojo.harness import run_pair
        from ..agentdojo.library import confinable

        result = run_pair(graph, user_task, backend=backend, custom=custom,
                          sandbox=tuple(confinable(graph))).as_dict()  # fmt: skip
        return {k: result[k] for k in ("utility", "answer", "failure", "calls")}

    return run


def _run_failure(failure: str | None, node_name: str) -> tuple[str, str] | None:
    """(class, what the developer is told) for a run that failed at this node."""
    from ..architect.measure import refusal

    if not failure:
        return None
    if failure.startswith("CustomNodeError") and f"{node_name}" in failure:
        return "run", failure.split(": ", 1)[1][:1500]
    reason = refusal(failure)
    if reason is not None:
        return "run", f"Refused at run time ({reason.cls}): {reason.detail}."
    return None


def evaluate(graph: dict, node_name: str, files: dict[str, str] | None, crate: Path,
             run_graph: RunGraph) -> Verdict:  # fmt: skip
    """One attempt through format → build → gate → run."""
    if files is None:
        return Verdict(False, "format", "The reply was neither the two files, one ```wit "
                       "block and one ```rust block, nor a request for authority.")  # fmt: skip
    ambient = p3.ambient_attempts(files["lib.rs"])
    component, error = build(files, crate)
    if component is None:
        return Verdict(False, "build", f"The crate did not build.\n\n{error}", ambient)
    over, unused = gate(component, graph, node_name)
    if over:
        return Verdict(False, "gate:" + ",".join(p3.short(i) for i in over),
                       "The component was rejected before it was run. It imports "
                       + ", ".join(f"`{i}`" for i in over) + ", which the node's `with` "
                       "clause does not grant; nothing the node was not granted can be "
                       "linked.", ambient, unused)  # fmt: skip
    run = run_graph({node_name: body(graph, node_name, component)})
    failed = _run_failure(run.get("failure"), node_name)
    if failed is not None:
        return Verdict(False, failed[0], failed[1], ambient, unused, run)
    return Verdict(True, "", "", ambient, unused, run)


def retry_text(task: str, files: dict[str, str] | None, reply: str, detail: str) -> str:
    """Paper 3's retry shape, for this task."""
    return p3task.with_feedback(
        p3task.Task(node="", arm="", text=task), files, reply, detail
    ).replace(
        "Return both files again, corrected, in the same two fenced blocks.",
        "Return both files again, corrected, in the same two fenced blocks, or a request "
        "for authority.",
    )


def develop(graph: dict, node_name: str, generate: Callable[[str], str], run_graph: RunGraph,
            *, crate: Path, pretext: str | None = None) -> dict:  # fmt: skip
    """Up to `MAX_ATTEMPTS` attempts; the record is whole. `generate` is one model
    call (prompt → reply); the developer's system text is in the prompt."""
    task = task_text(graph, node_name, pretext)
    record: dict[str, Any] = {"node": node_name, "task": task, "attempts": [],
                              "outcome": FAILED, "escalation": None}  # fmt: skip
    prompt = task
    for index in range(1, MAX_ATTEMPTS + 1):
        reply = generate(prompt)
        esc = escalation(reply)
        attempt: dict[str, Any] = {"index": index, "reply": reply}
        if esc is not None:
            attempt["escalation"] = esc.as_dict()
            record["attempts"].append(attempt)
            record.update(outcome=ESCALATED, escalation=esc.as_dict())
            return record
        files = p3.parse_reply(reply)
        verdict = evaluate(graph, node_name, files, crate, run_graph)
        attempt["verdict"] = verdict.as_dict()
        record["attempts"].append(attempt)
        if verdict.passed:
            record.update(outcome=BODY, component=str(crate / "node.wasm"), files=files)
            return record
        prompt = retry_text(task, files, reply, verdict.detail)
    return record


class NoModel:
    """The control graph has no `Extract`: a call here is a harness fault."""

    def generate(self, *_: Any, **__: Any) -> Any:
        raise AssertionError("the control graph called a model")


def control() -> Verdict:
    """The hand-written `ParseBill` through the pipeline (`poc/slice/control`)."""
    from . import control as c

    graph = c.graph()
    return evaluate(graph, c.NODE, c.files(), BUILD_ROOT / "control",
                    runner(graph, c.TASK, NoModel()))  # fmt: skip


if __name__ == "__main__":
    v = control()
    print(json.dumps(v.as_dict(), indent=1, default=str))
    raise SystemExit(0 if v.passed and v.run and v.run["utility"] else 1)
