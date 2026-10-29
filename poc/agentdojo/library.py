"""The node library an architect composes banking graphs from (design, Decision 1).

An architect writes wiring and parameters, never code. Each node of a banking graph
names a library entry (`"uses"`) and gives it parameters (`"params"`); its body is
the entry's, here, and (task 3.4) its confined component. Three families:

* **tool nodes**, one per banking tool operation: the readers, which hold a
  bank-backed `DBHandle<scope, read>`, and the writers, which hold a banking kind;
* **deterministic nodes**: `Start`, the selectors (`SelectTransaction`,
  `FilterTransactions`, `SumAmounts`, `Branch`), `Compose`, which builds a record
  from its inputs by a closed expression language, and `Respond`, which fills a
  template and sends it as the final answer;
* **`Extract`**, an inference-only model call (`LLMClient<inference>`) that
  returns a closed schema: the fields and their types are parameters, and an
  answer with any other shape fails the run.

Values are plain dicts and lists (AgentDojo's tool results, as JSON). Everything
read from the environment is labelled `Untrusted<_>`, because in AgentDojo any of
it can carry an injection; the selectors keep that label, and only `Compose`,
`Extract` and `Respond` may discharge it. Which fields actually carry attacker
text is the predictions' business (`predict.py`), not the label's.

This module is stdlib-only (no AgentDojo, no wasmtime), so the catalogue and its
check run anywhere.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from type_parser import TApp, TName, TSum, parse_type, strip_trust, unparse

from .. import contracts
from ..values import Variant

# ── The record schemas the tool nodes read and write ────────────────

# field → type ("string", "number", "boolean"); a trailing "?" marks it optional.
RECORDS: dict[str, dict[str, str]] = {
    "PaymentOrder": {"recipient": "string", "amount": "number", "subject": "string",
                     "date": "string"},
    "StandingOrder": {"recipient": "string", "amount": "number", "subject": "string",
                      "date": "string", "recurring": "boolean"},
    "OrderUpdate": {"id": "number", "recipient": "string?", "amount": "number?",
                    "subject": "string?", "date": "string?", "recurring": "boolean?"},
    "ProfileUpdate": {"first_name": "string?", "last_name": "string?", "street": "string?",
                      "city": "string?"},
}  # fmt: skip
FIELD_TYPES = frozenset({"string", "number", "boolean"})

# ── The catalogue ───────────────────────────────────────────────────

READER = "reader"
WRITER = "writer"
SELECTOR = "selector"
COMPOSE = "compose"
EXTRACT = "extract"
RESPOND = "respond"
START = "start"


@dataclass(frozen=True)
class Entry:
    """One library node. `inputs`/`output` are fixed type strings, or None where the
    architect declares the type. `capability` is the kind the `with` clause must
    hold (one at most), and `scope` constrains a reader's `DBHandle` scope."""

    name: str
    family: str
    doc: str
    inputs: tuple[str, ...] | None = None
    output: str | None = None
    capability: str | None = None
    scope: str | None = None  # a reader's DBHandle scope; "file:" means any one file
    params: Mapping[str, str] = field(default_factory=dict)  # name → what it holds
    may_discharge: bool = False


def _reader(name: str, scope: str, output: str, doc: str) -> Entry:
    return Entry(name, READER, doc, ("TaskRequest",), f"Untrusted<{output}>", "DBHandle", scope)


def _writer(name: str, record: str, capability: str, doc: str) -> Entry:
    return Entry(name, WRITER, doc, (record,), "Receipt", capability)


_WHERE = "list of predicates over a transaction, in the contract vocabulary"

