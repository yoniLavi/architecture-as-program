// Document setup
#set document(
  title: "Confinement by Construction: Capability Surfaces Derived from an Architecture Model",
  author: ("Yoni Lavi"),
  date: datetime(year: 2026, month: 9, day: 30),
)
#set page(margin: 2.5cm, numbering: "1")
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true)

// ── Evaluation data ────────────────────────────────────────────────
//
// Every figure this paper states about the demonstrator is interpolated from
// dist/evaluation.json, emitted by poc/evaluate.py on each build from the same
// run that produces dist/evaluation.md. Nothing below is transcribed by hand,
// so no number here can drift from the code that produced it — and a corpus
// case that stopped being caught, or stopped being caught for its pinned
// reason, fails the build rather than quietly restating itself.
//
// This covers *magnitudes* as well as values. "Tens of microseconds" is a claim
// about a measurement exactly as "23.1µs" is, and it was the last figure here
// maintained by hand — which is how a build on a contended machine once put a
// hand-typed "tens of microseconds" beside an interpolated 343.1µs. Use
// #d.crossing_magnitude, never the phrase; the harness pins the measurement to a
// band whose ceiling is the decade boundary, so the two cannot disagree.
#let ev = json("/dist/evaluation.json")
#let d = ev.display
#let tick(ok) = if ok [#text(fill: rgb("#1a7f37"))[✓]] else [#text(fill: rgb("#b91c1c"))[✗]]
// Booleans out of the harness are facts about the run, not code literals; typeset
// them as prose so a table row reads as a finding rather than as a JSON value.
#let yesno(b) = if b [yes] else [no]

// ── Predictions and outcomes ───────────────────────────────────────
//
// The founding vision's claims and what the artifact did to each (@tab:outcomes).
// Held as data so the verdict counts quoted in the abstract, §5, and the
// conclusion are computed from the table rather than typed beside it — the same
// reason the evaluation figures are interpolated.
#let outcomes = (
  ([Unsafe wirings are rejected statically, before execution], "Substantiated", [@sec:eval-corpus]),
  ([Trust cannot be laundered by relabelling the consumer], "Substantiated", [@sec:eval-corpus]),
  ([A node cannot exceed its declared capabilities], "Partial", [@sec:eval-tiers]),
  ([Nodes have no ambient authority], "Partial", [@sec:eval-tiers]),
  ([Per-crossing overhead stays inside the stated envelope], "Substantiated", [@sec:eval-overhead]),
  ([Prompt injection is structurally attenuated], "Partial", [@sec:eval-injection]),
  ([Hierarchical composition follows from the model], "Substantiated", [@sec:subgraph]),
  ([Capability identity, revocation, and rotation are expressible], "Substantiated", [@sec:identity]),
  ([Implementations are interchangeable across languages], "Partial", [@sec:sandbox-tier]),
  ([The _declared_ capability distribution is complete and reviewable], "Substantiated", [@sec:validator]),
  ([Behavioural contracts constrain generated implementations], "Partial", [@sec:contracts]),
  ([Well-typed wiring implies noninterference], "Conditional", [—]),
  ([The full type system (graded or decentralised labels)], "Conditional", [—]),
  ([Memory-level unforgeability on CHERI hardware], "Conditional", [—]),
  ([User-level authorisation threaded through capability injection], "Not attempted", [—]),
  ([Replay and time-travel debugging from boundary logs], "Not attempted", [—]),
  ([Differential evaluation of the graph at scale], "Not attempted", [—]),
  ([Agent tooling for the graph workflow], "Not attempted", [—]),
  ([The visual graph editor], "Not attempted", [—]),
)
#let verdicts(status) = outcomes.filter(o => o.at(1) == status).len()

// Title block
#align(center)[
  #text(size: 16pt, weight: "bold")[
    Confinement by Construction: \
    Capability Surfaces Derived from an Architecture Model
  ]
]

#align(center)[
  #text(size: 12pt)[Yoni Lavi] \
  #text(size: 10pt, style: "italic")[Codeliance]
]

#align(center)[
  #text(size: 11pt)[September 2026]
]

#align(center)[
  #text(size: 9pt)[
    Preprint · #link("https://doi.org/10.5281/zenodo.23057135")[doi:10.5281/zenodo.23057135] · CC BY 4.0
  ]
]

// The note below is one line on purpose: pandoc's typst reader drops the space at a
// soft line break inside this block, and drops the block if a comment sits in it.
#align(center)[
  #block(width: 85%)[
    #set text(size: 9pt, style: "italic")
    Second paper in a corpus on architecture-as-program. The founding vision @lavi_architecture_2026 was frozen at its last state before the executable demonstrator was built, and later published without revising its predictions; this paper reports the artifact, most of it built afterwards, and accounts for the vision's predictions against it without revising them.
  ]
]

#v(1em)

#align(center)[
  #block(width: 85%, stroke: 0.5pt + luma(180), inset: 1em, radius: 3pt)[
    #set text(size: 9pt)
    #set par(justify: true)
    *Note on process.* This paper was developed collaboratively with Claude (Anthropic), which served as primary drafter under the author's direction, and the demonstrator it reports was likewise AI-implemented against author-directed specifications. The architectural vision and synthesis are the author's; the literature survey, formal framing, prose, and implementation were produced by the AI and verified against primary sources and a test suite. This transparent accounting reflects the paper's own thesis: that the interesting artifact is the _intent_, not the implementation, and that honest attribution of AI contribution is preferable to ambiguity.
  ]
]

#v(1em)

#block(width: 100%, inset: (x: 2em))[
  #set text(size: 10pt)
  #set par(justify: true)
  *Abstract.* Architecture models in mainstream use describe what a system's components may do; they do not constrain it. This paper reports a demonstrator in which the model constrains the artifact _mechanically_. The primary artifact is a _signal graph_ — a functional reactive program in which each node declares its authority as typed capability handles in a `with` clause — and a node's `with` clause determines the set of interfaces its compiled WebAssembly component may import: derived from the graph and checked against the built binary, so a world that over-grants fails the build rather than shipping. Because the components carry no WASI adapter, they import no filesystem, socket, environment, or clock function their clause does not grant, so confinement to the granted interfaces is a property of the artifact rather than of how a host happened to configure it — a distinction we found only by building the tier twice. Alongside it, a trust lattice with no upward coercion, applied uniformly to edges and node bodies, rejects trust laundering that type-checks on _every edge_, and an evaluation harness pins each rejection to the check that must produce it. A capability-boundary crossing costs #d.crossing_magnitude while marshalling typed values.

  The design was frozen at its last state before the executable demonstrator was built, and we report the artifact against its #outcomes.len() predictions without revising them: #verdicts("Substantiated") substantiated at the demonstrator's scale, #verdicts("Partial") only under restrictions the vision did not attach, #verdicts("Conditional") still conditional, and #verdicts("Not attempted") not attempted — together with three design corrections building forced, each legible as a correction only because the pre-build text survives with its predictions unamended. We are explicit about what does not follow. The mutation corpus is curated, so its counts are not a soundness result, and no noninterference proof is attempted; the host tier's escapes are recorded as passing tests rather than omitted; prompt injection is _attenuated, not eliminated_ — adversarial text survives in a permitted free-text field even on the confined tier, and what bounds the damage is the capability scope rather than the type or the sandbox; and trust is declared rather than inferred, so content a capability returns reaches the lattice unlabelled.
]

#v(1em)

= Introduction <sec:intro>

For thirty years a small research community pursued an idea working developers consistently rejected: that source code should be a structured graph, not text in files. Projectional editors @jetbrains_mps_2025, structure editors @simonyi_intentional_2006, and model-driven architecture @omg_mda_2014 foundered on one obstacle — programmers prefer text, value its flexibility for half-formed thoughts, and resist representations that constrain expression before intent is clear. That obstacle has moved. AI coding agents (Claude Code @anthropic_claude_code_2025, Codex @openai_codex_2025, Cursor @anysphere_cursor_2025, Windsurf @codeium_windsurf_2025) are a new primary author of implementation code that does not need text editing's affordances, and benefits instead from machine-readable intent: LLM generation inside the Hazel typed-hole environment improves substantially with static context from the type system @blinn_statically_2024, and spec-driven development frameworks (OpenSpec @fission_openspec_2025, Spec Kit @github_spec_kit_2025, Kiro @aws_kiro_2025) already treat structured intent, not generated code, as the artifact that matters.

Earlier work @lavi_architecture_2026 argued that these trends converge on a _signal graph_: a program in a functional reactive style in which each node is a function from typed inputs to typed outputs, all authority is held as explicitly declared capability handles, and trust is a propagating type-level annotation — so that the graph is at once the architecture model, the security policy, and the program. That paper was written before its executable demonstrator was built, frozen at that state, then published with its predictions unchanged, and stated its security claims conditionally: properties that _would_ hold in a sound realisation of a type system that did not yet exist.

This paper reports what happened when it was built. It defends one property the vision did not predict — that the model can determine the artifact's authority _mechanically_ — and then reports the artifact against every prediction the frozen vision made.

== The central claim <sec:claim>

