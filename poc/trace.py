"""A structured execution trace of a signal-graph run.

The runtime already *knows*, per run, everything a reader otherwise reconstructs
from prose: the order nodes ran in, which enforcement tier ran each, what trust
label every value carried, and which capability instances were crossed. This
module gives that knowledge a first-class, machine-readable form so the run itself
becomes a checked artifact — pinned by a committed schema, deterministic across
builds, and rendered (later) by the graph inspector without re-deriving anything.

Three design commitments, each load-bearing:

* **Two layers, one of them derived.** A `Call` is a per-use record — interface,
  instance, operation, sequence position — in encounter order and undeduplicated.
  A `Crossing` is `(interface, instance)`, deduplicated, and is *computed from* the
  calls rather than recorded beside them. The two answer different questions for
  different readers: an auditor asks what authority a node exercised, a debugger
  asks what happened on one run.

  The projection is what makes the tiers comparable. The host tier calls a
  capability method once; the confined tier's component runs its own internal loop
  and crosses the *same* interface a different number of times, under a different
  function name (`respond` vs `generate`). Forgetting operation and sequence is
  exactly what erases that legitimate difference, so the structural equality
  `tests/test_poc_sandbox.py` asserts is now a property of the projection rather
  than a coincidence between two hand-maintained views. The call layer is
  correspondingly excluded from structural comparison — the tiers *should* differ
  there.

  What the call layer is not: sufficient for replay. Durable-execution systems that
  replay (Golem journals precisely this at a component's WIT boundary) also record
  argument and return *values*, which nothing here captures. This layer is the
  ordering and multiplicity replay would need, not the data.

* **Determinism by construction.** No wall-clock timestamps, no randomness in any
  structural field. Crossings are emitted in a sorted order, so two runs of the
  same graph and input serialise byte-for-byte identically. Timing, when recorded
  at all, lives in one optional field (`timing_us`) that structural comparison and
  the schema both treat as absent.

* **Nesting mirrors execution.** A sub-graph node carries the child run's whole
  `GraphTrace` under its `subgraph` field, so a composed run is inspectable at both
  altitudes — the parent's crossings and, one level down, the child's.

The recording itself happens at the capability handle (see `RecordingHandle`),
threaded by the runtime, so a node body cannot forge or suppress an entry on the
confined tier. On the host tier recording is exactly as circumventable as
everything else there — that is a property of the host tier, not of this trace.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .values import Untrusted, Variant

# The two points of the trust lattice, at the value level. A value is `untrusted`
# iff it is wrapped in `Untrusted<_>`; everything else is `trusted`. A node *raises*
# trust when it consumes an untrusted input and emits a trusted output — which the
# graph requires it to declare via `discharges_trust`, and which the trace makes
# observable after the fact.
TRUSTED = "trusted"
UNTRUSTED = "untrusted"

# The committed schema the emitted traces are pinned to. It lives here, beside the
# model, rather than under graphs/: graphs/ is globbed as *graph definitions* (see
# graph.graphs_by_name, which loads every graphs/*.json as a graph), so a schema
# file there would be mis-read as a graph. This is the poc-local home the change's
# design.md sanctions when a graphs/ home is not cleaner.
SCHEMA_PATH = Path(__file__).resolve().parent / "trace-schema.json"


def trust_label(value: object) -> str:
    """The trust label a value carries. A `Variant` is unwrapped to its payload
    first, so a sum-typed node's output is labelled by what it actually emits."""
    if isinstance(value, Variant):
        value = value.value
    return UNTRUSTED if isinstance(value, Untrusted) else TRUSTED


@dataclass(frozen=True)
class Crossing:
    """One capability-boundary crossing: the WIT interface crossed and the name of
    the capability instance it landed on.

    Deliberately not an operation-level record. `respond` on the host tier and
    `generate` on the confined tier are the same crossing of the same `tool-llm`
    interface; naming the operation would make the two tiers disagree for no gain.
    The instance name is the graph-declared identity where one exists (so identity
    routing is visible — `customer_session` rather than a bare `user-session`), and
    the capability's scope otherwise."""

    interface: str
    instance: str

    def to_dict(self) -> dict:
        return {"interface": self.interface, "instance": self.instance}


