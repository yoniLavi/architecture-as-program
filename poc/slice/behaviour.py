"""What a graph would *do* with each grant: the behaviour-shown reviewer's view (task 2.1).

The registered reviewer saw type strings (`ScheduledPayments<['Rent'], [amount, date]>`)
and passed most widenings, 42 of them field or mode widenings whose every literal stands
in the prompt (task 1.2). This view says instead what the graph can do over each handle:
which payees and amounts it admits, which orders and fields it can change, and, for each
field a writer sends, where the graph gets its value — a constant, the task's words, bank
data, or a model's answer and what that model read — or that the graph never sets it.

**The analysis is the predictions' taint analysis, generalised** (`poc/agentdojo/predict.py`).
Taint asks one question, whether a known injection vector reaches a field; a reviewer
knows no vector, so this asks where every field comes from, by the same rules: readers
originate their scope; the selectors pass a record through and `SumAmounts` sums bank
amounts; `Compose` takes exactly the paths its expressions read; `Extract` (and a
`Custom` node) makes every field it names a model's (a developer's) answer over all it
read. A test holds the two together: every field taint marks as influenced has the
vector's scope among its origins here.

**Limits, as taint's.** It trusts the library's bodies to do what the catalogue says,
and a `where` that reads a field steers *which* record is chosen without appearing as a
field's origin. A list's fields stand for its elements' fields. A `Custom` node's
fields are taken as its developer's answer over everything it reads, since its body is
not yet written when the graph is reviewed.

Deterministic and stdlib-only; it calls no model.
"""

from __future__ import annotations

from dataclasses import dataclass

from type_parser import DYNAMIC_PAYEES, TApp, TList, TName, TString, parse_type

from ..agentdojo.library import (
    COMPOSE,
    CUSTOM,
    EXTRACT,
    READER,
    RECORDS,
    RESPOND,
    SELECTOR,
    SLICE_CATALOGUE,
    START,
    WRITER,
    _field_spec_paths,
    custom_schema,
)

ALL = "*"  # every field of a value

TASK = ("task",)


def bank(scope: str) -> tuple:
    return ("bank", scope)


# An origin is one of: TASK; ("bank", scope); ("const", value);
# ("model", node, reads) or ("custom", node, reads), where `reads` is the frozenset
# of TASK / bank origins upstream of that node.
Prov = frozenset


def _reads(origins: frozenset) -> frozenset:
    """The task and bank origins behind `origins`, through any model's reads."""
    out: set = set()
    for o in origins:
        if o[0] in ("task", "bank"):
            out.add(o)
        elif o[0] in ("model", "custom"):
            out |= o[2]
    return frozenset(out)


def _field(value: dict[str, frozenset], name: str) -> frozenset:
    if name in value:
        return value[name]
    return value.get(ALL, frozenset())


def _whole(value: dict[str, frozenset]) -> frozenset:
    return frozenset().union(*value.values()) if value else frozenset()


def _held_scope(node: dict, caps: set[str]) -> str | None:
    for c in node["inputs"]:
        if c in caps and c.startswith("DBHandle<'"):
            return c.split("'")[1]
    return None


def provenance(graph: dict) -> dict[str, dict[str, frozenset]]:
    """Node name → its output's field → the origins of that field (`ALL` for every
    field). A node whose output names no fields (a writer's receipt) maps to {}."""
    caps = set(graph["capabilities"])
    nodes = {n["name"]: n for n in graph["nodes"]}
    inputs: dict[str, dict[int, list[str]]] = {n: {} for n in nodes}
    for e in graph["data_edges"]:
        src = e["from"].split(".")[0]
        if src in nodes and e["to"] in nodes:
            inputs[e["to"]].setdefault(e.get("to_input", 0), []).append(src)
    out: dict[str, dict[str, frozenset]] = {}
    visiting: set[str] = set()

    def visit(name: str) -> dict[str, frozenset]:
        if name in out:
            return out[name]
        if name in visiting:  # a cycle, which the validator rejects
            return {}
        visiting.add(name)
        node = nodes[name]
        entry = SLICE_CATALOGUE[node["uses"]]
        by_pos: dict[int, dict[str, frozenset]] = {}
        for pos, srcs in inputs[name].items():
            merged: dict[str, set] = {}
            for s in srcs:
                for k, v in visit(s).items():
                    merged.setdefault(k, set()).update(v)
            by_pos[pos] = {k: frozenset(v) for k, v in merged.items()}
        upstream = (
            frozenset().union(*(_whole(v) for v in by_pos.values())) if by_pos else frozenset()
        )
        value: dict[str, frozenset]
        if entry.family == START:
            value = {ALL: frozenset({TASK})}
        elif entry.family == READER:
            value = {ALL: frozenset({bank(_held_scope(node, caps) or "?")})}
        elif entry.family == SELECTOR:
            first = by_pos.get(0, {})
            value = {"amount": _whole(first)} if node["uses"] == "SumAmounts" else dict(first)
        elif entry.family == COMPOSE:
            value = {}
            for fname, spec in node.get("params", {}).get("fields", {}).items():
                paths = _field_spec_paths(spec)
                if not paths:
                    value[fname] = frozenset({("const", spec)})
                    continue
                got: set = set()
                for path in paths:
                    pos, _, rest = path[2:].partition(".")
                    src = by_pos.get(int(pos), {})
                    head = rest.split(".")[0]
                    got |= _field(src, head) if head else _whole(src)
                value[fname] = frozenset(got)
        elif entry.family in (EXTRACT, CUSTOM):
            reads = _reads(upstream)
            if entry.family == CUSTOM:
                scope = _held_scope(node, caps)
                if scope:
                    reads |= {bank(scope)}
                fields = custom_schema(node)
            else:
                fields = node.get("params", {}).get("fields", {})
            origin = ("model" if entry.family == EXTRACT else "custom", name, frozenset(reads))
            value = {f: frozenset({origin}) for f in fields}
        else:  # WRITER, RESPOND: nothing downstream reads a field of theirs
            value = {}
        visiting.discard(name)
        out[name] = value
        return value

    for name in nodes:
        visit(name)
    return out