#block(width: 100%, inset: (x: 1.5em, y: 0.6em), stroke: (left: 2pt + luma(140)))[
  A node's declared capabilities can _determine_ the authority surface of its
  compiled artifact: the set of interfaces its WebAssembly component may import
  is derived from its `with` clause in the architecture model and checked
  against the built binary, so confinement to those interfaces is a property of
  the artifact rather than of the host's configuration and an over-granting world
  fails the build.
  On the same model, a trust lattice with no upward coercion, applied uniformly
  to edges and node bodies, _rejects at assembly time_ — before any node
  executes — wirings that conventional architectures can only discourage by
  review, including the trust-laundering case that type-checks on every edge.
]

The claim does not say the system is provably secure: no soundness argument connects well-typed wiring to noninterference (@sec:threat-security). It does not say prompt injection is prevented: it is attenuated, and @sec:eval-injection reports the residual that survives on the confined tier. It does not say the corpus of caught mistakes is complete: it is curated, and its counts are evidence of implementability, not of coverage (@sec:threats). It does not say untrusted content is recognised: trust is declared, not inferred (@sec:threat-security). And it is a claim about _confinement_, not about the correctness of what a confined node computes. A reader who finishes this paper believing a stronger claim has been shown has been misled by it.

== Contributions <sec:contributions>

- *A capability surface derived from the architecture model and checked against the artifact*: each node's permitted import set is computed from its `with` clause and compared against what its built component imports, so an over-granting world fails rather than ships — and, with no WASI adapter, the absence of filesystem, socket, and environment authority, and of any clock the clause does not grant, is structural rather than configured (@sec:sandbox-tier, @sec:eval-derivation).
- *A graph validator* implementing six classes of analysis, in which trust laundering violates the _same_ no-upward-coercion order that governs edges rather than a rule bolted on beside edge typing, with one sink rule beside that order for what it cannot express: labelled untrusted data may not reach a tool-capable node, and such a node may not be declared a discharger (@sec:validator).
- *An executable runtime with two enforcement tiers* that compose in one graph — host-level object discipline, whose escapes are recorded as passing tests, and the confined tier — together with operational sub-graph composition, capability identity and revocation, a contract layer with blame, and a structured execution trace (@sec:implementation).
- *An evaluation emitted as a reproducible artifact*: the graph-to-binary derivation per node with a real over-granting binary as a negative control, corpus verdicts pinned to the reason class that must catch them, boundary overhead, and prompt-injection outcomes on both tiers (@sec:evaluation).
- *A prediction-by-prediction accounting* of the frozen vision against the artifact, under a protocol that guards the prediction against silent revision, and the three design corrections that building forced (@sec:outcomes).

@sec:design presents the design, @sec:implementation what was built, and @sec:evaluation its evaluation. @sec:outcomes accounts for the vision's predictions, @sec:related positions the work, @sec:threats states the limits, and @sec:future names what comes next.

= Design <sec:design>

This section restates the design the demonstrator implements @lavi_architecture_2026, cut to what later sections depend on. One convention is load-bearing: claims the demonstrator has substantiated are in the present tense, and claims it has not stay in the conditional mood the vision wrote them in. This section describes intent as much as artifact, so a conditional here is deliberate; @sec:outcomes says which is which.

*The signal graph is the source of truth.* The artifact humans author, review, and version is a functional reactive program: a directed graph of nodes, each a function from time-varying typed inputs to typed outputs, with every effect mediated by an explicitly declared capability handle. It is at once architecture model, security policy, and program.

*Capabilities are declared requirements.* Nodes have no ambient authority. Side effects are typed handles declared in a `with` clause: a node `(OrderRequest) → OrderConfirmation with DBHandle<'orders', read-write>, EventEmitter<'order-events'>` can read and write orders and emit order events, and nothing else. A node with no `with` clause is pure. Whether that absence of ambient authority is _enforced_, or is only an object discipline a hostile body can reach around, is a fact about the tier a node runs on — a distinction the vision did not draw (@sec:tiers).

*Code is a compiled artifact.* Agents would generate each node's body to satisfy the contracts in its signature, and the body could be regenerated without changing the system's meaning, up to what those contracts can say (@sec:open). This is the one property the demonstrator does not exercise at any useful scale: `ParseMessage`'s body was generated from its signature and a prose contract in its prompt, in Python and in Rust, with the prompts committed, and every other body was written in the ordinary directed loop with sight of the whole repository (@sec:future).

*Security by construction.* Because capabilities are injected and trust propagates in types, security properties are intended to be structural invariants of the graph rather than aspirations enforced by code review. Their strength varies sharply by vulnerability class, and @sec:security names each.

== Functional reactive programming, extended <sec:frp>

The model applies _functional reactive programming_ (FRP) as a whole-system substrate. FRP began with Elliott and Hudak @elliott_functional_1997; _arrowized_ FRP @nilsson_functional_2002, building on Hughes's arrows @hughes_generalising_2000, made the _signal function_ `SF a b` the composable unit with its interface explicit in the type — the formal object extended here. Its realisations range from Elm @czaplicki_elm_2012 to Cycle.js @cyclejs_2025, whose driver discipline is close to capability injection, alongside the synchronous dataflow languages (Lustre @halbwachs_synchronous_1991, Esterel @berry_esterel_1992) and, at commercial scale, LabVIEW @ni_labview_2025 and Simulink @mathworks_simulink_2025. Two extensions turn it into an architectural model. _Capability annotation_ gives effects the fine-grained type structure of the object-capability model @miller_robust_2006, in which possession of an unforgeable typed reference is the proof of authorisation. _Trust tainting_ marks data from untrusted sources — user input, third-party responses, model output — with a type that propagates until an explicitly designated node discharges it, as in taint tracking @sabelfeld_language-based_2003 and labelled IO @stefan_flexible_2011, but expressed as ordinary type-level propagation rather than a separate analysis. In the artifact the marking is declared, not inferred: data is untrusted where a node's output type says so, and what a handle returns is not labelled for it (@sec:threat-security).

== The signal graph <sec:signal-graph>

*Nodes* have two-part signatures: _data inputs_, typed signals from upstream, and _capability requirements_, declared with `with`. Data flows at invocation; capabilities bind when the graph is instantiated. The separation is syntactic on purpose, although capabilities are values in the object-capability sense, because what a node transforms and what authority it holds are different review concerns.

*Edges* are typed data connections, valid only if the types match. Capabilities are not wired through edges: E-lineage systems permit delegation by passing references in messages, which defeats static analysis of the authority topology, and the signal graph trades that flexibility for a fully analysable capability distribution. The `with` clauses together are the security policy, as reviewable graph structure, and a `with` clause names a type rather than an instance, so a live `DBHandle` becomes a test fixture by a change at the graph boundary alone.

*Trust annotations* propagate: `Untrusted<T>` is preserved until discharged, and in a well-typed realisation could not reach a node that accepts only `T`. Discharge is most effective as a _type transformation_ — unstructured input converted to a constrained representation — rather than a label removal. Local typing is not enough: the wiring must be checked too, which is the standard coercion problem of information-flow type systems #cite(<sabelfeld_language-based_2003>, supplement: [§3]) — `Untrusted<T>` must not be a subtype of `T`. The demonstrator implements a first realisation, a lattice with no upward coercion (@sec:validator); the choice among richer lattices, and a soundness argument that well-typed wiring implies noninterference, are open (@sec:open).

*Behavioural contracts* are pre- and postconditions on signatures: the specification a generated body would be verified against, and the interface across which bodies are interchangeable. The demonstrator implements a deliberately small instance, checked with blame (@sec:contracts); the contract language the model ultimately wants — refinement types, Dafny-style specifications, or QuickCheck-style properties — is undesigned (@sec:open).

== A concrete graph <sec:concrete-graph>

The running example is an AI customer-support agent, chosen because every property under test is visible in it: untrusted user input, LLM invocations with and without tool access, and fine-grained capability distinctions. Types are angle-bracketed; capability types are parameterised by scope, so `DBHandle<'knowledge-base', read>` is a handle to that database in `read` mode, where `read`, `append`, and `read-write` are modes in a permission lattice. `LLMClient<inference>` grants model access without tool-calling, and `LLMClient<[lookup]>` one named tool. Sum types carry role labels, and an edge addresses a variant as `Node.role`. No concrete syntax is claimed; the value is the structural shape.

#raw(read("/dist/graphs/customer-support.graph"), block: true)

The parameter list is the system's authority manifest. Because the graph has a typed signature, it is itself a node in a larger one: in `SupportPlatform` (@fig:support-platform), `CustomerSupport` is a single node beside `AgentDashboard` and `BillingService`, its #ev.graphs.customer_support_nodes nodes and trust zones encapsulated, so that `BillingService` holding read-write billing access and no LLM capability is legible at that altitude without opening it. `CustomerSupport` and `BillingService` both require `ResponseChannel<user-session>`, and the platform binds each a distinct named instance, so identity crosses the composition boundary rather than being aliased by type (@sec:identity). Two composition questions stay open: how a sub-graph routes a provisioned capability to exactly the nodes that need it, and how several terminal types collapse into one boundary type — spelled here as the union `DeliveryConfirmation | EscalationTicket`, since the language has no alias mechanism (@sec:subgraph, @sec:open).