@dataclass(frozen=True)
class Call:
    """One *use* of a capability, in encounter order and undeduplicated: the
    interface crossed, the instance it landed on, the operation reached for, and
    the position in this node's call sequence.

    This is the layer the durable-execution systems record (Golem journals exactly
    this at a component's WIT boundary) and the layer replay would need. It is
    deliberately *not* tier-comparable: the host tier calls a capability once where
    a confined component loops internally, under different operation names, and
    that difference is real rather than noise to be suppressed. `Crossing` above is
    its projection, and that is the tier-comparable view.

    Honesty constraint: on the host tier this record is exactly as circumventable
    as every other host-tier guarantee — a node that declines to play by the object
    model can drive the wrapper however it likes. Confined-tier-authoritative,
    host-tier-advisory; a more detailed artifact is not a stronger one."""

    interface: str
    instance: str
    operation: str
    index: int

    def to_dict(self) -> dict:
        return {
            "interface": self.interface,
            "instance": self.instance,
            "operation": self.operation,
            "index": self.index,
        }


@dataclass
class NodeTrace:
    """One node's run: which tier ran it, the trust it received and produced, the
    capability uses it made — as an ordered per-call journal and as the
    deduplicated projection of it — and, for a sub-graph node, the nested run of
    its body."""

    node: str
    tier: str
    input_trust: str
    output_trust: str | None = None
    calls: list[Call] = field(default_factory=list)
    subgraph: GraphTrace | None = None
    # Excluded from every structural comparison and from the schema's required
    # fields. Present only when a run is asked to time itself; never populated on
    # the paths the pins compare, so structure stays deterministic.
    timing_us: float | None = None

    @property
    def crossings(self) -> list[Crossing]:
        """The distinct capability crossings, *derived* from `calls` by forgetting
        operation and sequence and deduplicating.

        Deriving rather than recording separately is what keeps the two layers from
        disagreeing: the structural equality of the two tiers' traces is now a
        property of this projection rather than a coincidence between two
        independently maintained views. First-encounter order is preserved;
        serialisation sorts."""
        seen: list[Crossing] = []
        for call in self.calls:
            crossing = Crossing(call.interface, call.instance)
            if crossing not in seen:
                seen.append(crossing)
        return seen

    def record_call(self, interface: str, instance: str, operation: str) -> None:
        """Record one capability use. The deduplicated crossing follows from it."""
        self.calls.append(Call(interface, instance, operation, len(self.calls)))

    def raises_trust(self) -> bool:
        """True iff this node consumed untrusted input and emitted trusted output —
        the observable signature of a trust discharge."""
        return self.input_trust == UNTRUSTED and self.output_trust == TRUSTED

    def to_dict(self, *, include_timing: bool = True, include_calls: bool = True) -> dict:
        # Crossings are sorted, not emitted in encounter order: encounter order is a
        # per-tier artefact (the host and confined tiers touch handles in different
        # orders), and sorting is what makes the two tiers' traces structurally
        # equal and every run byte-identical.
        ordered = sorted(self.crossings, key=lambda c: (c.interface, c.instance))
        out: dict = {
            "node": self.node,
            "tier": self.tier,
            "input_trust": self.input_trust,
            "output_trust": self.output_trust,
            "crossings": [c.to_dict() for c in ordered],
        }
        # The per-call journal is emitted in encounter order and omitted from the
        # structural form, for the same reason timing is: the two tiers legitimately
        # differ here, so including it in a comparison would make the tier-equality
        # property fail for a difference that is not a defect.
        if include_calls and self.calls:
            out["calls"] = [c.to_dict() for c in self.calls]
        if self.subgraph is not None:
            out["subgraph"] = self.subgraph.to_dict(
                include_timing=include_timing, include_calls=include_calls
            )
        if include_timing and self.timing_us is not None:
            out["timing_us"] = self.timing_us
        return out


@dataclass
class GraphTrace:
    """A whole run, in execution order. The root of a trace document; also the
    value nested under a sub-graph node's `subgraph` field."""

    graph: str
    nodes: list[NodeTrace] = field(default_factory=list)

    def to_dict(self, *, include_timing: bool = True, include_calls: bool = True) -> dict:
        return {
            "graph": self.graph,
            "nodes": [
                n.to_dict(include_timing=include_timing, include_calls=include_calls)
                for n in self.nodes
            ],
        }

    def structural(self) -> dict:
        """The trace with timing and the per-call journal excluded — the form the
        determinism test compares, the schema pins, and the two tiers must agree on.
        What remains is the projection: interface identity and instance, deduplicated."""
        return self.to_dict(include_timing=False, include_calls=False)

    def walk(self):
        """Yield every `NodeTrace` in the run, descending into sub-graphs. Lets a
        check (e.g. "trust is raised only at the discharge node") reason over the
        whole composed run, not just the top level."""
        for node in self.nodes:
            yield node
            if node.subgraph is not None:
                yield from node.subgraph.walk()