# ── The scopes, read off the type (quoted set names read as the set) ─


@dataclass(frozen=True)
class Scope:
    kind: str
    payees: tuple[str, ...] = ()  # literal payees
    dynamic: tuple[str, ...] = ()  # 'any', 'inbound-senders'
    cap: str | None = None  # None: uncapped
    recurring: bool = False
    orders: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    scope: str = ""  # a DBHandle's
    mode: str = ""


def _items(arg) -> list:
    return list(arg.items) if isinstance(arg, TList) else []


def read_scope(cap: str) -> Scope:
    """A grant's scope, read from the type without the parser's refusals: the
    registered records predate its refusal of a quoted `'any'`, and this view must
    describe what they hold."""
    ast = parse_type(cap)
    head = ast.head if isinstance(ast, TApp) else ast.name if isinstance(ast, TName) else cap
    args = list(ast.args) if isinstance(ast, TApp) else []
    if head == "Payments" and args:
        lit, dyn = [], []
        for i in _items(args[0]):
            text = i.value if isinstance(i, TString) else getattr(i, "name", str(i))
            (dyn if text in DYNAMIC_PAYEES else lit).append(text)
        cap_arg = args[1] if len(args) > 1 else None
        amount = cap_arg.value if isinstance(cap_arg, TString) else None
        recurring = any(isinstance(a, TName) and a.name == "recurring" for a in args[2:])
        return Scope(head, tuple(lit), tuple(dyn), amount, recurring)
    if head == "ScheduledPayments" and len(args) == 2:
        orders = tuple(i.value if isinstance(i, TString) else str(i) for i in _items(args[0]))
        fields = tuple(getattr(i, "name", str(i)) for i in _items(args[1]))
        return Scope(head, orders=orders, fields=fields)
    if head == "UserProfile" and args:
        return Scope(head, fields=tuple(getattr(i, "name", str(i)) for i in _items(args[0])))
    if head == "DBHandle" and args:
        s = args[0].value if isinstance(args[0], TString) else str(args[0])
        mode = getattr(args[1], "name", "") if len(args) > 1 else ""
        return Scope(head, scope=s, mode=mode)
    return Scope(head)


# ── The rendering ───────────────────────────────────────────────────

WRITER_DOES = {
    "SendMoney": "sends one payment",
    "ScheduleTransaction": "schedules a new payment",
    "UpdateScheduledTransaction": "changes an existing scheduled payment",
    "UpdateUserInfo": "changes the user's profile",
}


def _origin(o: tuple) -> str:
    if o == TASK:
        return "the task's words"
    if o[0] == "bank":
        return _source(o[1])
    if o[0] == "const":
        return f"the constant {o[1]!r}"
    return ""


def _source(scope: str) -> str:
    if scope.startswith("file:"):
        return f"the file '{scope[5:]}' (bank data)"
    return f"the bank's {scope} (bank data)"


def _describe(origins: frozenset, names: dict[str, str]) -> str:
    """One field's origins, in words, models first."""
    parts: list[str] = []
    for o in sorted(origins, key=repr):
        if o[0] in ("model", "custom"):
            who = "a model's answer" if o[0] == "model" else "developer-written code's output"
            read = "; ".join(sorted(_origin(r) for r in o[2])) or "nothing"
            parts.append(f"{who} ({names.get(o[1], o[1])}), from: {read}")
        else:
            parts.append(_origin(o))
    return " | ".join(parts) if parts else "nothing the graph computes"