#figure(
  image("/dist/graphs/support-platform.svg", width: 75%),
  caption: [The SupportPlatform composition graph. Each service node is a sub-graph by design; only CustomerSupport is defined and run as one (the #(ev.graphs.customer_support_nodes)-node graph here a single node). Where a service holds a distinct named instance of a capability type, the identity label is shown after `@`. The audit node collects outcomes from all services with append-only database access.],
) <fig:support-platform>

#figure(
  image("/dist/graphs/customer-support.svg", width: 85%),
  caption: [The CustomerSupport signal graph. Red shading marks the untrusted zone; green shading marks the structured region. LLM access (blue) is graduated: inference-only for parsing and moderation, a single lookup tool for response generation.],
) <fig:customer-support>

Three properties are visible in the diagram without reading implementation code, and they are what @sec:evaluation puts under test.

_Prompt injection is addressed through structural typing and topological constraint._ `ParseMessage` does not merely strip the `Untrusted` wrapper: it transforms the message into a classified intent from a finite set, extracted entity references, and bounded text fields, and the raw message is consumed. `ModerateContent` refines that into a distinct `ModeratedQuery`, so a wiring that bypasses moderation is ill-typed. The LLM is itself the discharging component, bounded by its capability shape and by the schema of what it emits. The tool-capable `GenerateResponse` receives only `ConversationContext` assembled downstream of moderation, so no direct path from untrusted input to a tool-capable LLM exists in the graph; in a sound realisation it would be ill-typed, and the validator's sink rule already rejects one for labelled data (@sec:validator). Two limits attach. Capability restriction stops the LLM _acting_ on adversarial instructions but not being _influenced_ in its classification, so a crafted message can cause a misroute, and bounding that further depends on user-scoped capabilities, which the artifact neither binds nor types: a run records the principal it acts for, but no handle is scoped to it (@sec:identity, @sec:open). And the schema guarantee holds only _provided the schema excludes free text in positions flowing to privileged nodes_ — most schemas keep such a field, for the question itself, and @sec:eval-injection measures exactly that residual.

_Capability distribution is minimal and visible._ `ReceiveMessage` is pure; `ParseMessage` and `ModerateContent` hold inference-only LLM access; `FetchContext` read-only knowledge-base access; `GenerateResponse` one lookup tool plus that handle; the three reply terminals a session-scoped response channel; `EscalateToHuman` may emit to the support queue but touches no database. A new requirement appears in a diff as a new `with` clause.

_Conditional routing is explicit._ `ModerateContent` emits a three-way union routed to the response pipeline, to user notification, and to human escalation. The validator enforces that every variant has a consumer, but cannot force a body to emit the _correct_ one — a `ModerateContent` that always emits `.ok` is well-typed and wrong, an obligation outside the contract vocabulary of @sec:contracts.

== Security properties <sec:security>

The capability-injection model is intended to provide guarantees qualitatively different from those achievable by code review or runtime monitoring. Their strength varies by vulnerability class, and the variation is the point.

*Injection attacks.* SQL and command injection depend on untrusted input reaching an interpreter in executable form. A SQL-executing capability would accept typed queries, not raw strings, so `Untrusted<string>` could not reach it without transiting a sanitisation node that produces a typed query. In a sound realisation the pattern would be ill-typed.

*Privilege escalation.* A node would not acquire capabilities it was not given, the graph being the complete and sole description of the capability distribution, and would extend to the memory level on CHERI hardware — on which nothing here has run (@sec:effects). Three things bound this. Two are caveats about the design: a node holding a network capability can in principle acquire authority out-of-band from services the graph does not model, a distributed-authority problem this work inherits rather than addresses; and for user-scoped operations the guarantee is only as strong as a principal binding that the artifact records per run but attaches to no capability instance and no type (@sec:identity). The third is a measured fact about the artifact — the property holds on the confined tier and only as an object discipline on the host tier, where an ungranted capability is reachable and the escape is recorded as a passing test (@sec:eval-tiers).

*Supply chain attacks.* The defence is _capability scoping_, not I/O denial: a malicious library inherits only the scope of the node it inhabits, so the blast radius is that scope rather than the library's creativity. This holds as a property of the artifact on the confined tier and only as an object discipline a hostile library can reach around on the host tier (@sec:eval-tiers). A new capability requirement surfaces in the graph diff as a new `with` clause.

*Prompt injection and confused deputies.* Structurally attenuated, not eliminated. No well-typed wiring would connect an untrusted source to a tool-capable LLM without transiting a type that constrains the downstream payload, but a free-text field reaching an LLM-capable node stays adversarial even when its wrapper is non-`Untrusted`, and an untrusted source is one declared so, since content a handle returns is not labelled (@sec:threat-security); strength depends on schema discipline, and @sec:eval-injection measures the residual. The confused-deputy case adds a second mechanism, capabilities bound at the graph boundary to the calling user's credentials, which @sec:identity does not yet do: it records and propagates the principal but binds no handle to it, and does not type it (@sec:open).

*Covert channels remain an open concern.* A node granted a permitted capability can encode information into the timing, query shape, or ordering of its legitimate outputs — channels the type system does not model, and which general covert-channel elimination, a known-hard problem, is not claimed to close (@sec:threat-security).

= Implementation <sec:implementation>

The demonstrator implements the graph-level analyses and the capability-injected runtime of @sec:design. It is *not* the language the vision called for: it has no noninterference proof, no dependent types, and no visual editor, and its contracts are checked rather than verified. What it implements is the part whose implementability was least obvious — that a graph carrying capability and trust annotations can be statically analysed to reject unsafe wirings, and that node bodies can be confined to exactly the authority their signatures declare. Everything in this section is built and tested, and where a property is asserted by a test, that is said.

The graph definitions in `graphs/*.json` are the single source of truth, validated against a JSON Schema. The listing and diagrams of @sec:concrete-graph are generated from them, so the graphs shown are the graphs run, and the documented type grammar is emitted from the parser rather than maintained by hand.

== The validator: six graph-level analyses <sec:validator>

A dependency-free validator runs six classes of analysis over the canonical graphs.

/ Edge type-compatibility: source output types, with sum-variant resolution, must match target input types in data shape, independently of trust.
/ Trust-lattice checking: trust forms a two-point lattice ordered by trustworthiness, `Untrusted ⊑ Trusted` (the reverse of the flows-to order of integrity labels), along which a value may be used at its own level or lower but never raised: no upward coercion. This is checked on every edge and every node body, per variant of a sum and through type constructors, since one variant marked untrusted does not license a clean sibling. Only a node declared `discharges_trust`, as `ParseMessage` is, may raise trust. A node holding a tool-scoped `LLMClient<[...]>` may neither consume `Untrusted<_>` nor be declared a discharger itself: the lattice alone constrains *raising* trust, and this sink rule is what keeps labelled untrusted data off a tool-capable node.
/ Variant completeness: every declared sum-type output variant has a consuming edge on its own port — the runtime routes a variant by its role, so a whole-output edge would never carry it, and a sum is labelled throughout or not at all — so dead branches are visible in the graph, and the runtime refuses a value no edge carries.
/ Capability narrowing: at composition a parent may provide wider authority than a sub-graph declares — a larger tool set, `read-write` where `read` is required, or an `HTTPClient<[...]>` host allowlist that is a superset, narrowing by set inclusion — while strict equality governs every data-flow position. Narrowing is checked, not enforced: the parent's handle is routed to the child unattenuated (@sec:open), so a tool-scoped client may not be routed into an inference-only slot, where the sink rule would not see it.
/ Intra-graph consistency: every declared capability is used, every boundary input consumed, every edge references a valid node and variant, and no capability type appears in a data position, so a handle cannot be passed along an edge; the data edges form an acyclic graph with no edge repeated.
/ Cross-graph signature matching: a node whose name matches another graph must satisfy that graph's parameter list position by position, and its declared boundary output must equal the union of that graph's terminal outputs, with no role labels, since a boundary value is a terminal's output, never a variant.

The runtime runs all six at assembly, over the graph and every canonical graph it reaches as a sub-graph, and again before running a sub-graph a caller supplied; a graph cannot contain a node of its own name, and graph names must be unique.

The second analysis changed under implementation, and the change is a result. Trust is not a rule beside edge typing; it is the same no-upward-coercion order applied in two places. The blunt unsafe wiring — untrusted input run straight into the tool-capable node — fails as an ordinary data-shape mismatch. The subtle one survives that check: widen the tool-capable node's declared input to `Untrusted<RawMessage>` and every edge type-checks on data shape. The graph is still rejected, because the node now emits a non-`Untrusted` output from an `Untrusted<_>` input without being a declared discharger — an upward coercion. The same graph also breaks the sink rule, since the node consumes `Untrusted<_>`; the harness pins the lattice's own error, so the sink rule cannot mask a lattice that stopped firing. A design that folded trust into subtyping, admitting `Untrusted<T> <: T`, would have accepted it, with the failure invisible at the level of edge types. What the validator does *not* establish is soundness: that every graph well-typed under this lattice satisfies noninterference (@sec:open).

== Two enforcement tiers <sec:tiers>

The runtime loads the same graph JSON, instantiates each node with injected capability handles, and propagates signals along the active path. Each node runs on one of two tiers, and the runtime reports which.

The *host tier* is object discipline, not containment: each node receives only its declared handles, each exposing only the operations its type permits (unless composition routes it a wider one), but nothing stops a hostile Python node from importing `os`. The escapes are performed in plain Python in the runtime's own process, which is where a host-tier body runs — a filesystem, socket, and environment read, and a handle minted that no clause granted — and they *succeed*: the gap recorded as a passing test, the one form in which it cannot be forgotten (@sec:eval-tiers).

