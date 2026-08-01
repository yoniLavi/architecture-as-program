# Prior art: what we surveyed, what we took, what we did not

A standing record of engagement with the community of practice, kept because the
alternative — citations attached to decisions already made — is a failure mode
this project has had and is trying to correct. The rule here is that a survey
entry must say **what changed**, or say plainly that nothing did.

Papers cite from `citations.bib`; this file is the reasoning behind those
citations and, more importantly, behind the design decisions they informed.

---

## Survey, July 2026 — six domains

Run across WASM component tooling, durable execution, authorization and
delegation, typed effects in production languages, agent frameworks and
sandboxing, and dataflow UX. Findings below are ordered by consequence, not by
domain.

### 1. TACIT — the closest concurrent work, and it is close

Odersky, Zhao, Xu, Bračevac and Pham, *Securing Agents With Tracked
Capabilities*, **Best Paper, ACM CAIS 2026** (arXiv:2603.00991 as *Tracking
Capabilities for Safer Agents*). Agents write Scala 3 under capture checking
rather than calling tools; the type system statically prevents generated code
from forging access rights or exceeding its capability budget, and
`Classified[T]` is a type-level trust wrapper discharged only through designated
mechanisms. Evaluated on τ2-bench and SWE-bench Lite across three model
families, reporting no loss in task performance.

This is our thesis one layer down, from the author of the capture-checking work
we already cite. **What distinguishes this work has to be stated, not assumed:**

- TACIT checks freeform imperative snippets as they arrive. We validate a fixed
  topology at assembly time, before anything runs. Neither is strictly stronger:
  they buy open-ended expressiveness, we buy static analysability.
- TACIT's capture checker is the *only* boundary, at the source-language level —
  which is why they ship a restricted "safe subset" to disable casts and
  reflection. Our WASM import table holds even if every analysis above it is
  wrong.
- `Classified[T]` is per-computation. Our trust lattice propagates across a
  wiring, applied uniformly to edges and node bodies.

It is also the evaluation template our roadmap experiment must match: standard
benchmarks, multiple model families, a task-performance control.

### 2. The novelty claim narrows — and survives, but only in its narrow form

"Authority is declared per-component rather than ambient" is **not novel**. It
is what wasmCloud (`wadm` links routing an interface to a named provider
instance), Fermyon Spin (`allowed_outbound_hosts`), and wasi-virt all ship in
production today.

wasi-virt matters most: it composes a virtual adapter into a component to
*physically remove* WASI imports, which already makes confinement a property of
the artifact rather than the host's configuration. That is the distinction §3.3.2
draws, and the Bytecode Alliance has tooling for it.

**What no surveyed system does** — and this is where the defensible claim now
sits — is *derive* the permitted import set from a **separate, higher-level
architecture model** and *gate the build* on comparing it against the compiled
binary. wasmCloud's manifests and WAC's `wac targets` both check against
hand-authored WIT. Nobody generates the world from something like our graph JSON
and then holds the binary to it as a regression gate.

Stated as strong-but-not-certain: this was a documentation-level survey, not a
code audit.

**Taken:** narrow the rhetoric in §1/§3.3.2 so "declared not ambient" is not
leaned on as novel; cite wasi-virt, wasmCloud and WAC as nearest prior art.
**Not taken (yet):** wasi-virt-style forced composition as defence-in-depth on
top of the derive-and-compare test, so drift is unforgeable rather than merely
tested. Recorded as a research-agenda item.

### 3. The text-vs-graph premise does not hold as a *comprehension* claim

The strongest single finding of the survey, and it argues against us.

No production system that runs graphs at hundreds-of-nodes scale lets a human
author the graph visually. Dagster, Airflow, Prefect, Kedro and Bazel are all
authored in **text**, with the graph as a generated, read-only, queryable view.
Enso is the one serious counterexample with genuine bidirectional graph↔text
sync — and its market fit narrowed to small-graph analyst tooling rather than
displacing text for software systems.