def _payees(s: Scope) -> str:
    out = []
    if "any" in s.dynamic:
        out.append("any payee at all")
    if "inbound-senders" in s.dynamic:
        out.append("anyone who has sent the user money")
    out += [repr(p) for p in s.payees]
    return ", ".join(out) if out else "no payee"


def _writer(node: dict, cap: str, prov: dict, inputs: dict, names: dict) -> list[str]:
    s = read_scope(cap)
    n = names[node["name"]]
    lines = [f"  {n} ({node['uses']}) {WRITER_DOES.get(node['uses'], 'writes')}."]
    if s.kind == "Payments":
        mode = "recurring standing orders" if s.recurring else "one-off payments"
        lines.append(f"  The handle admits: {mode}; to {_payees(s)}; "
                     + (f"at most {s.cap} each." if s.cap else "any amount (no cap)."))  # fmt: skip
    elif s.kind == "ScheduledPayments":
        lines.append(f"  The handle admits changing the orders {list(s.orders)}, "
                     f"and only their fields {list(s.fields)}.")  # fmt: skip
    elif s.kind == "UserProfile":
        lines.append(f"  The handle admits changing the fields {list(s.fields)}.")
    entry_inputs = SLICE_CATALOGUE[node["uses"]].inputs or ("",)
    record = RECORDS.get(entry_inputs[0]) or custom_schema(node)
    srcs = inputs.get(node["name"], [])
    value: dict[str, set] = {}
    for src in srcs:
        for k, v in prov.get(src, {}).items():
            value.setdefault(k, set()).update(v)
    lines.append("  Where the graph gets each field it sends:")
    for field in record:
        got = frozenset(value[field]) if field in value else frozenset(value.get(ALL, ()))
        text = _describe(got, names) if got else "never set by the graph (left unchanged)"
        scoped = s.kind in ("ScheduledPayments", "UserProfile") and field != "id"
        note = ""
        if scoped and got and field not in s.fields:
            note = "  [outside the handle: refused at run time]"
        elif scoped and not got and field in s.fields:
            note = "  [the handle admits it, the graph never uses it]"
        lines.append(f"  - {field}: {text}{note}")
    return lines


def _rank(name: str) -> tuple:
    return (0, int(name[1:])) if name[:1] == "N" and name[1:].isdigit() else (1, name)


def render(graph: dict, names: dict[str, str] | None = None) -> str:
    """The behaviour of every grant of `graph`, with nodes called by `names` (the
    reviewer's `N1…Nk`; identity if None)."""
    names = names or {n["name"]: n["name"] for n in graph["nodes"]}
    caps = list(graph["capabilities"])
    prov = provenance(graph)
    inputs: dict[str, list[str]] = {}
    for e in graph["data_edges"]:
        inputs.setdefault(e["to"], []).append(e["from"].split(".")[0])
    consumers: dict[str, list[str]] = {}
    for e in graph["data_edges"]:
        consumers.setdefault(e["from"].split(".")[0], []).append(e["to"])
    blocks: list[str] = []
    for cap in caps:
        holders = [n for n in graph["nodes"] if cap in n["inputs"]]
        lines = [cap]
        if not holders:
            lines.append("  Held by no node: the graph never uses it.")
        for node in sorted(holders, key=lambda n: _rank(names[n["name"]])):
            family = SLICE_CATALOGUE[node["uses"]].family
            n = names[node["name"]]
            if family == WRITER:
                lines += _writer(node, cap, prov, inputs, names)
            elif family == READER:
                to = sorted({names[c] for c in consumers.get(node["name"], [])}, key=_rank)
                lines.append(f"  {n} ({node['uses']}) reads {_source(read_scope(cap).scope)}; "
                             f"it goes to {', '.join(to) or 'no node'}.")  # fmt: skip
            elif family == EXTRACT:
                fields = list(node.get("params", {}).get("fields", {}))
                read = "; ".join(sorted(_origin(r) for r in _reads(
                    frozenset().union(*(_whole(prov[s]) for s in inputs.get(node["name"], [])))
                ))) or "nothing"  # fmt: skip
                lines.append(f"  {n} (Extract) asks a model for {fields}, from: {read}.")
            elif family == RESPOND:
                lines.append(f"  {n} (Respond) sends the final answer to the user.")
            elif family == CUSTOM:
                role = node.get("params", {}).get("role", "")
                lines.append(f"  {n} (Custom) is developer-written code: {role!r}. "
                             "It may use this handle in any way the handle admits.")  # fmt: skip
            else:
                lines.append(f"  {n} ({node['uses']}) holds it.")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