=== The confined tier <sec:sandbox-tier>

The confined tier closes that gap for the nodes ported to it. Node bodies are compiled to WebAssembly *components* (@sec:sandboxing) — Rust, via `wit-bindgen`, to `wasm32-unknown-unknown`, converted with `wasm-tools` — and run under `wasmtime`. Each capability kind is a typed WIT interface: `LLMClient<inference>` offers a single inference function, `DBHandle<'knowledge-base', read>` a `lookup` and no writer. A node's `with` clause is then precisely the set of interfaces its component imports, beside the function-free type vocabulary, and a component declaring a capability it was not granted cannot be instantiated at all — the refusal lands before any guest code runs. The derivation that holds each binary to its clause runs at build, over the canonical graphs and one that does not ship (@tab:derivation); at run time the host links each ported node's fixed interface set. Two properties follow from the boundary being typed, and both are asserted by tests.

*There is no ambient authority to reach for, as a property of the artifact rather than of the host's configuration.* An earlier iteration compiled nodes to `wasm32-wasip1` modules under an empty WASI context. That confined them, but the modules still *imported* `environ_get`, `fd_write`, and `path_open`: present and merely powerless, so confinement was a fact about how the host had configured the runtime, and a misconfigured host would silently have granted them. Built for `wasm32-unknown-unknown` with no WASI adapter, no filesystem, socket, or environment function, and no clock the clause does not grant, appears among the imports at all; the ambient-escape hostile component imports only the function-free type vocabulary. A `wasip2` build would reintroduce the problem through `wasi:cli/*`, which is why the tier targets a bare component.

*The boundary cannot silently drift from the node's declared signature.* Because imports are typed interfaces rather than opaque symbols, the import set each component is held to is *derived from the graph*: each node's expected interfaces are computed from its `with` clause and compared against what the built component imports, so a world granting an unrequested interface fails rather than shipping. The absence is per-node, not tier-wide, and a deliberately granted clock is the sharpest test of it. The vocabulary extends to #ev.tiers.capability_kinds kinds, among them some that no shipped graph holds yet (@tab:derivation): `Clock`, `Notifier<'channel'>`, and `HTTPClient<[host, ...]>`, whose allowlist lives in the handle behind the interface so that the node holds the _operation_ while the host holds the _scope_. `Clock` is granted as the upstream `wasi:clocks/wall-clock` interface directly: a component built to hold only a clock imports exactly #ev.tiers.clock_node_imports.map(i => raw(i)).join([, ]) beside the function-free type vocabulary, with #ev.tiers.clock_node_ambient_imports ambient imports, because the boundary between capability and ambient authority is the `with` clause, not the package namespace. Each new kind cost the derivation one mapping entry and no special case.

Typing also absorbed node-body checks into types: an intent label that `ParseMessage` once had to check against its permitted set is a WIT `enum`, so widening it is unrepresentable, and a malformed model reply, a WIT `variant`, has no encoding.

On the demonstrated customer path, #ev.injection.confined_count of its #ev.injection.path_length nodes run as components, every node on it but the pure `ReceiveMessage`, while the platform around them runs on the host tier, so the tiers compose within one graph — the incremental-migration path. The confined set spans the capability boundary, not only pure transformations: `FetchContext` holds a read-only knowledge-base handle, `GenerateResponse` a scoped tool set plus that handle, and `SendReply` an identity-routed send that lands on exactly the channel instance the parent routed. Each runs a Rust body written against the same signature as its Python counterpart with the graph unchanged, and a test holds both tiers to the same path — interchangeability across languages, bounded by that test, since no canonical node carries a checked contract (@sec:contracts). Enforcement is unforgeable at the WASM boundary, not at the memory level; a runtime defect is out of scope, and nothing here touches the free-text residual (@sec:eval-injection).

== Also built <sec:also-built>

Four further mechanisms are built and tested. Each is reported with the limit it carries.

=== Capability identity, revocation, and scoped lifetime <sec:identity>

Revoking a *specific* handle first requires a way to *name* one, and the runtime's default shares one handle per capability *type* across every node declaring it. A node may therefore carry a `capability_identities` map in the graph source, binding a declared type to an identity label; the validator checks it and the diagrams render it. On that prerequisite, revocation and rotation are one mechanism: a revocable instance is wrapped in a caretaker @miller_robust_2006 whose revoke authority stays with the host that assembled the graph, and rotation re-points the same proxy at a same-kind replacement. Both are targeted and opt-in, and revocation reaches the confined tier, where a severed caretaker fails the guest's next crossing unforgeably; on the host tier it binds the handle but not a node that reaches around the object model. Rotation checks that the replacement is the same kind of handle, not that its scope matches the declared type, so a rotation can widen it; it reaches the confined tier through the same caretaker, untested there; the graph-transformation form of both operations is undesigned. An assembly used as a scope severs every revocable instance it provisioned on exit, on the failure path too — but only those: an instance provisioned bare has no caretaker and survives, a limit pinned by a test, since a caretaker on every instance would put a proxy on every crossing.

Identity also gives the *principal* a place to live. A run may bind the authenticated party it acts for, and a node declaring `binds_principal` — mirroring `discharges_trust` — is the sole point licensed to extend the chain of parties acting on its behalf, recorded per node in the delegation shape of #cite(<rfc8693>). The chain grows only at declared binders, and a sub-graph acts for whoever its parent acts for. The principal is recorded, not enforced: no handle is scoped to it and no authority decision consults it, so two runs for different principals exercise identical instances. Nor is it in the type grammar, so the validator cannot say statically which principals a node could ever act as, and a node cannot attenuate the principal it was given (@sec:open).

=== Operational composition <sec:subgraph>

A node whose name resolves to another graph executes by nested assembly and execution, so composition adds no second execution model, and `SupportPlatform` runs: a request crosses `RouteRequest` into the `CustomerSupport` graph and its outcome back out to an append-only `RecordAudit`. Four properties are tested. *A sub-graph cannot provision authority of its own*: the executor holds no backend to provision from, so the child receives exactly the handles the parent routed — confinement across the boundary follows from the plumbing, not from a rule (on the host tier, only as far as a body keeps to the object model), though a wider handle the validator accepted as narrowing reaches the child whole (@sec:open). *Identity routing has an executable consequence*: the reply node inside the sub-graph sends on the `customer_session` instance the platform routed, and its sibling's is untouched. The parent matches the child's parameter list *by position*. And composition *crosses tiers*: severing a routed instance at the parent makes the confined crossing fail two altitudes down. The boundary output check is structural rather than nominal — a node claiming only `DeliveryConfirmation`, hiding the escalation path, is rejected with every edge still type-checking. The demonstration is bounded: only leaves on the taken path have bodies, and a run reaching several terminals, or any node twice, is refused rather than resolved.

=== Behavioural contracts, at a deliberately small size <sec:contracts>

Nodes may carry pre- and postconditions over a closed vocabulary — comparison against a literal, variant membership, field presence, and `len` — with no quantifiers, recursion, or escape into the host language. That ceiling keeps the checker dependency-free and a precondition enumerable enough to derive a property-based test from (a generative mode designed but unbuilt, @sec:open). Contracts assign *blame* as in Design by Contract @meyer_applying_1992, the discipline Racket's contracts carry to higher-order values @findler_contracts_2002: a failed precondition indicts the wiring and a failed postcondition the body. Field paths are not resolved before a run, so a precondition naming a field the input lacks is simply false, and blamed on the wiring — a narrower form of the ambiguity the ceiling exists to avoid. A contract outside the vocabulary is rejected before anything runs, pinned as its own corpus case (@sec:eval-corpus), because a predicate that quietly evaluated to false would make every _satisfied_ contract ambiguous. Nothing is verified: contracts are checked on the values a run produces, not proved over all inputs, and a postcondition relating output length to input length is inexpressible without a solver. No canonical graph attaches a contract yet: the tests attach them to `ParseMessage`, whose body was generated (@sec:design), and blame a violated postcondition on it.

=== The execution trace <sec:trace>