The founding premise ("agents removed the human objection to graph
representations") is about *authoring*, and nothing found bears on it either
way — it is untested, not refuted. But the adjacent claim that a graph is a
better *comprehension* surface at scale is contradicted by every production
system built by people with every incentive to make visual authoring work.

**Taken:** state this openly as a limitation. It costs nothing, because the
inspector already occupies the defensible position — views and runs, does not
author — and it pre-empts a reviewer making the argument less charitably.

### 4. Hard numbers for the scale threat

Yoghourdjian, Archambault, Diehl, Dwyer, Klein, Purchase and Wu, *Exploring the
Limits of Complexity: A Survey of Empirical Studies on Graph Visualisation*
(Visual Informatics, 2018; arXiv:1809.00270), surveying 152 studies:

- ~120 nodes is roughly the ceiling for completing graph-reading tasks in under
  two minutes (Kobourov et al.).
- Trees of 42–346 nodes rate "easy"; 1192–5480 rate "hard" (Borkin et al.).
- **Density matters more than count**: dense graphs become unreadable
  "hairballs" from 10–15 nodes, while globally sparse structures stay
  comprehensible at large node counts.

**Taken:** replace "real systems have hundreds of nodes" with these figures.
They cut both ways honestly — our nine-node graph is deep in easy territory, and
a 200-node capability graph sits at the edge of what has been empirically tested
at all. The density finding is the one point in our favour: a well-typed
capability graph with disciplined fan-in could stay sparse by construction, and
that is a testable prediction rather than a hope.

### 5. Principal binding — a design, not just references

The best constructive result. Every surveyed system that keeps delegation
*reasoned about* — Cedar's SMT-checkable policies, Biscuit's Datalog checks,
AWS IAM's policy intersection — does so by restricting the attenuation language
to a decidable fragment. Those that take full dynamism (UCAN's chains,
macaroons' unrestricted caveats, Zanzibar's live tuple store) make the authority
topology unknowable until run time.

That is the trade we already make for trust, so it generalises: **keep the
topology static and validator-checked, let the values be dynamic, restrict the
narrowing operation to something monotone.** Concretely —

- A `Scope` dimension on capability types, parallel to trust.
- One designated node kind (`binds_principal`) that may introduce or rebind a
  principal, mirroring `discharges_trust`. Every other node may only narrow.
- Narrowing restricted to **intersection over fixed dimensions** (principal,
  resource, action), IAM-style, not an open predicate language.
- An RFC 8693-shaped `{principal, acting_as}` field on trace crossings, making
  the confused-deputy claim a pinned test rather than prose.
- This argues for **named capability slots** over flat positional matching.

The cost is real and worth stating: a node cannot attenuate at a point the graph
author did not declare, and cross-cutting caveats ("valid 9am–5pm") are
inexpressible unless added as an explicit dimension.

**Also taken:** an anti-pattern to name explicitly — if a deployment needs
Zanzibar-style dynamic ACLs, the check must be a first-class capability in a
`with` clause, never called ambiently, or the authority decision moves into a
store the validator cannot see. **Landed** (Aug 2026) in §7.5, stated as a rule,
citing `pang_zanzibar_2019` as the production instance of the dynamic side —
which the paragraph previously lacked, naming only the analysable side (Cedar,
Biscuit, IAM) and so describing a trade with one end missing.

### 6. The trace is not sufficient for replay, and the reason is interesting

Every durable-execution system surveyed (Temporal, Restate, DBOS, Golem) replays
by recording **actual values per call, in call order, undeduplicated**. Ours
records `(interface, instance)` **deduplicated per node** — the right *kind* of
artifact, the wrong *granularity*.

But the dedup is not laziness: §3.5 argues it is what makes host-tier and
confined-tier traces structurally identical, pinned by a test. So two properties
are in tension — tier-comparability, which the dedup buys, and
replay-sufficiency, which it forecloses.

**Resolution:** they answer different questions for different consumers. An
auditor asks "what authority did this exercise"; a debugger asks "what actually
happened". Make the coarse layer a **derived projection** of a fine per-call
layer `(interface, instance, call_index, value)`, so tier-equality becomes a
theorem about the projection rather than two hand-maintained views staying in
sync. The fine layer must be stated as confined-tier-authoritative and
host-tier-advisory, since a hostile host-tier node can feed the wrapper fake
values as easily as it can fake a call.

**Novel constraint worth reporting:** Golem has one substrate (everything is a
component); Restate's journal is developer-demarcated steps. Neither runs the
same source unit through two structurally different runtimes and then claims
something about both. Nobody else needed this split because nobody else has our
migration story.

### 7. Fan-in — a rule, not three unranked options

Two findings combine into a design rule:

- **DBOS**'s durable `Select` does not make a race deterministic; it records
  *which branch actually won* as data, and replay injects the recorded winner.
- **Feldera/DBSP** shows that if a combinator is commutative and associative,
  arrival order genuinely does not matter and nothing needs recording.

**Rule:** classify merge combinators as order-sensitive or not. Only the former
needs a realized-order trace field. "Watermark" (Arroyo, formalised as
"frontiers" in Timely) is the standard vocabulary for the completeness question
a merge node faces; use it rather than inventing a term.

**Related correction:** differential evaluation is naive as a blanket ambition.
DBSP works because nodes are declarative operators over deltas; our nodes send
email and call LLMs, and most are not safely re-runnable on a delta without
re-triggering effects. Scope the claim to effect-free subgraphs.

### 8. Evidence for keeping the two-point lattice

**W3C Trusted Types** — shipped across all major browsers — is a two-point taint
lattice with a single discharge mechanism: a DOM sink refuses a raw string and
requires a `TrustedHTML`/`TrustedScript`/`TrustedScriptURL` produced by a
registered policy, enforced via CSP. The **Checker Framework's Tainting Checker**
is the same shape for Java, with a parameterisable lattice that in practice
nobody instantiates beyond two points.

Two shipped mainstream taint systems, both stopping at two points, is the
strongest available rebuttal to "why not graded from the start". Worth citing
*against* the graded direction, alongside Jif which argues for it.

**Flagged for a full read before the graded decision is settled:** Filament
(arXiv:2604.14357), a 2026 static IFC library for Rust with no compiler
modifications. Only the abstract was obtained; its lattice arity is unconfirmed.

### 9. A minimal contract language, sized correctly

Grounded in Racket contracts (**blame**: precondition violations blame the
caller, postcondition the callee), Clojure `spec/fdef` (`:args`/`:ret`/`:fn`,
checked both by runtime instrumentation and generatively), and
`icontract-hypothesis` (derives a property-based-test strategy *from* the
precondition).

Proposed shape: a `requires:`/`ensures:` block per node, predicates over field
paths of the node's already-typed record, reusing `scripts/type_parser.py`.
Deliberately closed vocabulary — comparisons, variant membership, field presence.
No quantifiers, no recursion, no arbitrary code. That ceiling is what keeps it a
contract rather than a refinement type. Checked two ways: a runtime guard at the
executor boundary yielding a new `contract_violation` reason class in the
existing pinning discipline, and a generative mode deriving Hypothesis
strategies, run at test time rather than on the execution path.

### 10. Smaller items taken

- **Austral** (linear types + capabilities, attenuation-from-root) contributes a
  *fourth* option to hierarchical routing — a linear split function proving the
  parent's remaining share still valid. Also a caution: Austral's "revocation" is
  lexical scope ending, checked statically. It does **not** solve revocation more
  cleanly than caretaker proxies; it solves a different, static problem.
- **ZIO `ZLayer`** supplies vocabulary for the `Layer` idea already named as
  unadopted: horizontal combine, vertical sequence, scoped release, and
  **fallback construction** (a provisioning step that fails over to a degraded
  handle) — a pattern absent from our design entirely. Its **memoized-vs-fresh**
  distinction is exactly our identity-routing question with prior art.
- **Anthropic, *How we contain Claude across products*** (McGuinness, Grace, De
  Jonghe, Eaton, Ribbink; 25 May 2026): reframes an egress allowlist as a
  *capability grant* rather than a destination filter — allowlisting
  `api.anthropic.com` also permitted file uploads to arbitrary accounts.
  Real-world evidence for the `unknown-unknown` argument. **Landed** (Aug 2026):
  cited in §7.4, and pointed at our *own* `HTTPClient<[host, ...]>`, whose
  allowlist is host-granular and therefore has the same coarseness. It argues
  against the demonstrator as much as for the framing, which is why it belongs in
  the threats section rather than beside the claim.
- **Wassette** (Microsoft, not Bytecode Alliance) runs WASM components as MCP
  tools with deny-by-default permissions granted interactively — but **decoupled
  from the WIT interface**. A precise contrast: same ingredients, not connected
  the way we connect them.
- **MCP**'s authorization is OAuth-style session consent; tool schemas describe
  *shape*, not authority. Closer to ambient authority behind one UI gate than to
  a per-node typed handle.
- **Dagster's asset-selection syntax** (`+key:"x"+`, `2+key:"x"+1`, `tag:`,
  `roots(...)`) is the most transferable inspector idea found: a textual
  selection language over the graph, used identically in UI, jobs and CLI. A
  capability/trust-flavoured analogue (`trust:"Untrusted"+1`, `crossing:"…"`,
  `tier:"host"`) is a filter over JSON we already have.