class TraceCollector:
    """Where the currently-running node's crossings are recorded.

    One collector is shared across a whole (possibly nested) execution; the
    executor points `current` at the node it is about to run, and every
    `RecordingHandle` records into whatever that is. Because the PoC executor runs
    nodes synchronously and depth-first, there is exactly one current node at any
    instant — the same assumption the capability caretaker already relies on."""

    def __init__(self) -> None:
        self.current: NodeTrace | None = None

    def record(self, interface: str, instance: str, operation: str) -> None:
        if self.current is not None:
            self.current.record_call(interface, instance, operation)


class RecordingHandle:
    """A transparent forwarding proxy over a capability handle that records a
    crossing whenever the node reaches for the handle.

    Wrapped around the handle by the runtime just before a node runs, so recording
    is a property of the plumbing, not of node cooperation: a node cannot make a
    crossing without going through the handle it was given, and going through it is
    what records. It forwards the handle's *entire* surface (like the caretaker), so
    a node cannot tell a recording handle from the bare one — including the case
    where the wrapped handle is itself a caretaker, which this proxy sits outside of
    (record first, then the caretaker's revoke check, then the real handle).

    Recording on attribute *access* rather than call is deliberate: some confined
    adapters reach a capability through a field (`llm.backend`) rather than a method,
    and that access is still a use of the capability. Deduplication downstream makes
    the granularity irrelevant to the structural trace — one touch or ten, the node
    crossed that instance."""

    def __init__(self, target: object, interface: str, instance: str, collector: TraceCollector):
        # Real instance attributes, set past __getattr__ so their own lookup never
        # recurses into it (the caretaker uses the same trick).
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_interface", interface)
        object.__setattr__(self, "_instance", instance)
        object.__setattr__(self, "_collector", collector)

    def __getattr__(self, name: str):
        # Reached only for attributes not on the proxy itself — i.e. everything on
        # the wrapped handle. That is exactly the set of accesses that constitute
        # using the capability, so recording here, then forwarding, captures the
        # crossing without the node's knowledge.
        collector: TraceCollector = object.__getattribute__(self, "_collector")
        collector.record(
            object.__getattribute__(self, "_interface"),
            object.__getattribute__(self, "_instance"),
            name,
        )
        return getattr(object.__getattribute__(self, "_target"), name)


# ── Schema validation (stdlib-only, matching the repo's no-jsonschema stance) ──
#
# The project deliberately carries no JSON-Schema library — the graph validator is
# a hand-rolled mirror of graphs/schema.json for the same portability reason. The
# trace schema is small and closed, so a focused recursive checker covering the
# subset it uses (type unions, enum, required, properties, additionalProperties,
# items, local $ref/$defs, minLength) keeps traces schema-checkable everywhere,
# including in the stdlib-only pre-commit path, with no new dependency.


_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value: object, spec) -> bool:
    types = spec if isinstance(spec, list) else [spec]
    for t in types:
        py = _JSON_TYPES.get(t)
        if py is None:
            continue
        # bool is a subclass of int — keep them distinct so `true` is not a number.
        if t in ("number", "integer") and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def _resolve(schema: dict, root: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref {ref!r}; only local refs are handled")
    node: object = root
    for part in ref[2:].split("/"):
        node = node[part]  # type: ignore[index]
    return node  # type: ignore[return-value]


def _validate(value: object, schema: dict, root: dict, path: str, errors: list[str]) -> None:
    schema = _resolve(schema, root)

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")
        return

    if "type" in schema and not _type_ok(value, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']}, got {type(value).__name__}")
        return

    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required property {req!r}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}: unexpected property {key!r}")
        for key, sub in value.items():
            if key in props:
                _validate(sub, props[key], root, f"{path}.{key}", errors)

    elif isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(value):
                _validate(item, item_schema, root, f"{path}[{i}]", errors)

    elif isinstance(value, str):
        min_len = schema.get("minLength")
        if isinstance(min_len, int) and len(value) < min_len:
            errors.append(f"{path}: string shorter than minLength {min_len}")


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def validate_document(document: dict, schema: dict | None = None) -> list[str]:
    """Validate a trace document against the committed schema. Returns the list of
    violations — empty means valid — matching the graph validator's convention."""
    root = schema if schema is not None else load_schema()
    errors: list[str] = []
    _validate(document, root, root, "trace", errors)
    return errors