Every run emits a structured trace, pinned by a committed JSON Schema and deterministic: per node, its tier, input and output trust labels, and its capability use in two layers. A per-call journal records each access to a capability handle — interface, instance, the operation reached, and sequence index — which on the confined tier is the host adapter's access in serving a crossing, not the WIT call itself (a `tool-llm` crossing journals as two); the per-node set of distinct `(interface, instance)` crossings is *computed from* it. That projection is the one representation both tiers produce identically — the confined component loops where the host calls once — so a test asserts the two tiers' projections structurally equal, with the journal, which ought to differ, excluded. On the confined tier a body cannot forge or suppress an entry; on the host tier the trace is as circumventable as everything else there. The harness pins two trace properties into the build: trust is raised only at the declared discharge node (#raw(ev.trace.discharge_node)), and adversarial text reaches the tool-capable node (#raw(ev.trace.tool_capable_node)) in a permitted field, its input labelled trusted, even on the confined tier. The journal records the ordering and multiplicity of handle accesses but not values, so it is the right kind of artifact at the wrong granularity for replay, which systems such as Golem @golem_cloud_2026 perform by journalling values. A web inspector renders the canonical graphs and overlays the trace of a run (@fig:inspector); it views and runs graphs but cannot author them, so it is not the visual editor the vision predicted.

#figure(
  image("/dist/ui/inspector-walkthrough-taint.png", width: 100%),
  caption: [The inspector rendering a confined-tier run of the canonical graph. The `Untrusted` value's path is distinguished up to the declared discharge node and nowhere after; per-node badges report the recorded tier and trust labels. Generated by the end-to-end suite, not composed by hand.],
) <fig:inspector>

= Evaluation <sec:evaluation>

The evaluation asks five questions: whether each compiled component imports what its `with` clause grants and nothing else; which faulty graphs the analyses reject, and by which analysis; what a boundary crossing costs; what an adversarial message can reach inside the graph; and what each tier stops.

*Method and scope.* Every figure is interpolated from a build artifact emitted by one run of an evaluation harness, which imports the corpus, benchmark, and injection scenario rather than re-deriving them. The harness is a regression guard, not a report: each corpus case pins its verdict *and the reason class that must catch it*, so trust laundering could not silently start being caught as an ordinary type mismatch, and an unpinned new case is an error. The corpus is *curated and illustrative*: its counts show the analyses are implementable and catch what they target, not that they are sound or complete (@sec:threat-construct). Timings come from one machine — #raw(ev.environment.platform) (#raw(ev.environment.processor)), Python #raw(ev.environment.python), wasmtime #raw(ev.environment.wasmtime) — and establish an order of magnitude.

== The capability surface, derived and checked <sec:eval-derivation>

For each node ported to the confined tier, the permitted interface set is computed from its `with` clause, parsed by the validator's own type parser, and compared against what its built component imports.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, left, right, center),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*node*], [*component*], [*capabilities granted*], [*binary matches*]),
    ..ev.derivation.nodes.map(n => (
      [#raw(n.node)#if not n.shipped [#super[†]]],
      raw(n.component),
      str(n.granted_count),
      tick(n.agrees),
    )).flatten()
  ),
  caption: [The `with` clause held against the compiled artifact. Counts exclude the shared type vocabulary every component links against, which grants no authority and is compared like the rest. † marks a row whose graph does not ship, included to put the I/O kinds of @sec:sandbox-tier through the same derivation.],
) <tab:derivation>

#ev.derivation.agreeing of #ev.derivation.total components import exactly what the graph grants them, across #ev.derivation.grants_compared capability grants. Divergence in *either* direction fails the build: an extra import is the over-grant the claim is about, and a missing one means the derivation has drifted from the artifact. Since no disagreeing row can reach the table, the harness also holds a real over-granting binary to a node's clause through the same code path: #ev.derivation.controls.map(c => [#raw(c.component), compiled with #raw(c.node)'s signature, is caught importing #c.over_granted.map(raw).join([, ]) beyond what that node's clause grants]).join([; ]) — pinned to be caught for exactly that interface, so a gate that stopped firing would fail the build. `GenerateResponse` carries the most weight: the tool-capable node, where an over-grant would matter and where the distinction between an inference client and a scoped tool client becomes an import-table fact.

The reading is narrow. The import table fixes each grant's *kind*; its scope — which store, hosts, or session — lives in the host-side handle, and the derivation does not see it. The comparison has been *exercised* on #ev.derivation.kinds_covered_count of the #ev.tiers.capability_kinds kinds the tier models, #ev.derivation.kinds_covered_shipped_count of them by the shipped graph's nodes; #ev.derivation.kinds_unexercised.map(k => raw(k)).join([, ], last: [ and ]) #if ev.derivation.kinds_unexercised.len() == 1 [is] else [are] mapped but held by no ported node, so nothing here checks it. The table shows that the derivation is implementable, covers every ported node rather than a chosen example, and took each new kind without a special case — on a hand-curated vocabulary in one repository, through a mapping a wrong entry would silently corrupt (@sec:threat-construct). It is not evidence that the derivation generalises to capability kinds nobody has written a mapping for.

== Graph-mutation corpus <sec:eval-corpus>

Each case is a graph the validator accepts or rejects at assembly time, before any node executes. The canonical graphs are cases in their own right: a validator that rejected everything would catch every unsafe wiring and be worthless.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, left, left, left, center),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*case*], [*kind*], [*verdict*], [*caught by*], []),
    ..ev.corpus.cases.map(c => (
      raw(c.name),
      c.kind,
      c.actual,
      if c.reason == none { [—] } else { c.reason },
      tick(c.ok),
    )).flatten()
  ),
  caption: [The graph-mutation corpus. Each faulty case is pinned to the analysis that must catch it, not merely to the fact of rejection. Every faulty case but `unevaluatable_contract` is an unsafe wiring; that one is a specification the checker refuses.],
) <tab:corpus>

#ev.corpus.canonical_accepted/#ev.corpus.canonical_total safe graphs were accepted and #ev.corpus.mutation_rejected/#ev.corpus.mutation_total faulty ones rejected, each by its pinned reason class.

`bypass_pipeline` and `launder_trust` separate a blunt mistake from a subtle one. The first wires untrusted input straight into the tool-capable node and fails on data shape, as any structural checker would. The second *repairs* that mismatch by widening the node's declared input, after which every edge is data-compatible, and is rejected by the trust lattice as an upward coercion — the property the pin enforces. The next #ev.corpus.found_by_review cases each passed the validator until an adversarial review of this paper found them, and the checks were changed to catch them (@sec:threat-construct). `launder_trust_via_variant` hides the laundering behind a sum, one variant untrusted and one clean; each variant is now checked on its own port. `launder_trust_by_declaration` declares the tool-capable consumer a discharger, and `untrusted_into_tool_node` keeps every output untrusted so no node raises trust; the sink rule of @sec:validator catches both. `delegate_via_edge` passes a handle along an edge, caught as a capability in a data position. `route_tool_into_inference_slot` routes a tool client into an inference-only slot the sink rule would not see; the cross-graph check refuses it. `launder_via_duplicate_role` gives two variants one role, so the edge check saw only the clean one; the type parser now rejects a repeated role. And `hide_branch_behind_whole_edge` consumes a labelled sum on an unported edge the runtime never fires, silently swallowing a policy violation; variant completeness now rejects it. `hide_branch_behind_unlabelled_variant` swallows it by dropping the variant's role instead, and the parser now rejects a partly labelled sum. `mislabel_subgraph_output` is the composition analogue: a sub-graph node declares a boundary output narrower than its terminals emit, hiding the escalation path while every edge type-checks, and is caught by the output-side cross-graph check (@sec:subgraph). `unevaluatable_contract` is a specification outside the closed vocabulary (@sec:contracts). Together they establish that the distinction between "type-checks" and "is well-trusted" is real and load-bearing on a graph that would otherwise pass. They do not establish that no further kind of mistake exists.

== Capability-boundary overhead <sec:eval-overhead>

The vision asserted an envelope with no measurement behind it: if a node does about #d.envelope_node_work_ms ms of useful work, a crossing below roughly #d.envelope_crossing_ms ms keeps overhead under about #d.envelope_max_overhead.

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, left),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*measurement*], [*value*], [*notes*]),
    [component compilation], [#d.compilation_ms ms], [one-time per artifact, cached; not paid per call],
    [instantiation (per node)], [#d.instantiation_ms ms], [the tier's fixed per-node price; pooling would amortise it],
    [`ParseMessage` run (warm)], [#d.parse_invocation_ms ms], [#ev.overhead.parse_crossings crossing],
    [`GenerateResponse` run (warm)], [#d.generate_invocation_ms ms], [#ev.overhead.generate_crossings crossings],
    [*marginal per-crossing*], [*#d.crossing_us µs*], [differenced between two warm paths through one component],
  ),
  caption: [Capability-boundary overhead on the confined tier. Every crossing lifts and lowers typed WIT values.],
) <tab:overhead>

A crossing costs #d.crossing_us µs — #if ev.overhead.within_envelope [within] else [*outside*] the #d.envelope_crossing_ms ms envelope, so a single crossing is #d.projected_overhead of a node doing #d.envelope_node_work_ms ms of work — even though crossings lift and lower typed variants, records, and lists rather than the packed `(ptr, len)` bytes of the tier's first implementation. No like-for-like measurement of that flat-ABI tier exists — its earlier, unpublished figures came from a cold-pass timing loop, since corrected to warm and take the best of several rounds, that could distort a differenced cost by an order of magnitude — so the figures say nothing about what typing the boundary cost, only that the typed crossing sits inside the envelope. The figures come from a Python host and a two-node slice; they locate the fixed cost in instantiation and say nothing about complex-type serialisation or graphs of hundreds of nodes.

== Prompt-injection attenuation <sec:eval-injection>

An adversarial message instructing the model to call an `exfiltrate` tool is driven through `CustomerSupport`. What matters is not whether the model is fooled — assume it is — but what it can *reach* once fooled. The message traverses #ev.injection.path.len() nodes: #ev.injection.path.map(n => raw(n)).join([ → ]), of which #ev.injection.tiers.values().filter(t => t == "sandbox").len() run on the confined tier.

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, left, center),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*property*], [*result*], []),
    [the tool-capable node received], raw(ev.injection.received_type), tick(not ev.injection.is_untrusted),
    [it received an `Untrusted<_>` value], yesno(ev.injection.is_untrusted), tick(not ev.injection.is_untrusted),
    [a fooled model's out-of-scope call took the error branch], yesno(ev.injection.out_of_scope_call_refused), tick(ev.injection.out_of_scope_call_refused),
    [adversarial text still present in a permitted field], yesno(ev.injection.adversarial_text_present), [—],
  ),
  caption: [Prompt-injection outcome. The last row is the residual, and it is asserted on the *confined* tier deliberately.],
) <tab:injection>