CATALOGUE: dict[str, Entry] = {
    e.name: e
    for e in (
        Entry(
            "Start", START, "The entry node: passes the task on, to fan out.",
            ("TaskRequest",), "TaskRequest",
        ),
        _reader("ReadTransactions", "transactions", "TransactionList",
                "The 100 most recent transactions."),
        _reader("ReadScheduled", "scheduled-transactions", "TransactionList",
                "The scheduled (standing) transactions."),
        _reader("ReadFile", "file:", "FileText", "One file's text, named by the handle."),
        _reader("ReadUserInfo", "user-info", "UserInfo", "The profile, without the password."),
        _reader("ReadBalance", "balance", "Balance", "The account balance."),
        _reader("ReadIban", "iban", "Iban", "The account's IBAN."),
        Entry(
            "SelectTransaction", SELECTOR,
            "The one transaction matching `where`. Declare the output as `Transaction` "
            "(no match fails the run) or `found: Transaction | none: NoMatch`.",
            params={"where": _WHERE, "pick": "first | last | only (default: only)"},
        ),
        Entry("FilterTransactions", SELECTOR, "The transactions matching `where`.",
              params={"where": _WHERE}),
        Entry("SumAmounts", SELECTOR, "The sum of `amount` over those matching `where`, "
              "as `Total {amount}`.", params={"where": _WHERE}),
        Entry(
            "Branch", SELECTOR,
            "Passes its input on as `yes: T` if every `when` predicate holds, else `no: T`.",
            params={"when": "list of predicates over the input"},
        ),
        Entry(
            "Compose", COMPOSE,
            "Builds a record from its inputs. Each field is a constant, or `=` followed "
            "by an expression over `inN.path` with + - * / and parentheses.",
            params={"fields": "field name → constant or `=expression`"},
            may_discharge=True,
        ),
        Entry(
            "Extract", EXTRACT,
            "Asks a model (inference only) to read its inputs and return exactly the "
            "named fields, with their types. Any other answer fails the run.",
            capability="LLMClient",
            params={"instruction": "what to extract", "fields": "field name → type"},
            may_discharge=True,
        ),
        _writer("SendMoney", "PaymentOrder", "Payments", "Send one payment."),
        _writer("ScheduleTransaction", "StandingOrder", "Payments",
                "Schedule a payment (the handle's recurring mode)."),
        _writer("UpdateScheduledTransaction", "OrderUpdate", "ScheduledPayments",
                "Change a standing order's fields."),
        _writer("UpdateUserInfo", "ProfileUpdate", "UserProfile", "Change profile fields."),
        Entry(
            "Respond", RESPOND,
            "Fills `template` (placeholders `{inN.path}`) and sends it as the final answer.",
            output="DeliveryConfirmation", capability="ResponseChannel",
            params={"template": "the answer text, with `{inN.path}` placeholders"},
            may_discharge=True,
        ),
    )
}  # fmt: skip

# `update_password` has no library node: its kind, `Credentials`, is never granted.

# ── Paths and the expression language ───────────────────────────────

_PATH = re.compile(r"in(\d+)((?:\.[A-Za-z_][A-Za-z0-9_]*)*)")
_TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|(in\d+(?:\.[A-Za-z_][A-Za-z0-9_]*)*)|([-+*/()]))")


class LibraryError(ValueError):
    """A library node's parameters or values do not fit its entry."""


def resolve(inputs: tuple[Any, ...], path: str) -> Any:
    m = _PATH.fullmatch(path)
    if m is None:
        raise LibraryError(f"not a path: {path!r} (expected inN.field...)")
    index = int(m.group(1))
    if index >= len(inputs):
        raise LibraryError(f"{path!r} names input {index}, but the node has {len(inputs)}")
    value = inputs[index]
    for part in filter(None, m.group(2).split(".")):
        if not isinstance(value, Mapping) or part not in value:
            raise LibraryError(f"{path!r} does not resolve: no field {part!r}")
        value = value[part]
    return value