- **Marimo**'s reference highlighting answers "an error deep in a sub-graph must
  be comprehensible at the developer's altitude" — highlight the path back to the
  parent's provisioning site *in the parent's view*, without navigating away.
- **Kedro-Viz layers** suggest an orthogonal trust-band axis across the canvas.
- **Graphtage** proves optimal graph diff is NP-hard even restricted to DAGs —
  formal justification for checking *properties* via the validator rather than
  building a general graph-diff feature.

### 11. Surveyed and deliberately not taken

- **UCAN / ZCAP-LD** — full dynamic delegation is precisely what we traded away
  for static analysability. Cite as "what full dynamism looks like and why we
  don't", not as a design to adopt.
- **Zanzibar / SpiceDB / OpenFGA** — moving authority decisions into a live
  external store reintroduces the ambient-authority failure mode §3.4 exists to
  rule out.
- **OPA/Rego** — deliberately not designed for static analysability of the policy
  set, unlike Cedar. Weaker fit for a paper about static analysis.
- **SPIFFE/SPIRE** — workload identity, not end-user principal identity. Do not
  conflate; relevant only to distributed node identity, which we do not address.
- **Dafny / Lean / F\*** — right idea, wrong weight class for the contract gap.
- **E2B, Modal, Firecracker, gVisor** — general untrusted-code execution,
  orthogonal to deriving permissions from an interface. One exception worth
  citing: the AWS Bedrock AgentCore DNS-exfiltration disclosure (March 2026), a
  dated instance of coarse network isolation failing exactly as
  ambient-authority arguments predict.
- **BAML, DSPy, Pydantic AI, Instructor, Outlines, Mastra** — typed-I/O
  frameworks constrain *shape*, not *authority*. One sentence covers all of them;
  Mastra is worth a clause as closest in topology and absent in security model,
  Pydantic AI's `deps_type` as the closest DI pattern to a `with` clause.
- **Golem Cloud** as a capability system — its own materials list capability-based
  security as roadmap, not built. Cite it for durable replay, not for capabilities.
- **Gleam, Verse, Wuffs, Flix, Node-RED, Retool, Streamlit** — checked, nothing
  actionable. Wuffs is interesting as convergent evidence: it achieves no ambient
  authority by having no I/O primitives at all, which is what an empty `with`
  clause plus `wasm32-unknown-unknown` already gives us from the other direction.

---

## Open verification debts

- **Wassette's permission mechanism** — the "decoupled from WIT" claim is
  documentation-level. Verify against source before publishing it as a contrast.
- **Filament's lattice arity** — abstract only; needs a full read before the
  two-point-vs-graded decision is settled.
- **AgenticOS** (arXiv:2606.21129) — real but unreviewed; at most a defensive
  sentence.
- **Foundry's two-altitude lineage** — marketing-level sourcing only.