*The residual, stated plainly.* The `Untrusted<RawMessage>` value is consumed at the parse boundary, and the tool-capable node receives a #raw(ev.injection.received_type) instead. But the question itself remains a free-text field, and that field stays adversarial. The guarantee is therefore *attenuation, not elimination*: the model can still be influenced by the text; it cannot call anything outside `{lookup}`. A second run whose model demands `exfiltrate` shows it: the tool-capable node takes its `error` branch, on the host tier because the handle refuses; on the confined tier the body reports the request, which it could not have acted on, since its component imports no interface for any tool but `lookup`. Blast radius drops from arbitrary tool execution to a bad lookup query. The confined tier does *not* close this residual — what bounds the damage is the capability scope, not the sandbox — which is why it is asserted on that tier, so that stronger enforcement is not misread as a stronger claim. And the attenuation depends on schema discipline: a discharging type that keeps free text in a position flowing to a privileged node — even length-bounded, as the question is — gives most of it back.

== Enforcement tiers: what each one stops <sec:eval-tiers>

The same classes of escape were attempted on both tiers: on the host tier in plain Python in the runtime's process, where a host-tier body runs, and on the confined tier by hostile components, each denial pinned to its discriminating error — an operation the guest reports unsupported for any target, since no host function backs it, and an environment variable it reports absent while the harness has set it. The host-tier column is *expected* to read ESCAPES; that gap is why the confined tier exists.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, center, center, center),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*escape attempt*], [*host tier*], [*confined tier*], []),
    ..ev.tiers.escapes.map(e => (
      e.probe,
      if e.host_escapes { [ESCAPES] } else { [—] },
      if e.sandbox_escapes { [*ESCAPED*] } else { [denied] },
      tick(not e.sandbox_escapes),
    )).flatten()
  ),
  caption: [Escape attempts on both tiers. The host tier's failures are the recorded gap, not an omission.],
) <tab:tiers>

The ungranted-capability row is the sharpest: the component imports an interface it was never granted, so it cannot instantiate at all. On the confined tier a capability is *absent, not merely unexposed*: an inference-only node imports only #ev.tiers.inference_node_imports.map(i => raw(i)).join([, ]) beside the function-free type vocabulary, with #ev.tiers.ambient_imports filesystem, socket, environment, or clock imports. The clock and HTTP rows are each other's dual. A hostile body granted _only_ a clock still cannot open a socket or read a file — the grant bought the authority it names and reopened nothing ambient — and a node with an allowlisted HTTP capability is refused at the crossing when it asks for an off-list host, the shape of an out-of-scope tool call. The row's two cells measure different things: the host cell mints a handle for the off-list host (against a stub; the PoC performs no network I/O), and the confined cell is a granted handle refusing that host, a refusal identical on either tier. That a confined body cannot mint a handle follows from no interface constructing one; the row does not probe it.


= Predictions and outcomes <sec:outcomes>

The vision's frozen text @lavi_architecture_2026 predates the runtime and tiers of @sec:implementation, though an early form of the validator of @sec:validator already ran; @sec:design restates it with the corrections building forced. This section reports what the artifact did to each of its predictions.

== The protocol <sec:protocol>

Architecture papers almost always describe systems that already exist, so a reader cannot separate predictions from rationalisations — and an author's memory of what they expected is no better. Adjacent fields answer this with pre-registration. An architecture vision is not a hypothesis with an analysis plan, but it can be reduced to a *document* frozen in time, and the protocol followed here does that in five steps. *Freeze* the vision at a state that precedes building: the vision @lavi_architecture_2026 was fixed at the last repository state with no executable demonstrator — a point designated after building had begun, and checkable in version control — when a stdlib validator for early forms of the analyses of @sec:validator already existed. *Publish* it under a DOI, so a third party holds a copy the author cannot alter. *Guard* the freeze in the ordinary build: a check fails it if the frozen sources drift from the published commit, and the published paper is served from its published files, checksum-verified by the same guard, so neither the evolving artifact nor the toolchain can change what it shows. *Permit only dated errata*, plus one recorded editorial revision for publication — made after building had begun, diffed against the pre-build commit to show it changed no prediction or argument, and removing the one passage that described that validator. And *report outcomes without revising predictions*: a prediction that failed stays in the frozen text as written.

The mechanisation is a few hundred lines of build tooling. Its weakness is granularity: the claims were enumerated from the frozen text after the outcomes were known, which leaves room to split, merge, or omit one flatteringly. The text is published, so the enumeration is checkable, and two of the four statuses are unflattering by construction — *conditional*, exactly as unproven as written, and *not attempted*, no evidence either way — so an honest non-result costs little to report. *Substantiated* means the artifact backs the claim at its scale with a test or measurement; *partial*, that it holds under a restriction the vision did not attach.

#figure(
  table(
    columns: (2.9fr, auto, 1fr),
    align: (left, left, left),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*Prediction from the founding vision*], [*Status*], [*Evidence*]),
    ..outcomes.map(o => (o.at(0), o.at(1), o.at(2))).flatten()
  ),
  caption: [The founding vision's #outcomes.len() claims and what the artifact does to each. Every "Substantiated" is qualified by the demonstrator's scale — #ev.corpus.canonical_total graphs, one domain, a curated corpus (@sec:threats).],
) <tab:outcomes>

*Two substantiated rows carry a scope.* Trust laundering is rejected for data labelled untrusted — at every node not declared a discharger, and a tool-capable node cannot be declared one — and what a handle returns is not labelled (@sec:threat-security). Rotation is expressible, but checks only a replacement's kind, so it can widen scope (@sec:identity).

*The partials*, by restriction. No capability can be exceeded, and no authority is ambient, on the confined tier only; the host tier escapes (@tab:tiers). Even there, a capability's kind is fixed by the binary, but an HTTP allowlist holds only where it is routed exactly, since a sub-graph receives a wider routed allowlist unattenuated (@sec:open). Prompt injection is attenuated by capability scope wherever it enters, but the structural part — untrusted input transits a discharging type before any tool-capable node, which the sink rule enforces — holds only for input the graph declares untrusted; the vision counted third-party responses and model output as untrusted sources, but what a handle returns is not labelled, so indirect injection through retrieved content reaches the tool-capable node bounded by scope alone (@sec:threat-security). Interchangeability is shown for the ported bodies by a tier-equality test, not a checked contract; no canonical graph attaches one. Contracts are checked but not verified — the vision's word was "verified" — and the only generated body, `ParseMessage`'s, predates the contract language, meets contracts only in test fixtures, and was generated uncontrolled and unmeasured.

*The conditionals* — soundness, the full lattice, and CHERI — are untouched, and this paper keeps their conditional mood rather than upgrading it to the present tense around them, which is the discipline most easily lost and the one a build check can least enforce.

*The authorisation, replay and editor rows have something adjacent.* A run records and propagates its principal, but no authority decision consults it and no handle is bound to it (@sec:identity). The trace is the structured log the replay claim assumed, but recording is not re-execution, and nothing is replayed. The inspector is the reviewing half of the predicted editor, but it authors nothing, and the agent workflow is untouched. Earlier drafts of this accounting recorded the editor as partial on the strength of the inspector, and authorisation on the strength of the recording; each was an adjacent mechanism flattering the prediction, and review rather than tooling caught both.

== What building it corrected <sec:corrections>

Agreement between predictions the author chose and an artifact the author directed is cheap. A correction is not: a place where the artifact contradicted the design and the design moved. Without the frozen text each would have been an invisible edit. There are three.

*Revocation had an unnoticed prerequisite.* The vision reached for caretaker indirection @miller_robust_2006 without noticing that revoking a *specific* handle requires naming one, when the natural default shares one handle per type. Capability identity had to become expressible before revocation was well-posed (@sec:identity) — the analogy imported the mechanism and dropped its precondition.

*"No ambient authority" named two guarantees.* The first confined tier satisfied the sentence by the host's configuration while its modules still imported `fd_write` and `path_open`; the rebuilt tier satisfies it in the artifact (@sec:sandbox-tier). Only the second survives a misconfigured deployment. Building it twice found the distinction; the frozen text is what makes the vision's undifferentiated phrasing legible as a correction rather than as something always known.

*The cheapest boundary convention was the least checked.* The union convention for a sub-graph's output type was asserted in the graph source and verified against nothing, so a node could misdescribe what it emits (@sec:subgraph). A boundary type that abbreviates must still be verified against what it abbreviates.

Two of the three are corrections to _security_ claims, and all three share a shape: the vision was wrong not about whether a property could hold but about what the property *was* — a failure mode prose is bad at exposing, because a sentence like "nodes have no ambient authority" reads as one claim and is two.