def _tokens(expr: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    expr = expr.rstrip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if m is None or m.end() == pos:
            raise LibraryError(f"not in the expression language: {expr!r} at {pos}")
        kind = "num" if m.group(1) else "path" if m.group(2) else "op"
        out.append((kind, m.group(m.lastindex or 0)))
        pos = m.end()
    return out


def evaluate(expr: str, inputs: tuple[Any, ...]) -> Any:
    """Evaluate a `Compose` expression. A lone path returns its value unchanged (a
    string stays a string); anything with an operator is arithmetic, rounded to
    cents. Closed: numbers, paths, + - * / and parentheses, nothing else."""
    tokens = _tokens(expr)
    if len(tokens) == 1 and tokens[0][0] == "path":
        return resolve(inputs, tokens[0][1])
    pos = 0

    def atom() -> float:
        nonlocal pos
        if pos >= len(tokens):
            raise LibraryError(f"expression ends early: {expr!r}")
        kind, text = tokens[pos]
        pos += 1
        if kind == "num":
            return float(text)
        if kind == "path":
            value = resolve(inputs, text)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise LibraryError(f"{text!r} is {value!r}, not a number")
            return float(value)
        if text == "(":
            value = sum_()
            if pos >= len(tokens) or tokens[pos][1] != ")":
                raise LibraryError(f"unclosed parenthesis in {expr!r}")
            pos += 1
            return value
        if text == "-":
            return -atom()
        raise LibraryError(f"unexpected {text!r} in {expr!r}")

    def product() -> float:
        nonlocal pos
        value = atom()
        while pos < len(tokens) and tokens[pos][1] in "*/":
            op = tokens[pos][1]
            pos += 1
            rhs = atom()
            value = value * rhs if op == "*" else value / rhs
        return value

    def sum_() -> float:
        nonlocal pos
        value = product()
        while pos < len(tokens) and tokens[pos][1] in "+-":
            op = tokens[pos][1]
            pos += 1
            rhs = product()
            value = value + rhs if op == "+" else value - rhs
        return value

    result = sum_()
    if pos != len(tokens):
        raise LibraryError(f"trailing tokens in {expr!r}")
    return round(result, 2)


def _field_spec_paths(spec: Any) -> list[str]:
    if isinstance(spec, str) and spec.startswith("="):
        return [t for k, t in _tokens(spec[1:]) if k == "path"]
    return []


def _fill(template: str, inputs: tuple[Any, ...]) -> str:
    def value(m: re.Match[str]) -> str:
        v = resolve(inputs, m.group(1))
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return v if isinstance(v, str) else json.dumps(v)

    return re.sub(r"\{(in\d+(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\}", value, template)


def check_record(value: Any, schema: Mapping[str, str], what: str) -> dict:
    """`value` as a record of exactly `schema`'s fields, or `LibraryError`."""
    if not isinstance(value, Mapping):
        raise LibraryError(f"{what} is {value!r}, not a record")
    extra = sorted(set(value) - set(schema))
    if extra:
        raise LibraryError(f"{what} has fields outside its schema: {extra}")
    out: dict[str, Any] = {}
    for name, ftype in schema.items():
        optional = ftype.endswith("?")
        ftype = ftype.rstrip("?")
        if name not in value or value[name] is None:
            if not optional:
                raise LibraryError(f"{what} is missing field {name!r}")
            continue
        v = value[name]
        ok = (
            isinstance(v, str)
            if ftype == "string"
            else isinstance(v, bool)
            if ftype == "boolean"
            else isinstance(v, int | float) and not isinstance(v, bool)
        )
        if not ok:
            raise LibraryError(f"{what} field {name!r} is {v!r}, not a {ftype}")
        out[name] = v
    return out


# ── Checking a graph against the catalogue ──────────────────────────


def _kind(cap: str) -> str:
    ast = parse_type(cap)
    return ast.head if isinstance(ast, TApp) else ast.name if isinstance(ast, TName) else ""


def _db_scope(cap: str) -> str | None:
    ast = parse_type(cap)
    if isinstance(ast, TApp) and ast.head == "DBHandle" and len(ast.args) == 2:
        scope = ast.args[0]
        return getattr(scope, "value", None)
    return None


def _untrusted(t: str) -> bool:
    return unparse(strip_trust(parse_type(t))) != unparse(parse_type(t))


def check_graph(graph: dict) -> list[str]:
    """Every way `graph` misuses the library; empty if it composes correctly. The
    validator's own checks (edges, the lattice, narrowing) run separately."""
    errors: list[str] = []
    caps = set(graph.get("capabilities", []))
    for n in graph.get("nodes", []):
        name = n.get("name")
        entry = CATALOGUE.get(n.get("uses", ""))
        if entry is None:
            errors.append(f"node {name!r} uses {n.get('uses')!r}, which is not in the library")
            continue
        data = [i for i in n["inputs"] if i not in caps]
        held = [i for i in n["inputs"] if i in caps]
        params = n.get("params", {})
        where = f"node {name!r} ({entry.name})"
        unknown = sorted(set(params) - set(entry.params))
        if unknown:
            errors.append(f"{where} has parameters the entry does not take: {unknown}")
        if entry.inputs is not None and tuple(data) != entry.inputs:
            errors.append(f"{where} must take {list(entry.inputs)}, not {data}")
        if entry.output is not None and n["output"] != entry.output:
            errors.append(f"{where} must emit {entry.output!r}, not {n['output']!r}")
        if not data:
            errors.append(f"{where} takes no data input")
        wanted = [entry.capability] if entry.capability else []
        if [_kind(c) for c in held] != wanted:
            errors.append(f"{where} must hold exactly {wanted or 'no capability'}, not {held}")
        elif entry.family == READER:
            scope = _db_scope(held[0]) or ""
            ok = (
                scope.startswith("file:") and len(scope) > 5
                if entry.scope == "file:"
                else (scope == entry.scope)
            )
            if not ok or not held[0].endswith(", read>"):
                errors.append(f"{where} must hold DBHandle<'{entry.scope}…', read>, not {held[0]}")
        elif entry.family == EXTRACT and held != ["LLMClient<inference>"]:
            errors.append(f"{where} must hold LLMClient<inference> only, not {held}")
        if n.get("discharges_trust") and not entry.may_discharge:
            errors.append(f"{where} may not discharge trust")
        if entry.family == SELECTOR and data:
            out = parse_type(n["output"])
            variants = [v.inner for v in out.variants] if isinstance(out, TSum) else [out]
            if any(_untrusted(unparse(v)) != _untrusted(data[0]) for v in variants):
                errors.append(f"{where} must keep its input's trust label on its output")
        errors.extend(f"{where}: {e}" for e in _check_params(entry, n, len(data)))
    return errors


def _check_params(entry: Entry, node: dict, arity: int) -> list[str]:
    params = node.get("params", {})
    errors: list[str] = []
    for key in ("where", "when"):
        if key in entry.params:
            preds = params.get(key, [])
            try:
                contracts.parse_all(preds, what=key)
            except contracts.ContractError as e:
                errors.append(str(e))
    if entry.name == "SelectTransaction" and params.get("pick", "only") not in (
        "first",
        "last",
        "only",
    ):
        errors.append(f"pick must be first, last or only, not {params.get('pick')!r}")
    if entry.family == COMPOSE:
        fields = params.get("fields")
        if not isinstance(fields, dict) or not fields:
            errors.append("Compose needs a non-empty `fields` object")
        else:
            for fname, spec in fields.items():
                try:
                    for p in _field_spec_paths(spec):
                        if int(_PATH.fullmatch(p).group(1)) >= arity:  # type: ignore[union-attr]
                            errors.append(f"field {fname!r} names an input the node lacks")
                except LibraryError as e:
                    errors.append(f"field {fname!r}: {e}")
            record = RECORDS.get(strip_output(node["output"]))
            if record is not None:
                required = {k for k, t in record.items() if not t.endswith("?")}
                missing, extra = required - set(fields), set(fields) - set(record)
                if missing or extra:
                    errors.append(
                        f"fields must fit {strip_output(node['output'])}: "
                        f"missing {sorted(missing)}, extra {sorted(extra)}"
                    )
    if entry.family == EXTRACT:
        fields = params.get("fields")
        if not isinstance(fields, dict) or not fields:
            errors.append("Extract needs a non-empty `fields` object")
        elif not all(str(t).rstrip("?") in FIELD_TYPES for t in fields.values()):
            errors.append(f"Extract field types must be among {sorted(FIELD_TYPES)}")
        if not isinstance(params.get("instruction"), str) or not params["instruction"]:
            errors.append("Extract needs an `instruction`")
    if entry.family == RESPOND and not isinstance(params.get("template"), str):
        errors.append("Respond needs a `template`")
    return errors


def strip_output(t: str) -> str:
    return unparse(strip_trust(parse_type(t)))


# ── The bodies (host tier) ──────────────────────────────────────────

EXTRACT_SYSTEM = (
    "You extract values for a banking task. Read the material and reply with one "
    "JSON object with exactly these fields and types, and nothing else: {fields}. "
    "Use null for an optional field (marked ?) you cannot fill."
)


def _matching(items: Any, where: tuple[contracts.Predicate, ...]) -> list[dict]:
    if not isinstance(items, list):
        raise LibraryError(f"expected a list of transactions, got {type(items).__name__}")
    return [t for t in items if all(p.holds(t) for p in where)]


def _parse_json_object(text: str) -> Any:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise LibraryError(f"the model's answer holds no JSON object: {text[:200]!r}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise LibraryError(f"the model's answer is not JSON: {e}") from e


def _decode(value: Any) -> Any:
    """A bank read arrives as a list of JSON strings (the `DBHandle` surface)."""
    items = [json.loads(v) if isinstance(v, str) and v[:1] in "[{" else v for v in value]
    return items


def body(node: dict, capabilities: list[str]) -> Callable[..., Any]:
    """The host-tier body of a library node, bound to its parameters."""
    entry = CATALOGUE[node["uses"]]
    params = node.get("params", {})
    output = parse_type(node["output"])

    if entry.family == START:
        return lambda request: request

    if entry.family == READER:

        def read(_request: Any, handle: Any) -> Any:
            items = _decode(handle.read(""))
            if entry.name in ("ReadTransactions", "ReadScheduled"):
                return items
            if entry.name == "ReadFile":
                return {"text": items[0] if items else ""}
            if entry.name == "ReadBalance":
                return {"amount": items[0]}
            if entry.name == "ReadIban":
                return {"iban": items[0]}
            return items[0]

        return read

    if entry.family == SELECTOR:
        key = "when" if entry.name == "Branch" else "where"
        preds = contracts.parse_all(params.get(key, []), what=key)
        if entry.name == "FilterTransactions":
            return lambda items: _matching(items, preds)
        if entry.name == "SumAmounts":
            return lambda items: {
                "amount": round(sum(t["amount"] for t in _matching(items, preds)), 2)
            }
        if entry.name == "Branch":
            return lambda value: Variant(
                "yes" if all(p.holds(value) for p in preds) else "no", value
            )
        pick = params.get("pick", "only")
        optional = isinstance(output, TSum)

        def select(items: Any) -> Any:
            found = _matching(items, preds)
            if pick == "only" and len(found) > 1:
                raise LibraryError(f"{len(found)} transactions match; `only` wants one")
            if not found:
                if optional:
                    return Variant("none", {"matched": 0})
                raise LibraryError("no transaction matches")
            chosen = found[-1] if pick == "last" else found[0]
            return Variant("found", chosen) if optional else chosen

        return select

    if entry.family == COMPOSE:
        fields = params["fields"]
        record = RECORDS.get(strip_output(node["output"]))

        def compose(*inputs: Any) -> Any:
            built = {
                k: evaluate(v[1:], inputs) if isinstance(v, str) and v.startswith("=") else v
                for k, v in fields.items()
            }
            return check_record(built, record, node["name"]) if record else built

        return compose

    if entry.family == EXTRACT:
        schema = {k: str(v) for k, v in params["fields"].items()}
        system = EXTRACT_SYSTEM.format(fields=json.dumps(schema))

        def extract(*args: Any) -> Any:
            *inputs, llm = args
            material = json.dumps(inputs if len(inputs) > 1 else inputs[0], indent=1)
            answer = llm.infer(
                system=system,
                prompt=f"{params['instruction']}\n\nMaterial:\n{material}",
                task=f"extract:{node['name']}",
            )
            return check_record(_parse_json_object(answer), schema, node["name"])

        return extract

    if entry.family == WRITER:
        record = RECORDS[entry.inputs[0]]  # type: ignore[index]

        def write(order: Any, handle: Any) -> Any:
            order = check_record(order, record, node["name"])
            if entry.name == "SendMoney":
                result = handle.send(**order)
            elif entry.name == "ScheduleTransaction":
                result = handle.schedule(**order)
            elif entry.name == "UpdateScheduledTransaction":
                result = handle.update(int(order.pop("id")), **order)
            else:
                result = handle.update(**order)
            return {"result": result}

        return write

    if entry.family == RESPOND:
        template = params["template"]

        def respond(*args: Any) -> Any:
            *inputs, channel = args
            return channel.send(_fill(template, tuple(inputs)))

        return respond

    raise LibraryError(f"no body for {entry.name}")  # pragma: no cover


def bodies(graph: dict) -> dict[str, Callable[..., Any]]:
    """Node name → body, for every node of a library graph."""
    caps = list(graph.get("capabilities", []))
    return {n["name"]: body(n, caps) for n in graph["nodes"]}


__all__ = [
    "CATALOGUE",
    "RECORDS",
    "Entry",
    "LibraryError",
    "bodies",
    "check_graph",
    "check_record",
    "evaluate",
]