*One apparent correction is a simplification, and is not counted.* The vision treated local trust discharge and the wiring check as separate obligations, and offered a no-upward-coercion lattice only for the second; building made them one order applied in two places (@sec:validator). Nothing forced this: the separate rules of the validator that predates the freeze already caught the laundering graph. The artifact argued the vision into a simpler design, but did not contradict it.

= Related work <sec:related>

To our knowledge no existing system combines graph-level capability analysis, trust-propagated type checking across component boundaries, and implementations confined to what the graph grants; the property emerges from the combination. The prior art that matters most is where each element is already done better.

== Securing LLM agents against prompt injection <sec:agentsec>

Greshake et al. @greshake_not_2023 documented _indirect_ prompt injection — adversarial instructions in content the model retrieves — against deployed LLM applications, and AgentDojo @debenedetti_agentdojo_2024 turned the threat into a benchmark of 97 tool-using tasks and 629 security cases. Beurer-Kellner et al. @beurer-kellner_design_2025 catalogue design patterns that trade generality for resistance — action-selector, plan-then-execute, dual-LLM, context-minimisation. The `CustomerSupport` graph instantiates several, but as consequences of the wiring checked at assembly rather than patterns a developer applies; the cost is that the graph cannot express the behaviours those patterns exclude.

CaMeL @debenedetti_defeating_2025 shares the central intuition — the defence belongs in the system around the model — and reaches for the same currency, capabilities: it runs untrusted data through a quarantined LLM without tools and enforces capability policies over value provenance in a custom interpreter before each tool call, solving 77% of AgentDojo tasks with provable security against 84% undefended. CaMeL enforces at *runtime*, per call, inside one agent; the signal graph enforces *statically*, before anything runs, over a composed system. Its policies govern data provenance, including what tools return; `with` clauses govern *authority topology*, and the lattice here labels only what a node declares, not what a handle returns (@sec:threat-security). And its guarantees rest on its interpreter and on a faithful LLM-generated plan, where a confined node's authority is bounded in kind by its binary even if every analysis above it is wrong, its scope being the handle the host routes. The signal graph presumes the topology is authored in advance, an assumption CaMeL deliberately avoids. Neither closes the free-text residual.

Closest in mechanism is TACIT @odersky_securing_2026: agents emit Scala 3 code under capture checking @boruch-gruszecki_capturing_2023, so the type system prevents generated code forging access or exceeding its capability budget, and a `Classified[T]` wrapper marks values only designated mechanisms may discharge. It shares our thesis. The differences cut both ways: TACIT checks freeform code as it arrives, where the graph checks a fixed topology before anything runs and gives up TACIT's expressiveness; TACIT's boundary is the source language, where the import table binds the artifact but bounds only authority, not behaviour; and `Classified[T]` belongs to one computation, where the lattice here propagates across a wiring. TACIT is also the more thorough evaluation, on established agent benchmarks across model families. Language-based agent control @zhou_language_2026 takes the same route in Haskell — a `Trusted` wrapper whose hidden constructor is the nearest relative of discharge here — and matches CaMeL's utility on AgentDojo. This work evaluates against no published suite, which is the sharpest statement of what its curated corpus costs (@sec:threat-construct).

== Architecture descriptions that constrain <sec:c4>

Model-driven architecture @omg_mda_2014 foundered on round-trip engineering, because models and generated code diverged; the signal graph is not a model _of_ the code but the program at the level humans review. C4 @brown_c4_2018 is the lightweight successor, which recent tooling @likec4_2025 and practitioners, the author included @lavi_c4_skill_2025, extend toward agent context — but C4 describes an authority distribution and nothing checks the deployed artifact against it. The derivation of @sec:sandbox-tier is that missing check.

One tradition constrains more strongly than this work does. In CAmkES @kuz_camkes_2007, the seL4 component framework, an architecture description generates the glue code and, through capDL @kuz_capdl_2010, the initial capability distribution, with a proof that the distribution has exactly the inter-component authority the description declares @klein_formally_2018. That is a proof where this work offers a test. CAmkES *generates* the authority-bearing artifact, so model and artifact agree by construction; here bodies are compiled independently — in this corpus's setting, by any agent — and what is checked is that the binary asks for no more than the graph grants. Generation with proof is stronger wherever one verified toolchain builds the whole system; deriving and checking is what remains when the code inside a component is authored elsewhere.

== The WebAssembly Component Model <sec:sandboxing>

WebAssembly gives capability-based isolation at near-native speed @haas_bringing_2017, and its Component Model @w3c_component_model_2024 declares typed imports and exports in WIT. WASI is a standard library of such interfaces, and a worked precedent: each host resource granted as an explicit typed interface, the same object as `DBHandle<'knowledge-base', read>`. This work recognises WASI's interfaces as one instance of capability-as-interface and extends the discipline to application capabilities.

The ecosystem already ships most of the surrounding claim. Fermyon Spin @fermyon_spin_2026 allowlists each component's outbound hosts; wasmCloud @wasmcloud_2026 links a component's WIT interface to a *named provider instance*, which is capability identity in production; and WASI-Virt @bytecodealliance_wasi_virt_2026 composes a virtual adapter to satisfy or remove a component's WASI imports, already making confinement a property of the artifact. None of that is claimed as new. What we did not find is the step taken here: deriving the permitted interface set from a *separate, higher-level architecture model* and gating the build on comparing it against the binary. wasmCloud routes against hand-authored WIT, and WAC's `wac targets` @bytecodealliance_wac_2026 checks a component against a hand-written world; McCann's certified-purity gate @mccann_certified_2026 parses a workflow executor's import section at admission against one fixed whitelist rather than a set derived per component; and Wassette @microsoft_wassette_2026 links agent tools against all of WASI 0.2 behind a policy file, the host-configured confinement of our earlier build. This was a survey of published documentation, not an audit, in an ecosystem that moves quickly. Because every WASI version rebases onto the same Component Model @wasi_030_2026 @wasi_roadmap_2026, bespoke WIT interfaces leave the tier untouched by WASI churn; only a directly granted WASI interface, such as the clock, tracks it.

== Capabilities, effects, and adjacent traditions <sec:effects>

The object-capability model @miller_robust_2006 @goos_paradigm_2003 has been realised in languages (E, Caja @google_caja_2012), operating systems (Capsicum @watson_capsicum_2010, seL4 @klein_sel4_2009), and runtimes (Deno @deno_2025); E and Hardened JavaScript @agoric_hardened_2023 extend it to the network, where reachability is itself ambient authority. CHERI @watson_cheri_2015 makes every pointer a hardware capability, and is reaching silicon @sci_first_silicon_2026 @amar_cheriot_2023; it would backstop the confined tier at the memory level, and nothing here has run on it. Effect systems make effects typed and explicit — Koka @leijen_type_2017, Effekt @brachthauser_effects_2020, and Scala's capture checking @boruch-gruszecki_capturing_2023 at function granularity, Roc's platforms @feldman_roc_2025 at application granularity — and Effect @effect_ts_2026 brings a requirements channel much like a `with` clause into production TypeScript, though with ambient authority beside it, the host tier at language scale, and no provenance lattice. The BEAM @armstrong_making_2003 is the closest runtime to the intended one, and durable-execution systems — Temporal @temporal_2025, Restate @restate_2025 — validate the journalling the replay claim assumes. Visual automation (n8n @n8n_2025) and agent frameworks (LangGraph @langchain_langgraph_2025) already build directed graphs of actions without the typed capabilities or trust propagation that are the subject here.

= Limitations and open problems <sec:threats>

The failure mode of a paper like this one is not a false claim but a true claim read more broadly than it was made.

== Construct validity <sec:threat-construct>

*The corpus is curated, and counts are not coverage.* #ev.corpus.mutation_rejected of #ev.corpus.mutation_total faulty graphs rejected is #d.mutations_caught_pct by construction: a case enters the corpus only once the validator catches it. #ev.corpus.found_by_review of the #ev.corpus.mutation_total passed the validator until an adversarial review of this paper found them and the checks were changed, so the corpus holds the mistakes someone thought to write down, and nothing bounds the rest. Reason-class pinning keeps the mechanism under test from silently stopping; it says nothing about mistakes absent from the corpus.

*The derivation is only as right as its mapping table.* The comparison catches a binary that drifts from the graph, not a mapping entry that is wrong — a kind mapped to an interface more permissive than the type intends would produce an agreeing row and an over-granted node. What bounds this is that each entry is one reviewable line, which is an argument, not a check.

*One domain, and the injection result is not benchmarked.* Every canonical graph describes a customer-support pipeline chosen to display the properties under test. @sec:eval-injection drives one hand-written message through one graph: a demonstration of the mechanism, not an attack-success rate comparable with published defences. Expressing AgentDojo's environments as graphs is the work that would make the attenuation claim quantitative.

== Internal validity <sec:threat-internal>

*The per-crossing cost is a differenced quantity, and fragile.* Any systematic cost landing in one of two timings is charged to the boundary, and a contended machine moves the figure by a decade, since differencing amplifies any slowdown that lands unevenly on its two terms. The harness therefore pins the measurement to a band, re-measures an excursion, and fails the build on a sustained one; the magnitude quoted is interpolated from that pinned run. The supported claim is the magnitude, #d.crossing_magnitude, not the figure. Instance pooling is unimplemented, and complex-type serialisation is unmeasured.

== External validity <sec:threat-external>

*#ev.graphs.customer_support_nodes nodes, not hundreds.* Every claim about reviewability is made at that scale. Surveying 152 studies, @yoghourdjian_exploring_2018 report roughly 120 nodes as the ceiling for graph-reading tasks inside two minutes, and density rather than node count as what makes a graph unreadable; whether capability-annotated graphs stay sparse by construction is untested. Nor is there evidence that a graph beats queryable text for *comprehending* a large system: production systems executing graphs at that scale — Dagster @dagster_2026, Airflow @airflow_2026 — are authored in text with the graph as a generated view, and Enso @enso_2026, built on bidirectional graph-and-text editing, found its fit in small analyst graphs. The inspector's scope, viewing but not authoring, is the position that evidence supports.

*The confined tier is #ev.injection.confined_count of #ev.injection.path_length path nodes, not the system.* The platform around them runs on the host tier, where the same escapes succeed. The runtime is a single-threaded Python proof of concept, with no differential evaluation, snapshotting, or deployment.

== Threats to the security argument <sec:threat-security>

*No soundness result.* Nothing connects well-typed wiring to noninterference. Every security claim here is a claim about *what the implemented checks reject*, not about what a sound type system would guarantee.

*Enforcement stops at the WASM boundary*; a `wasmtime` defect is out of scope, and CHERI is unimplemented.

*The free-text residual is real, and nothing here closes it.* Adversarial text survives in a permitted field on the confined tier (@tab:injection). What bounds it is the capability scope, not the type and not the sandbox.

*Trust enters only where it is declared.* A value read through a capability — a knowledge-base row, an HTTP body, a model's reply — leaves its node at whatever level the node's output declares. Retrieved adversarial content, the indirect injection of @greshake_not_2023, is therefore invisible to the lattice unless a node's output type says `Untrusted<_>`, and nothing checks that it does: a graph fetching a feed and handing it to a tool-capable node validates with no `Untrusted` anywhere, and the canonical `FetchContext` hands knowledge-base rows to `GenerateResponse` as clean data. The lattice rejects laundering of what is labelled; labelling what a handle returns is the author's obligation, not the checker's. And the sink rule treats only a tool-scoped model as privileged: labelled untrusted data may still reach a node holding a writable store or an HTTP client, so the topology keeping it from those is authored, not checked.

*Covert channels and distributed authority are out of scope.* A node can encode information in the timing or shape of its legitimate outputs, and one with a network capability can acquire authority the graph does not model. `HTTPClient` makes the second concrete, against this work: an allowlist entry is a _host_, and a host grants everything reachable at it. Anthropic report exactly that failing in production — allowlisting one API host also permitted uploads to arbitrary accounts — and conclude that an egress allowlist is better read as a capability grant than as a destination filter @anthropic_contain_claude_2026. A set-valued scope narrows by inclusion; it does not make what is included finer.

== Threats from the method <sec:threat-method>

*The accounting is one instance, run by its designer.* The predictions were enumerated by the predictor after the outcomes were known, and a different granularity would produce a different table; the freeze guard prevents silent revision of the text but not a generous reading of it — the editor row shows that failure is live. The artifact and its evaluation were produced by the same AI-driven process, and so risk agreeing for reasons unrelated to the truth of the claim, which is why the harness pins verdicts and reason classes rather than reporting what it finds, and why figures are interpolated rather than transcribed. None of this substitutes for independent replication, which has not occurred. *Not everything was built after the freeze.* A validator running early forms of the analyses of @sec:validator predates it, so the static-rejection, trust, and declared-distribution rows of @tab:outcomes credit analyses that partly existed when the predictions were frozen, and the published vision no longer describes it. The freeze point itself was designated two days after building began, as the last commit without the executable demonstrator; in between, the same document was amended in place with building findings, and the freeze restored the pre-build text as a separate paper. Version control dates the text, not the decision, and the author can rewrite it: a later history rewrite re-identified every commit from 14 July onward, trees unchanged and the pre-build commit untouched. Since the guard now checks the published text, only version history — which the author can rewrite — attests the pre-build text.

== Open problems that bound these results <sec:open>

*The lattice is chosen for tractability, and no soundness argument exists.* The two-point form has support: W3C Trusted Types @w3c_trusted_types_2026 is exactly a two-point lattice with a single designated discharge, shipped across browsers, while Filament @ching_filament_2026 leaves the lattice to the user. A successor must keep the wiring check's flow relation *transitive*, so a path of well-typed edges is well-typed, and *monotone*, so composition cannot manufacture trust. Compositional noninterference follows from standard results #cite(<sabelfeld_language-based_2003>, supplement: [§5]) only once the wiring model is shown to meet their conditions. The two-point lattice meets both trivially, which is why it is weak evidence for a richer one, graded or decentralised @myers_decentralized_1997.

*Contracts are partial specifications.* Two bodies can satisfy the same contract and still differ in latency, resource use, or the variant emitted on inputs the contract does not pin, so regeneration can change behaviour with no check failing, and the richer contract language the model wants is undesigned. The generative mode that would fuzz a body against its own precondition is designed and unbuilt.

*User-level authorisation is recorded but neither bound nor typed.* Systems that keep delegation analysable — Cedar @cutler_cedar_2024, Biscuit @biscuit_2026 — restrict narrowing to a monotone, enumerable operation, while Zanzibar-style stores @pang_zanzibar_2019 put the decision in a live service no artifact describes. A deployment needing such a store must hold the check as a capability in a `with` clause, or the authority decision moves where no validator can see it.

*Composition, state, and fan-in.* Capability narrowing is checked but not enforced: a parent's wider handle reaches the child as it is. An HTTP allowlist, the one handle-held scope that narrows by inclusion, is then the parent's on either tier (a store name must match exactly, and a tool client may not be routed into an inference-only slot); a wider mode or tool set the child's clause omits stays out of reach on the confined tier, whose component has no interface for it, but not on the host tier. Attenuating at the routing point is unimplemented. Routing by position is settled at the runtime, not shown right — a flat list matched by type is where aliasing ambiguity lives — and whether named output ports or an aggregation node should replace the checked union convention is open. The graphs are stateless and run a single active path: node-local state, fan-out, and runs reaching several terminals are unaddressed. Where several nodes feed one consumer, arrival order is a scheduling artifact, and the merge must be classified as order-insensitive, needing nothing recorded, or order-sensitive, needing its realised order journalled — a prerequisite to replay and to differential evaluation @budiu_dbsp_2023, whose results hold for declarative operators over deltas and not, as the vision stated it, for nodes whose effects cannot be re-run on a delta.

*Drift is detected, not prevented.* An over-granting component is built and then rejected. Composing unwanted imports away in the WASI-Virt manner @bytecodealliance_wasi_virt_2026 would make it unbuildable, and adopting that as defence in depth is unimplemented.

= Future work <sec:future>

The obvious next experiment is the one the design most depends on. Every node body here but `ParseMessage`'s was written in the ordinary directed loop, and that one was generated uncontrolled and unmeasured, so the claim that implementations are generated against typed signatures and are interchangeable is untested at any useful scale, though the artifact now makes it checkable: a generated body compiled to the confined tier that imports a capability kind its `with` clause does not grant is caught by the derivation before it ships. Whether that happens, how often, and whether the gate is the operative constraint on agent-authored code is what we expect to be most informative. Beyond it lie a typed lattice with a soundness argument, beginning from the conditions of @sec:open; fan-in with its merge-order classification, where monotonicity first becomes load-bearing; authoring in the inspector with the validator in the loop; and the AgentDojo evaluation that would make attenuation a measured rate.

= Conclusion <sec:conclusion>

Architecture models in mainstream use describe; they do not constrain. This paper reports a demonstrator in which one constraint is mechanical: a node's declared capabilities determine the import surface of its compiled artifact, derived from the graph and checked against the binary, so over-granting fails the build. That the components carry no WASI adapter makes the absence of ambient authority a fact about the binary rather than about the host's configuration — a distinction that sounds identical in prose, names two guarantees, and became visible only after building the tier both ways. It is the point at which an architecture diagram stops being documentation. Beside it, a trust lattice with no upward coercion rejects the laundering graph in which every edge type-checks, pinned so it cannot silently become a type mismatch; crossings cost #d.crossing_magnitude; and a sub-graph cannot be provisioned authority its parent did not route, because the executor holds no backend to provision from, though on the host tier a body can still reach around the object model.

The design was frozen at its last state before the executable demonstrator was built, and of its #outcomes.len() predictions #verdicts("Substantiated") are substantiated at this scale, #verdicts("Partial") hold only under restrictions it did not state, #verdicts("Conditional") remain conditional, and #verdicts("Not attempted") were not attempted. The yield was in the three corrections: in each, the vision was wrong not about whether a property could hold but about what the property was.

The distance remaining is larger than the distance covered. Nothing here is a soundness result; the corpus measures implementability, not coverage; the injection finding is a demonstration, not a benchmarked rate; prompt injection is attenuated, not eliminated, and the lattice sees only what the graph declares untrusted, not what a capability returns; and the host tier's escapes are a real gap that two tiers make transitional rather than acceptable. What is not settled is whether anyone can build software this way. The machinery for finding out is now in place.

// Bibliography
#bibliography("/citations.bib", style: "ieee")
