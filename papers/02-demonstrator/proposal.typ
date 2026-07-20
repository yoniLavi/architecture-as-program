// Document setup
#set document(
  title: "Architecture as Program: A Capability-Injected Signal Graph and What Its Demonstrator Substantiates",
  author: ("Yoni Lavi"),
  date: datetime(year: 2026, month: 7, day: 20),
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
#let ev = json("/dist/evaluation.json")
#let d = ev.display
#let tick(ok) = if ok [#text(fill: rgb("#1a7f37"))[✓]] else [#text(fill: rgb("#b91c1c"))[✗]]

// Title block
#align(center)[
  #text(size: 16pt, weight: "bold")[
    Architecture as Program: A Capability-Injected Signal Graph and What Its Demonstrator Substantiates
  ]
]

#align(center)[
  #text(size: 12pt)[Yoni Lavi] \
  #text(size: 10pt, style: "italic")[Codeliance]
]

#align(center)[
  #text(size: 11pt)[July 2026#footnote[
    This is the second paper of a longitudinal research program. The first
    @lavi_architecture_2026 set out the founding vision in June 2026, before an
    executable demonstrator existed, and is preserved frozen and unedited as the
    archived record of what was predicted. This paper reports what was
    subsequently built and what that artifact does and does not establish. Where
    the two disagree, the disagreement is the finding, and @sec:outcomes states
    it prediction by prediction.
  ]]
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
  *Abstract.* AI coding agents have removed the thirty-year obstacle to graph-based code representations: the human preference for text. A companion paper @lavi_architecture_2026 argued from that premise for a development model in which the primary artifact is a _signal graph_ — a functional reactive program with explicitly typed capability boundaries — serving simultaneously as architecture model, security policy, and source of truth, and predicted that a class of vulnerability would become ill-typed rather than merely discouraged. This paper reports a demonstrator built to test that prediction, and evaluates it. The demonstrator comprises a graph validator implementing six classes of static analysis over canonical graph definitions, an executable runtime that instantiates nodes with injected capability handles, and two enforcement tiers: host-level object discipline, and a confined tier compiling node bodies to WebAssembly components whose imported WIT interfaces _are_ their declared capabilities. We find that unsafe wirings are rejected at assembly time, each by the analysis it is meant to exercise — including trust laundering, which type-checks on every edge and is caught as a lattice violation rather than a type mismatch; that a capability-boundary crossing costs #d.crossing_us µs, inside the #d.envelope_crossing_ms ms envelope the vision asserted without evidence, even though every crossing now marshals typed values; and that escape attempts succeeding on the host tier are refused on the confined tier, where an inference-only node's component imports no filesystem, socket, environment, or clock interface at all. We are equally explicit about what does not follow. The corpus is curated and illustrative, so the counts are not a soundness result; no noninterference proof is attempted; the host tier's escapes are a real gap, reported rather than omitted; and prompt injection is _attenuated, not eliminated_ — adversarial text survives in a permitted free-text field, and what bounds the damage is the capability scope rather than the type. The contribution is an existence proof at modest scale that graph-level capability analysis and confinement are implementable, together with a precise account of the distance remaining to the vision's stronger claims.
]

#v(1em)

= Introduction <sec:intro>

For thirty years, a small community of researchers pursued an idea that working software developers consistently rejected: that source code should be a structured graph, not text in files. Projectional editors @jetbrains_mps_2025, structure editors @simonyi_intentional_2006, model-driven architecture @omg_mda_2014: the history of these efforts is a history of elegant ideas that foundered on a single obstacle: programmers prefer text editors, value syntactic flexibility for half-formed thoughts, and resist representations that constrain expression before intent is clear.

That obstacle has moved. The rapid adoption of AI coding agents (Claude Code @anthropic_claude_code_2025, Codex @openai_codex_2025, Cursor @anysphere_cursor_2025, Windsurf @codeium_windsurf_2025) has introduced a new primary author of implementation code that does not _require_ the specific affordances of text editing that motivated human resistance to structured representations. What agents benefit from instead is semantically rich, machine-readable representations of intent that prevent entire categories of error before generation begins. Recent work on LLM code generation within the Hazel typed-hole environment @blinn_statically_2024 gives direct empirical evidence: providing agents with rich static context from the type system substantially improves generation quality. The graph representation that human developers rejected may be precisely what agent-authored software requires — and the parallel emergence of spec-driven development frameworks (OpenSpec @fission_openspec_2025, GitHub's Spec Kit @github_spec_kit_2025, AWS's Kiro @aws_kiro_2025) is evidence that practitioners have already begun treating structured intent, rather than generated implementation, as the artifact that matters.

The companion paper to this one @lavi_architecture_2026 argued that these trends converge on a development model built around a _signal graph_: a program written in a functional reactive style in which each node is a function from typed inputs to typed outputs, all authority is held as explicitly declared capability handles, and trust is a propagating type-level annotation. In that model the graph is simultaneously the architecture model, the security policy, and the program; implementation code inside nodes is a compiled artifact. That paper was written before any of it had been built, and said so: its security claims were stated conditionally throughout — properties that _would_ hold in a sound realisation of a type system that did not yet exist.

This paper reports what happens when that model is built.

== The central claim <sec:claim>

The claim this paper defends is deliberately narrower than the vision's, and is chosen to be falsifiable by the artifact accompanying it:

#block(width: 100%, inset: (x: 1.5em, y: 0.6em), stroke: (left: 2pt + luma(140)))[
  A signal graph with capability-annotated, trust-annotated types admits a
  practical static analysis that _rejects at assembly time_ — before any node
  executes — a class of wirings that conventional architectures can only
  discourage by review, including the trust-laundering case that type-checks on
  every edge; and node bodies can be confined so that a node's declared
  capabilities are the totality of what its artifact can reach, at a
  capability-boundary cost of tens of microseconds.
]

What this claim does not say is as important as what it does. It does not say the system is provably secure: no soundness argument connects well-typed wiring to noninterference here, and that gap is Phase 3 work (@sec:phase3). It does not say prompt injection is prevented: it is attenuated, and @sec:eval-injection reports the residual that survives on the confined tier. It does not say the corpus of caught mistakes is complete: it is curated, and counts of caught mutations are evidence of implementability, not of coverage (@sec:threats). A reader who finishes this paper believing a stronger claim has been shown has been misled by it, and we have tried throughout to make that outcome difficult.

== Contributions <sec:contributions>

- *A graph validator* implementing six classes of analysis over canonical graph definitions — edge type-compatibility, a flow-sensitive trust lattice, variant completeness, capability narrowing at composition, intra-graph consistency, and cross-graph signature matching — in which trust laundering is a violation of the _same_ no-upward-coercion order that governs edges, rather than a rule bolted on beside edge typing (@sec:validator).
- *An executable runtime with two enforcement tiers* that composes in one graph: host-level object discipline, and a confined tier compiling node bodies to WASM components for which a node's `with` clause _is_ its component's import set, so confinement is a property of the artifact rather than of the host's configuration (@sec:tiers).
- *Operational hierarchical composition*: a node whose name resolves to another graph executes by nested assembly, from which capability confinement across the composition boundary follows from the plumbing rather than from a rule (@sec:subgraph).
- *Capability identity, revocation, and rotation* expressed in the graph source — identity and revocation enforced on both tiers, rotation on the host tier — resolving a prerequisite the vision did not notice its own revocation problem had (@sec:identity).
- *An evaluation* — corpus verdicts pinned to the reason class that must catch them, boundary overhead against the vision's stated envelope, and prompt-injection outcomes on both tiers — emitted as a build artifact so that every figure in @sec:evaluation traces to a reproducible run and a regression fails the build.
- *An explicit predictions-and-outcomes accounting* against the frozen vision (@sec:outcomes), separating what the artifact substantiates from what remains conditional.

== Relation to the founding vision <sec:relation>

The two papers are deliberately different kinds of document, and the corpus keeps them apart rather than merging them. The vision paper @lavi_architecture_2026 is _frozen_: it reproduces the repository's state before the demonstrator existed and is corrected only by dated errata, so that what was predicted cannot be quietly revised once outcomes are known. This paper is _living_: it is rewritten as the artifact evolves, and builds its figures from the shared, current research artifact.

That arrangement is what makes @sec:outcomes possible, and it is the reason this paper exists separately rather than as a revision. A vision paper edited in place to match its results is unfalsifiable by construction; the interesting content — which conditional claims survived contact with an implementation, which needed weakening, and which turned out to be harder than the hedge admitted — is available only if the original stands unaltered. @sec:outcomes states that accounting prediction by prediction.

The remainder of the paper is organised as follows. @sec:design presents the design, largely inherited from the vision and restated here to make the paper self-contained. @sec:implementation reports what was built. @sec:evaluation evaluates it. @sec:outcomes gives the predictions-and-outcomes accounting. @sec:related positions the work against prior art, @sec:agenda sets out the forward agenda including the problems that remain open, and @sec:threats states the limits of what has been shown.

= Design <sec:design>

This section presents the design the demonstrator implements. It is largely inherited from the founding vision @lavi_architecture_2026 and restated here so that this paper stands alone; readers of that paper may skim to @sec:implementation. Two things have changed in the restatement, and both are marked where they occur: claims the demonstrator has since substantiated are stated in the present tense, and claims it has not are left in the conditional mood they were written in. @sec:outcomes collects that accounting in one place.

The model has four interlocking properties.

*The signal graph as source of truth.* The primary artifact that humans author, review, and version-control is a functional reactive program (FRP — see @sec:frp for the paradigm and its history): a directed graph in which each node is a function from time-varying typed inputs to time-varying typed outputs, with any effects mediated through explicitly declared capability handles. This graph is simultaneously the architecture model, the security policy, and the program. It _is_ the implementation at the level of abstraction humans author and review; the code inside each node is a generated artifact derived from it.

*Capabilities as declared requirements.* Nodes have no ambient authority: side effects (database access, network calls, LLM invocations, event emission) are not capabilities that code can reach for from the surrounding environment. They are typed capability handles declared separately from data inputs using a `with` clause — for example, a node with signature `(OrderRequest) → OrderConfirmation with DBHandle<'orders', read-write>, EventEmitter<'order-events'>` can read and write orders and emit order events, and nothing else, because no other mechanism exists within its scope. A node with no `with` clause is a pure function of its inputs in the conventional sense.

*Code as compiled artifact.* AI agents generate the implementation of each node to satisfy the behavioural contracts encoded in the graph's type signatures. The imperative code inside each node is an implementation detail, analogous to compiled bytecode. It can be regenerated, refactored, or rewritten without changing the system's meaning, provided it satisfies its contracts — an interchangeability claim that holds up to the expressiveness of those contracts, a limit examined in @sec:phase2. Humans review graph transformations; they do not routinely review generated code.

*Security by construction.* Because capabilities are injected and the type system propagates trust annotations, security properties are intended to be structural invariants of the graph rather than aspirations enforced by code inspection. The strength of the resulting guarantees varies by vulnerability class and is worth naming up front. Injection attacks that depend on untrusted input reaching an interpreter in executable form would be statically ill-typed in a sound realisation. Privilege escalation — a node acquiring capabilities it was not given — would be prevented by construction, because the graph would be the complete and sole description of the capability distribution. Prompt injection and confused-deputy patterns are structurally attenuated through capability scoping and trust propagation rather than wholly eliminated; the precise strength of each guarantee, together with its schema-design prerequisites, is detailed in @sec:security, and what the demonstrator measured of it in @sec:eval-injection.

== Functional reactive programming as the conceptual core <sec:frp>

The signal graph model is not a novel metaphor. It is a direct application of _functional reactive programming_ (FRP), a paradigm with a nearly thirty-year research history, here elevated from a UI programming technique to a whole-system architectural substrate.

=== FRP: a brief account <sec:frp-brief>

FRP was introduced by Elliott and Hudak in their 1997 paper _Functional Reactive Animation_ @elliott_functional_1997, which modelled interactive animations as pure functions over continuous time. The central abstractions are _behaviours_ (values that vary continuously over time) and _events_ (discrete occurrences at points in time). Programs are expressed as compositions of these abstractions, without explicit state mutation or callback registration. The semantics are denotational: a behaviour is literally a function `Time → Value`, giving the paradigm a clean mathematical foundation that supports equational reasoning unavailable in imperative or callback-driven styles.

Subsequent work refined the model. Wan and Hudak's _Functional Reactive Programming from First Principles_ @wan_functional_2000 gave the paradigm a rigorous stream-based semantics, characterising the conditions under which a sampled implementation is faithful to the continuous denotation. Building on Hughes's arrow abstraction @hughes_generalising_2000, Nilsson, Courtney, and Peterson then developed _arrowized FRP_ @nilsson_functional_2002, which makes _signal functions_ (rather than signals themselves) the primary composable unit. This restriction prevents certain classes of space and time leaks and, more importantly for our purposes, makes the interface of each signal function explicit in its type. A signal function with signature `SF a b` transforms a signal of `a` values into a signal of `b` values. This is the formal object we extend with capability annotation.

The most prominent early realisation of FRP principles for browser UIs was Elm @czaplicki_elm_2012, which enforced purity strictly, made all effects explicit and managed by the runtime, and avoided runtime exceptions in practice. Elm later moved away from explicit FRP, but the design properties it demonstrated remain instructive. In the JavaScript ecosystem, the FRP lineage continued through RxJS @rxjs_2025 (observable stream composition) and Cycle.js @cyclejs_2025, which structures entire applications as pure functions from input streams to output streams with all side effects handled by external drivers. Cycle.js is particularly relevant: a component not given a DOM driver or an HTTP driver simply cannot perform those effects, a discipline close to this work's capability injection. The gap is the absence of fine-grained capability typing and trust propagation, not the basic architectural shape.

A parallel tradition of graph-based reactive programming exists in the synchronous dataflow languages (Lustre @halbwachs_synchronous_1991, Esterel @berry_esterel_1992, and Signal @benveniste_signal_1991), developed primarily for safety-critical embedded systems. These languages compile reactive signal graphs to deterministic, formally verifiable code and have decades of deployment in avionics and nuclear instrumentation. An adjacent industrial tradition, flow-based programming @morrison_flow-based_1994, anticipated the componentised form of the idea: applications assembled as networks of black-box components exchanging data across named ports, with the network definition maintained as an artifact distinct from component code — though without static typing of the network, and with no notion of capability or trust. At the commercial end of this tradition, LabVIEW @ni_labview_2025 and Simulink @mathworks_simulink_2025 are the most widely deployed graph-based programming environments, validating the "graph as program" concept at scale while also illustrating the UX challenges (version control difficulty, visual clutter, loss of context at scale) that inform the graph-scale comprehension problem discussed in @sec:agenda. The synchronous dataflow languages' formal verification track record is directly relevant to Phase 3 of our research agenda, though their focus on synchronous, clock-driven execution differs from the asynchronous, event-driven model this work targets.

More recently, the FRP research community has explored _differential_ computation, evaluating only the graph nodes affected by a change. Differential dataflow @mcsherry_differential_2013, as implemented in Materialize @materialize_2025 and the DBSP framework @budiu_dbsp_2023, demonstrates that this is practical at database scale. This work's claim that the signal graph can serve as a production substrate, beyond a development-time abstraction, depends on this line of work.

*A concrete illustration.* To motivate the extensions developed in @sec:frp, consider a node that processes user-submitted text and passes it to an LLM with tool-calling access. In a conventional system, this is dangerous: if the submitted text contains adversarial instructions, the LLM may execute them using its tools. The vulnerability is not a bug in any individual component; it is an architectural property: the unintended flow from untrusted input to a privileged executor.

In the signal graph, the same scenario is expressed as two nodes. The first, `UserInputHandler`, has signature:

```
UserInputHandler : (HTTPRequest<'POST', 'user:message'>) → Untrusted<UserMessage>
```

The second, `LLMOrchestrator`, has signature:

```
LLMOrchestrator : (SanitisedPrompt) → AgentResponse
  with LLMClient<[respond, lookup]>
```

A direct wiring from `UserInputHandler`'s output to `LLMOrchestrator`'s input is a _type error_: `Untrusted<UserMessage>` does not match `SanitisedPrompt`. The graph cannot be assembled without an explicit node that transforms `Untrusted<UserMessage>` into `SanitisedPrompt` — a node whose existence is visible in the architecture, whose implementation is subject to contract verification, and whose presence is required by the type system rather than by a policy document. In a well-typed realisation of this model, the prompt injection vulnerability would be _ill-typed_: no well-typed graph could express it. The type system design that would deliver this guarantee is the central obligation of Phase 1 (@sec:phase1); the example illustrates the target property, not a proven result.

#figure(
  image("/dist/diagrams/typed-wiring.svg", width: 80%),
  caption: [The direct wiring of the two nodes above is structurally rejected: the output type `Untrusted<UserMessage>` does not inhabit the input type `SanitisedPrompt`. An explicit sanitisation node — not shown — would be required by the type system to close the gap. Security, here, would be a property of graph shape.],
) <fig:typed-wiring>

=== Extending FRP: capability annotation and trust tainting <sec:frp-architecture>

The step from FRP as a UI technique to FRP as a whole-system architectural model requires two extensions that the existing literature does not fully address.

The first is _capability annotation_. Standard FRP treats effects as values managed by the runtime, but does not give them a fine-grained type structure that distinguishes, say, a read-only database handle from a read-write one, or a sanitised string from an untrusted one. The object-capability model @miller_robust_2006 provides the missing ingredient: capabilities are unforgeable typed references whose possession is the proof of authorisation. Combining FRP's signal graph semantics with the object-capability model's typed authority gives us signal graphs in which data-flow and capability-flow are both first-class, typed, and statically checkable.

The second is _trust tainting_. Data entering the graph from untrusted sources (user input, third-party API responses, LLM outputs) carries a type marker that propagates through signal transformations until it passes through an explicitly designated sanitisation node. This is analogous to taint tracking as studied in information-flow security @sabelfeld_language-based_2003, and specifically to the labelled-IO approach demonstrated by practical information-flow control libraries such as LIO @stefan_flexible_2011, but expressed as ordinary type-level propagation rather than a separate analysis. A node that accepts `Untrusted<string>` and a node that accepts `LLMClient<[respond, lookup]>` cannot be directly wired; the type system would prevent the combination. The graph topology would enforce the security property without separate analysis.

=== Time as a structural dimension <sec:time>

In a conventional program, time is implicit: state changes in place, and its history is lost unless explicitly logged. In the proposed signal graph model, under the purity guarantees the runtime would enforce, time would be structural: every signal would carry a history, and the system's behaviour at any point would be a pure function of its input signals up to that point. This has immediate practical consequences.

Proposing a change to the system would mean forking the signal graph's timeline. An agent would explore the fork, observing projected effects on downstream signals. If the exploration is satisfactory, the fork is merged into the main timeline; if not, it is discarded with no cleanup cost, because the fork is a value, not a mutation. The human review step would not be a diff of two static models but a _behavioural comparison of two timelines_, including the agent's exploratory history and the projected downstream effects on dependent signals.

In production, this structural temporality would double as observability infrastructure. Every crossing of a capability boundary (every database read, network call, or LLM invocation) would be a typed, observable event. A structured log of these events would constitute a record of the system's inputs (subject to the fidelity limitations discussed in @sec:agenda). Given that log and a deterministic signal graph, the system's behaviour at any past point would be substantially reproducible. Debugging a production failure would mean replaying the event log in the development environment, reconstructing the timeline, and forking the failure point. The replay of the production event log would provide a substantial basis for regression testing; authoring it would not be a separate step.

== The signal graph <sec:signal-graph>

The primary artifact is a version-controlled, typed signal graph with the following structure.

*Nodes* are functions with explicit signatures. A node's signature has two parts: its _data inputs_ (typed signals from upstream nodes) and its _capability requirements_ (typed handles to external resources, declared with a `with` clause). The data inputs describe what the node transforms; the capability requirements describe what authority it has. This separation reflects a lifecycle distinction: data signals flow at runtime as the graph propagates, while capabilities are provisioned when the graph is instantiated. A node with no `with` clause is a pure function of its inputs; a node with a `with` clause is pure with respect to its inputs _given_ its handles, with all effects mediated through those handles.

_A note on the design choice._ An alternative design treats capabilities as ordinary typed parameters alongside data inputs, consistent with the object-capability model's principle that capabilities are just values. We separate them syntactically because the distinction between "what a node transforms" and "what authority it holds" serves different review concerns — architecture and security — and because the lifecycle difference is real: capabilities are bound at construction, data flows at invocation.

*Edges* are typed data connections between nodes. An edge from node A's output to node B's input is valid only if the types match. Edges carry data; capabilities are not wired through edges but provisioned via `with` clauses. This is a deliberate restriction. Object-capability systems in the E lineage permit dynamic delegation by passing capability references through messages, which is flexible but defeats static analysis of the authority topology. The signal graph trades that flexibility for a fully statically analysable capability distribution; the distributed extension of this trade-off is a separate problem discussed in @sec:agenda. The `with` clauses collectively constitute the architecture's security policy, expressed as reviewable graph structure rather than prose. Because the graph's parameter list declares all external dependencies, swapping a production capability for a mock (replacing a live `DBHandle` with a test fixture, for example) requires only a change at the graph boundary — no node signature changes, since the `with` clause names a type, not a specific instance.

*Trust annotations* (the type-level markers introduced as trust tainting in @sec:frp) propagate through the graph. Data entering from untrusted sources carries a type marker, `Untrusted<T>`, that is preserved through transformations until explicitly discharged. In a well-typed realisation, the type system would prevent `Untrusted<T>` from reaching a node that accepts only `T`. Discharge is most effective when it is not merely a label removal but a _type transformation_: converting unstructured input into a constrained representation whose structure limits what downstream nodes can receive. The combination of trust propagation and structural typing is what would deliver the security properties claimed in @sec:security.

An important open design question must be acknowledged here. The trust annotation scheme as described enforces the _local_ typing of individual nodes, but the full security guarantee requires that the _wiring_ also be checked; specifically, that a source classified as untrusted at the graph's edge cannot be connected to a node whose signature expects a clean `T`, bypassing the `Untrusted<T>` marker through a widening coercion. This is the standard coercion problem in information-flow type systems #cite(<sabelfeld_language-based_2003>, supplement: [§3]): local type correctness of nodes is necessary but not sufficient for noninterference; the type system must also enforce that the subtyping relation between `Untrusted<T>` and `T` is absent, or equivalently, that wiring compatibility checks are flow-sensitive with respect to trust levels.

Several solutions exist in the literature — most directly, treating trust levels as _security labels_ in the style of Jif @myers_decentralized_1997, or imposing a lattice structure on trust types with no upward coercion. The demonstrator implements a first realisation of the latter, and @sec:validator reports what that realisation does and does not settle. The design question itself remains open: whether a minimal two-point lattice suffices or a graded (`Untrusted ⊑ Sanitised ⊑ Trusted`) or Jif-style decentralised-label model is needed, and — critically — a soundness argument that well-typed wiring implies noninterference, which nothing here attempts (@sec:agenda). The claim is not that this problem is solved but that it is tractable, and that the right place to solve it is in the type system, where the literature provides well-understood tools.

*Behavioural contracts* are attached to node signatures as pre- and postconditions. These are the specifications against which AI-generated implementations are verified, and the stable interface across which different implementations are interchangeable. The contract language is a Phase 1 design obligation: candidates range from refinement types in the Liquid Haskell tradition, through Dafny- or Ada-style declarative specifications, to lightweight examples-and-invariants in the QuickCheck tradition. Contracts are authored alongside node signatures — either by the developer at graph-review time, or proposed by the agent during intent capture and confirmed on review — and checked by a combination of static analysis (for properties the type system expresses directly) and property-based or contract-based testing at implementation time (for properties that require runtime evidence). The tractability trade-off between contract expressiveness and automatic verification is addressed in @sec:agenda.

== A concrete graph <sec:concrete-graph>

The following pseudocode sketches an AI customer support agent as a signal graph. This scenario was chosen because it is a domain where the security properties of the signal graph model are most immediately visible: untrusted user input, LLM invocations with and without tool access, and fine-grained capability distinctions are all present. Unlike the simplified two-node illustration in @sec:frp, this example shows a realistic pipeline with structured input parsing and content moderation. The `SanitisedPrompt` of that earlier sketch is expanded here into the refined type `ModeratedQuery`, with trust discharge decomposed across two dedicated nodes (parsing and moderation) rather than collapsed into a single transformation. No concrete syntax has been designed; this is illustrative of the kind of artifact a developer would author and review.

_Syntax conventions used below._ Types are written angle-bracketed: `T<...>`. Capability types are parameterised by scope: `DBHandle<'knowledge-base', read>` denotes a handle to the `knowledge-base` database in read mode, where `read`, `append`, and `read-write` denote modes in a permission lattice (a handle with a wider mode may be supplied where a narrower one is required: `read-write` covers both `read` and `append`, which are mutually incomparable). `LLMClient<inference>` is an inference-only LLM client (model access without tool-calling); `LLMClient<[lookup]>` grants a single named tool, `lookup`. Sum types may be written with named role labels, as in `ok: ModeratedQuery | violation: PolicyViolation | escalation: EscalationRequest` — the label on the left of the colon is an edge-addressable role, the type on the right is the variant's value type. An edge addresses a specific variant of an upstream node's output as `Node.role` (for example, `ModerateContent.ok` is the `ModeratedQuery`-valued output). These conventions stand in for a concrete syntax that Phase 1 must design; the value here is the structural shape, not the notation.

#raw(read("/dist/graphs/customer-support.graph"), block: true)

The graph's parameter list declares its complete external dependencies: an inbound request, a database handle, two LLM clients with different permission levels, a response channel, and an event emitter. `CustomerRequest` is the domain entry type: a narrowed representation of HTTP POST traffic to `/customer/*` that can be produced either by a direct HTTP adaptor in a standalone deployment or by the `RouteRequest` dispatcher in the composed deployment shown below. Using a domain name for the entry type rather than a raw `HTTPRequest<...>` lets the same graph serve both deployments without signature churn. This list is the system's authority manifest. In production, these parameters are bound to real infrastructure; in testing, they are replaced with mocks or deterministic fixtures. Because the graph has a typed signature (its parameter list and output types), it can itself be used as a node in a larger graph. Hierarchical composition falls out naturally from the model. To make this concrete, the following graph sketches a platform that composes `CustomerSupport` (the graph above) alongside two other services:

#raw(read("/dist/graphs/support-platform.graph"), block: true)

`CustomerSupport` is no longer nine nodes visible at this level; it is a single node with a typed signature. Its internal wiring — the trust zones, the graduated LLM access, the moderation routing — is encapsulated. At the platform level, the reviewer sees only what authority each service holds and how data flows between them. The platform's parameter list is the union of its sub-graphs' requirements: the `DBHandle`, `LLMClient`, and channel capabilities each appear exactly where they are needed. `BillingService` has read-write access to the billing database but no LLM access; internally it would be a conventional pure pipeline — input validation, policy checks, and DB transactions — with no reliance on LLM nondeterminism, and how its shape differs from `CustomerSupport` is itself visible at the composition level through the absence of LLM capabilities. `AgentDashboard` can read the knowledge base but cannot write to billing. These constraints are visible at a glance in the capability annotations.

The boundary output `ServiceOutcome` declared here is the aggregation of `CustomerSupport`'s internal terminal outputs — in this example, the disjoint union of `DeliveryConfirmation` (from the reply paths) and `EscalationTicket` (from the escalation path). The sub-graph has several terminal nodes of different types, and the composition requires a single boundary type; treating `ServiceOutcome` as that aggregated union is the simplest of several possible designs. The same type also serves as the boundary output of `AgentDashboard` and `BillingService`: at the platform level, `ServiceOutcome` is the shared outcome currency that `RecordAudit` consumes, and each service maps its own terminal types onto it. How multi-terminal sub-graphs should expose their outputs (as a union-typed boundary, as named multi-output ports, or via an explicit aggregation node inside the sub-graph) is a Phase 1 language-design question noted in @sec:agenda.

Hierarchical composition also surfaces a design obligation this work does not claim to have solved. When `SupportPlatform` provisions `LLMClient<inference>` to `CustomerSupport`, the sub-graph's internal wiring must route that capability to the specific internal nodes that require it (`ParseMessage` and `ModerateContent`) and not to others. How a sub-graph exposes its internal capability requirements at its boundary — as a flat union reabsorbed by convention, as named capability slots, or via structural matching on capability types — is an open question noted in @sec:agenda and part of the Phase 1 language design. The complementary, narrower question — which _instance_ of a capability type a parent routes to each sub-graph — is now expressible in the canonical graph source: `CustomerSupport` and `BillingService` both require `ResponseChannel<user-session>`, and the platform binds each a distinct named instance (`customer_session` and `billing_session`, shown in the composition figure below), so identity is carried across the composition boundary rather than aliased by type. @sec:identity and @sec:subgraph report what the demonstrator makes of both questions: the narrower one is implemented and tested, the internal-fan-out surface remains open.

#figure(
  image("/dist/graphs/support-platform.svg", width: 75%),
  caption: [The SupportPlatform composition graph. Each service node is a sub-graph (the nine-node CustomerSupport graph is now a single node). Capability annotations show the authority distribution at the platform level; where a service holds a distinct named instance of a capability type, the identity label is shown after `@` (the two services holding `ResponseChannel<user-session>` are routed distinct `customer_session` and `billing_session` instances). The audit node collects outcomes from all services with append-only database access.],
) <fig:support-platform>

The `CustomerQuery` type is central to the security argument. `ParseMessage` does not merely strip the `Untrusted` wrapper from free text: it transforms unstructured input into a constrained representation — a classified intent (from a finite set of categories), extracted entity references, and bounded text fields — whose type limits what downstream nodes can receive. The raw message is consumed; downstream nodes never see it. `ModerateContent` then refines this further into a `ModeratedQuery` (the `.ok` variant of its output), a type distinct from `CustomerQuery` that records, at the type level, that a moderation check has occurred. Downstream nodes accept only `ModeratedQuery`, so a wiring that bypasses moderation is ill-typed; the type distinction makes the moderation step _load-bearing_ rather than advisory.

This is a stronger guarantee than trust annotation alone: a well-typed `ModeratedQuery` cannot carry arbitrary executable instructions in positions that flow to privileged nodes, _provided the schema is designed to exclude unbounded free text in those positions_. This proviso is essential and bears stressing: the framework provides the enforcement substrate (structural typing, capability separation, topological constraint), but eliminating prompt injection requires disciplined schema design within that substrate. A schema that retains a free-text field (most real schemas do, for the original question itself) still treats that field as adversarial at every point where it reaches an LLM-capable node. The defence is layered rather than absolute, but each layer is visible in the graph topology and, in a sound realisation, enforceable by the type system.

#figure(
  image("/dist/graphs/customer-support.svg", width: 85%),
  caption: [The CustomerSupport signal graph. Red shading marks the untrusted zone; green shading marks the structured region. Edges show data flow; capability requirements are annotated on each node. LLM access (blue) is graduated: inference-only for parsing and moderation, a single lookup tool for response generation.],
) <fig:customer-support>

This diagram is simultaneously the architecture model, the security policy, and the program. Several properties are visible at a glance, without reading any implementation code.

_Prompt injection is addressed through structural typing and topological constraint._ `ParseMessage` transforms raw input into a `CustomerQuery`, a constrained representation that discards the original free text. It is worth naming the trust placement this entails: the LLM is itself the trust-discharging component, since `ParseMessage` consumes `Untrusted<RawMessage>` and emits a non-`Untrusted` `CustomerQuery` on the strength of the LLM's classification. This trust is bounded by the LLM's capability shape (`LLMClient<inference>` grants model access without tool use) and by the schema of `CustomerQuery`, which constrains downstream exposure regardless of how the LLM is influenced. Both LLMs that process user input (`ParseMessage` and `ModerateContent`) have `LLMClient<inference>`: even if adversarial instructions influence their behaviour, they have no mechanism to act on them. The tool-capable LLM (`GenerateResponse`) receives only `ConversationContext` assembled from a `ModeratedQuery` and knowledge-base lookups — never raw user text. A direct path from untrusted input to a tool-capable LLM does not exist in the graph; in a sound realisation of the type system, it would be ill-typed. A subtlety must be acknowledged: capability restriction prevents the LLM from _acting_ on adversarial instructions, but not from being _influenced_ in its classification. An adversarially crafted message could cause `ParseMessage` to produce a `CustomerQuery` that misclassifies intent, routing the query to the wrong downstream path. The defence here is twofold: the attack surface is narrowed from arbitrary tool execution to incorrect routing within a typed pipeline (a qualitative reduction in severity), and the routing itself operates within the user's authorised scope — if downstream actions are bounded by the user's own credential-scoped capabilities (passed as a parameter at the graph boundary), a misrouted query can only trigger actions the user was authorised to perform. Separating user-level authorisation from node-level capability injection is a design consideration for Phase 1 and is listed as an open item in @sec:agenda.

_Capability distribution is minimal and visible._ The `with` clauses are a complete manifest of the system's authority. `ReceiveMessage` is pure: it transforms a typed customer request into a domain message with no `with` clause. `ParseMessage` and `ModerateContent` have inference-only LLM access: enough to classify and evaluate text, not enough to act on instructions. `FetchContext` has read-only knowledge-base access. `GenerateResponse` has a scoped LLM client with a single lookup tool and read-only database access. Terminal nodes (`SendReply`, `NotifyUser`, `HandleLLMError`) each have only a session-scoped response channel. `EscalateToHuman` can emit to the support queue but cannot read or write any database; its `EscalationTicket` output is a published identifier that a containing graph may route onward (for auditing or agent-dashboard display) or discard, consistent with the pattern that every node produces a typed value whether or not the current composition consumes it. No node has more authority than its function requires.

_Conditional routing and error handling are explicit._ `ModerateContent` produces a three-way union: approved queries continue to the response pipeline as `ModeratedQuery`, policy violations are routed to user notification, and ambiguous cases are escalated to human agents. `GenerateResponse` returns `AgentResponse | LLMError`, with the error case routed to `HandleLLMError`. In both cases, the routing is a structural property of the graph, visible in the diagram and the pseudocode. The validator enforces that every declared variant has a downstream consumer, but it cannot force a node's implementation to emit the _correct_ variant for a given input — a `ModerateContent` that always emits `.ok` would be well-typed but behaviourally wrong. Variant-correctness is a behavioural-contract obligation, checked by the shallow-verification work of @sec:agenda.

For concision, this example also elides transient infrastructure failures: `ParseMessage` could fail to classify, and `FetchContext` could fail on knowledge-base read errors. A production-shape version of the graph would route those into error variants using the same variant-typing mechanism shown for `GenerateResponse`, with their own terminal handlers. This is a presentation choice in the example rather than a claim that such failures do not exist.

The precise syntax for conditional routing, fan-out, and error propagation is an open design question for the Phase 1 language design; see @sec:phase1.

== The development workflow <sec:workflow>

The workflow below is proposed rather than implemented: the demonstrator covers the structural half of its verification step and none of the rest (@sec:conditional).

+ *Intent capture.* A human describes a desired change in natural language. An SDD-style tool translates this into a proposed graph transformation: new nodes, modified `with` clauses, changed signatures or contracts. Existing SDD frameworks produce prose specifications; extending their output to _typed graph transformations_ is the step most load-bearing for the development workflow to cohere, and is a core Phase 1 deliverable (@sec:phase1).
+ *Graph review.* Humans review the diff as a visual graph change: new nodes highlighted, new capability requirements marked, trust boundary crossings flagged. This review is simultaneously an architecture review, a security review, and a design review. The reviewer is approving a typed program transformation, not reading prose.
+ *Implementation.* AI agents generate code for each new or modified node, targeting the capability-restricted runtime. Each node is implemented in isolation: the agent receives the node's signature, its contracts, and the types of its inputs and outputs. It has no visibility into adjacent nodes' implementations. The rationale for isolation is not that agents benefit from less context in general — prior work @blinn_statically_2024 shows the opposite — but that any cross-node dependency an implementation might introduce must flow through the typed signature, preserving the graph as the complete specification of inter-node interaction. Context the agent would otherwise glean from adjacent implementations (error conventions, retry shapes, shared assumptions) must be lifted into types or contracts to have effect; this is a discipline the graph enforces by construction.
+ *Verification.* Automated tooling confirms that implementations satisfy their contracts, that the assembled graph conforms to the declared types, and that no node exceeds its injected capabilities. Since the runtime enforces capability restrictions, verification is primarily structural (type-checking and contract satisfaction) rather than arbitrary dataflow analysis.
+ *Merge.* If verification passes, the graph transformation is merged. The human approved the graph diff; the machine confirmed conformance. Routine human review of generated node implementations is not required to establish architectural or security properties — those are decided at the graph level. Spot checks of generated code for efficiency, clarity, or residual concerns remain available to reviewers who want them; the default position of the workflow is that contract-satisfying implementations are accepted without line-by-line review.

Nodes are individually testable by injecting mock capability objects and asserting output signals against input sequences. Graph-level integration tests are expressed the same way, at the graph boundary. The replay mechanism described in @sec:time doubles as regression testing infrastructure: a recorded production event log is a ready-made test suite.

== The runtime <sec:runtime>

In the intended runtime, each node would execute in a lightweight, capability-restricted sandbox (a WASM module, a Monty-style interpreter, or a BEAM-like process), with CHERI hardware where available. What the demonstrator implements of this is reported in @sec:tiers, and it is a strict subset: two tiers, one of them WASM components, no CHERI, no BEAM, and no Monty. The intended properties are:

*No ambient authority.* As described in @sec:signal-graph, a node would not be able to import libraries, access the filesystem, make network calls, or perform any side effect beyond calling methods on its injected capability objects, enforced by the absence of any mechanism rather than a policy guard.

*Defence in depth.* The type system would prevent the graph from expressing forbidden capability grants. The runtime sandbox would prevent generated code from exceeding its injected capabilities. The operating system would compartmentalise processes with OS-level enforcement. On CHERI hardware, the processor prevents capability forgery at the memory level. These layers are not fully independent, because the runtime's capability injection is configured by the type system's analysis, so a type system bug could misconfigure the runtime. But they would provide overlapping coverage with distinct failure modes: a sandbox escape does not help an attacker who lacks a hardware capability, and a type system error does not propagate past a correctly configured OS compartment. This is weaker than fully independent enforcement but substantially better than any single layer.

*Language agnosticism.* WASM is the intended compilation target, supporting Rust, C, C++, Go, and Python (via interpreters such as Monty). The signal graph defines component interfaces using a language-neutral type system; the implementation language is an optimisation choice made by the AI agent, or specified by performance constraints in the node's contract.

*Snapshotting and resumption.* Nodes would be pausable, serialisable, and resumable, enabling durable execution, time-travel debugging, and the production replay loop described in @sec:time. BEAM supports this robustly: hot code reloading and process-state inspection are native. WASM support is maturing — WASI 0.3 @wasi_030_2026 brought native async to the Component Model, which is progress on exactly the in-flight-I/O composition this needs — but component snapshotting and resumption mid-execution are not yet a solved capability. This is an implementation constraint for the Phase 1 demonstrator, not a fundamental limitation of the model.

*Evaluation strategy.* How the runtime propagates signal changes through the graph is a design choice with performance implications. A naive strategy re-evaluates every node on every input change; a differential strategy, in the tradition of differential dataflow @mcsherry_differential_2013 and DBSP @budiu_dbsp_2023, evaluates only the nodes affected by the change. The differential strategy is the target, treating the graph as a dataflow network whose nodes memoise outputs against inputs; the demonstrator implements neither, propagating signals along an active path in a single thread (@sec:threat-external). This is consistent with the differential FRP line of work referenced in @sec:frp and is what makes per-node sandboxing cost-acceptable at graph scale.

== Security properties <sec:security>

The capability-injection model would provide security guarantees qualitatively different from those achievable by code review or runtime monitoring.

*Injection attacks.* SQL injection and command injection depend on untrusted input reaching an interpreter in executable form. In the signal graph, a SQL-executing capability would accept typed queries, not raw strings. `Untrusted<string>` could not reach it without passing through a sanitisation node that produces a typed query. In a sound realisation of the type system, the pattern would be ill-typed — rejected by the type system rather than left to convention.

*Prompt injection.* Structurally attenuated through the combination of trust annotation, capability scoping, and schema discipline described in @sec:frp and @sec:concrete-graph: no well-typed wiring would connect an untrusted source to a tool-capable LLM without transiting a type that constrains the downstream payload. The strength of this guarantee depends on the schema chosen for the discharging type (a free-text field that reaches an LLM-capable node remains adversarial data even if the wrapper is non-`Untrusted`); the framework provides the enforcement substrate, disciplined schema design makes use of it.

*Supply chain attacks.* The defence operates primarily through _capability scoping_ rather than I/O denial. A library used within a pure node on the confined tier has no ambient authority and can be malicious with no effect, but most libraries in practice are used within nodes that _do_ hold capabilities: a database driver inside a node with a `DBHandle`, an HTTP client inside a node with a network capability. For that common case, the defence is that the capabilities are _scoped_: the `DBHandle` is bound to a single database in a specific mode; the HTTP client is scoped to a declared set of endpoints; the LLM client is scoped to a tool allowlist. A malicious library inherits only the scope of the node it inhabits, not ambient authority, and the blast radius is bounded by that scope rather than by the library's creativity — on the confined tier as a property of the artifact, on the host tier only as an object discipline a hostile library can reach around (@sec:eval-tiers). On CHERI hardware, even a library that attempts to exploit a memory safety vulnerability to escape its sandbox cannot forge a capability to memory it was not granted. If a library update introduces a new capability requirement, this appears in the graph diff as a new `with` clause — a visible, reviewable change — rather than as an implicit elevation.

*Confused deputies.* A privileged node acting on instructions derived from an unprivileged source is the classical confused-deputy pattern; the signal graph attenuates it through two mechanisms. First, capability scoping (above) limits the damage any one node's authority can do. Second, for operations whose safety depends on _which user_ initiated them, capabilities passed at the graph boundary can be bound to the calling user's credentials, such that downstream nodes operate only within that user's authorised scope. The distinction between user-level authorisation and node-level capability injection — and the precise mechanism by which the former is threaded through the latter — is a Phase 1 design obligation noted in @sec:concrete-graph and expanded in @sec:agenda.

*Covert channels remain an open concern.* A node granted a permitted capability can in principle encode information into its legitimate outputs (the choice of SQL query, the timing of LLM invocations, the shape of emitted events) in ways that leak data through channels the type system does not model. The `Untrusted<T>` discipline and the noninterference properties of the underlying type system would address a subset of these, but general covert-channel elimination is a known-hard problem and is not claimed here. This is flagged as an open item in @sec:agenda.

*Privilege escalation.* A node would not be able to acquire capabilities it was not given. The graph would be the complete and sole description of the system's capability distribution. On CHERI hardware, this guarantee extends to the memory level. Two caveats catalogued in @sec:agenda bound this claim: a node holding a network capability can in principle acquire authority out-of-band from services the graph does not model (distributed ambient authority), and for user-scoped operations the guarantee is only as strong as the principal-binding design that Phase 1 must deliver.

= Implementation <sec:implementation>

The demonstrator is a working, tested implementation of the graph-level analyses and the capability-injected runtime described in @sec:design. It is deliberately small, and its scope should be stated before its results are: it is *not* the Phase 1 language of @sec:agenda. It implements no noninterference proof, no dependent types, no contract language, and no visual editor. What it does implement is the part of the vision whose implementability was least obvious from the outside — that a graph carrying capability and trust annotations can be statically analysed to reject unsafe wirings, and that node bodies can be confined to exactly the authority their signatures declare — and it does so with enough tooling to be run, tested, and measured on every commit.

Everything in this section is built and tested; the present tense is used accordingly. Where a property is asserted by a test, that is said, because a test is the form in which this project prefers to record a claim: prose can drift from an artifact, a failing test cannot.

== Canonical graphs and the type grammar <sec:impl-graphs>

The graph definitions in `graphs/*.json` are the single source of truth, validated against a JSON Schema. Both the pseudocode listings and the SVG diagrams reproduced in @sec:concrete-graph are generated from them, so the figures in this paper cannot drift from the graphs the validator and runtime actually consume — the two graphs shown are the two graphs run.

A small type-expression parser reads the capability-annotated type grammar: angle-bracketed generics, capability scopes and modes, and sum types with role labels. The documented grammar is itself emitted from the parser as a build artifact rather than maintained by hand, on the same principle.

== The validator: six graph-level analyses <sec:validator>

A dependency-free validator implements six classes of analysis over the canonical graphs.

/ Edge type-compatibility: source output types, with sum-type variant resolution, must match target input types in data shape, independently of trust.
/ Trust-lattice checking: trust levels form a two-point lattice `Untrusted ⊑ Trusted` with no upward coercion — `Untrusted<T>` is not a subtype of `T` — and the wiring check is flow-sensitive with respect to trust, applied uniformly to edges *and* to node bodies. A node may raise trust only if it is declared a discharger with `discharges_trust: true`, as `ParseMessage` is in the `CustomerSupport` graph.
/ Variant completeness: every declared sum-type output variant must have at least one consuming edge, so dead branches are visible at the graph level rather than hidden inside node implementations.
/ Capability narrowing: at cross-graph composition a parent may provide a handle whose authority exceeds what the sub-graph declares — a wider `LLMClient<[...]>` tool set, or a `DBHandle<X, read-write>` where `read` is required — while strict equality still governs every data-flow position.
/ Intra-graph consistency: every declared capability is used, every boundary data input is consumed, and every edge references a valid node and output variant.
/ Cross-graph signature matching: a node whose name matches another graph's name must satisfy that graph's parameter list position by position.

The second of these is the one worth dwelling on, because its design changed under implementation and the change is a result rather than a detail. Trust is *not* a rule beside edge typing; it is the same no-upward-coercion order, applied to two places. The consequence is what @sec:eval-corpus measures: the blunt unsafe wiring — untrusted input run straight into the tool-capable node — fails as an ordinary data-shape mismatch, but the subtle one survives that check. Widen the tool-capable node's declared input to `Untrusted<RawMessage>` and every edge in the graph type-checks on data shape. The graph is still rejected, because the tool-capable node now emits a non-`Untrusted` output from an `Untrusted<_>` input without being a declared discharger, which is an upward coercion under the lattice.

That case is the argument for the discipline. An earlier design that folded trust into ordinary subtyping — admitting `Untrusted<T> <: T` — would have accepted the widened graph, with the failure invisible at the level of edge types. Trust laundering is thereby one violation of one principled order, and local edge data-compatibility is shown not to be the property worth checking. What the validator does *not* establish is soundness: that every graph well-typed under this lattice satisfies noninterference. That obligation is untouched, and is Phase 3's (@sec:phase3).

== Two enforcement tiers <sec:tiers>

The runtime loads the same canonical graph JSON, instantiates each node with injected capability handles, and propagates signals along the active path. Nodes run on one of two enforcement tiers, and the runtime reports which ran each node. The distinction between them is the whole point, so it is stated precisely.

=== The host tier <sec:host-tier>

The default tier is *host-level object discipline*, not unforgeable containment. Each node receives only the handles its signature declares, and each handle exposes only the operations its type permits: a handle for `LLMClient<inference>` has no tool-calling operation at all, and one for `LLMClient<[lookup]>` refuses every other tool. This demonstrates the _shape_ of the guarantee. It does not enforce it against a node that declines to play by the object model — nothing stops a hostile Python node from importing `os` and reading the filesystem directly.

That gap is not left as a caveat in prose. A hostile-node suite asserts that filesystem, network, environment, and ungranted-capability escapes *succeed* on this tier. The gap is recorded as a passing test, which is the only form in which it cannot be forgotten, and it is reported in @sec:eval-tiers rather than omitted from the evaluation.

=== The confined tier <sec:sandbox-tier>

The second tier closes that gap for the nodes ported to it. Node bodies are compiled to WebAssembly *components* (@sec:sandboxing) — Rust, via `wit-bindgen`, to `wasm32-unknown-unknown`, converted to a component with `wasm-tools` — and run under `wasmtime`. Each capability kind is declared as a typed WIT interface: `LLMClient<inference>` becomes an interface offering a single inference function, `DBHandle<'knowledge-base', read>` one offering `lookup` and no writer. A node's `with` clause is then precisely the set of interfaces its component imports.

On this tier the inference-only guarantee changes in kind rather than degree: an `LLMClient<inference>` node has no tool-calling *import*, not merely no tool-calling method, and a component declaring a capability it was not granted cannot be instantiated at all — the refusal lands before any guest code runs. Two properties follow from the boundary being typed rather than byte-oriented, and both are asserted by tests rather than argued in prose.

*There is no ambient authority to reach for, as a property of the artifact rather than of the host's configuration.* An earlier iteration of this tier compiled nodes to `wasm32-wasip1` modules run under an empty WASI context — no preopens, sockets, environment, or clock. That confined them, but the modules still *imported* `environ_get`, `fd_write`, and `path_open`; the imports were present and merely powerless, so confinement was a fact about how the host had configured the runtime, and a misconfigured host would have silently granted them. Compiled for `wasm32-unknown-unknown` and linked with no WASI adapter, no filesystem, socket, environment, or clock function appears among the imports at all — the hostile component imports nothing whatsoever. What was a configured absence is now a structural one, and the suite asserts the import set directly. A `wasip2` build would reintroduce the problem through `wasi:cli/*`, which is why the tier targets a bare component rather than a WASI snapshot.

*The boundary cannot silently drift from the node's declared signature.* Because a component's imports are typed interfaces rather than opaque symbols, the import set the runtime will accept is *derived from the graph*: each node's expected interfaces are computed from its `with` clause in the canonical JSON and compared against what the built component actually imports. A world that grants a node an interface its signature never requested fails that check rather than shipping as a quiet over-grant.

The same typing absorbed two node-body checks into types. Under the earlier flat `(ptr, len)` ABI, `ParseMessage` received an intent label as a string and had to *check* it against the permitted set so that adversarial text could not widen it; expressed as a WIT `enum`, widening is not representable, the check is gone, and the property is held by the type rather than by the node's own diligence. The model's reply is likewise a WIT `variant`, so a malformed reply has no encoding.

Two security-critical nodes run as components while the rest run on the host tier, so the two tiers demonstrably compose within one graph — the incremental-migration path of @sec:phase2, from opaque host node to confined node. One of them, `ParseMessage`, was regenerated in Rust from the same signature and contract as its Python counterpart: a concrete instance of the code-as-compiled-artifact property, with the same contract, a different implementation language, and an unchanged graph.

What this tier does not provide is memory-level unforgeability. Enforcement is unforgeable at the WASM boundary; a sandbox escape via a runtime defect is out of scope, and hardware-backed enforcement (CHERI) remains Phase 3 work. Nor does typing the boundary touch the residual free-text channel — @sec:eval-injection reports that residual, measured on this tier on purpose.

== Capability identity, revocation, and rotation <sec:identity>

The vision named capability revocation as an open problem and, in doing so, exposed a prerequisite it had not noticed: revoking a *specific* handle first requires a way to *name* it. With capabilities shared by type, there is no instance to revoke without severing every node that names the type.

The runtime's default is indeed to provision one handle per declared capability *type*, shared across every node whose `with` clause names it, so two nodes each declaring `DBHandle<'knowledge-base', read>` receive the same object. For read-only handles this is harmless; for stateful, rate-limited, or revocable handles it is not. Capability *identity*, not merely capability type, must therefore be expressible at the graph boundary.

It now is, and in the graph source rather than only through an assembly API: each node may carry a `capability_identities` map binding a declared capability type to an identity label. A capability with no identity declared keeps the type-shared default, so existing graphs are unchanged. Because identity lives in the JSON, the validator checks it — an identity declared for a capability a node does not hold is rejected at validation time — and the generated pseudocode and diagrams render it, so a distinct instance is visible in the artifact and cannot drift from the source. That two same-typed handles carry independent state is a tested property.

On that prerequisite, revocation and rotation are built as one mechanism. An instance provisioned as *revocable* is wrapped in a caretaker @miller_robust_2006: the node holds a forwarding proxy, and a separate revoke authority — kept by the host that assembled the graph, never handed to a node — severs it, after which the node's next use fails loudly instead of exercising authority. *Rotation* re-points that same proxy at a new resource behind the same identity, guarded to a same-kind replacement so the surface the node holds cannot change kind underneath it. Revoke and rotate are two levers on one indirection rather than two mechanisms. Both are *targeted* (severing one identity leaves its same-typed siblings, and the type-shared default, untouched) and *opt-in* (an instance not declared revocable is provisioned bare), and both are tested.

Enforcement reaches the confined tier as well: a sandboxed node reaches its capabilities through typed WIT host functions backed by the very same caretaker, so severing it makes the guest's next capability crossing fail at the boundary — and there it is unforgeable, because the confined node's import set is its whole world and it has no other path to the resource. On the host tier the caveat is unchanged: severing binds the handle's authority, but not a node that reaches around the object model. Sandbox-tier *rotation*, and the graph-transformation form of both operations, remain undesigned (@sec:phase2).

== Operational composition: sub-graph execution <sec:subgraph>

Hierarchical composition is operational, not merely structural. A node whose name resolves to another graph is a *sub-graph node*, which the runtime executes by nested assembly and execution: the same assembly gate, the same executor. Composition therefore adds no second execution model — a sub-graph is a node whose body happens to be a graph.

`SupportPlatform` accordingly runs rather than merely assembles. A customer request entering at its `HTTPRoute<'platform:*'>` boundary is dispatched by `RouteRequest`, crosses into the nine-node `CustomerSupport` graph, and its outcome crosses back to `RecordAudit`, which appends it to the audit log through an append-only handle that cannot read the log back. Three properties of that crossing distinguish composition from mere call nesting, and all three are tested on the shipped graph.

+ *A sub-graph cannot provision authority of its own.* The executor holds no backend to provision from, so the child receives exactly the handles the parent routed and nothing else. Capability confinement across the composition boundary is a property of the plumbing rather than a rule to be remembered — the case we most expected to need enforcing turned out not to need it, because there was no mechanism by which it could fail.
+ *Identity routing has an executable consequence.* The distinct `customer_session` instance the platform declares for `CustomerSupport` is the instance the reply node *inside* that sub-graph sends on, and its sibling's instance is untouched.
+ *The parent matches the sub-graph's flat parameter list by position and type.* This is option (i) of the capability-routing question the vision left open; it is now settled at the runtime, while the fuller slot surface remains a language-design choice (@sec:phase1).

The demonstration is bounded, and the bounds are worth stating rather than leaving to be discovered. Only leaf nodes on the taken path have implementations: `AgentDashboard` and `BillingService` are neither graphs in the repository nor registered node bodies, so those branches do not run. A sub-graph run reaching several terminals has no single boundary value, and the runtime *refuses* it rather than electing a winner — the multi-terminal aggregation question stays open, and fails loudly instead of silently. A sub-graph on a different enforcement tier from its parent is not attempted.

One gap here is genuine and is recorded as such, because it is the kind a reader would otherwise assume closed. `ServiceOutcome` is the union alias of the sub-graph's terminal types (`DeliveryConfirmation | EscalationTicket`) — the convention @sec:concrete-graph adopts. *Nothing checks that alias.* The graph language has no alias mechanism, so the relation between the name and the two types it abbreviates is asserted in the JSON and verified by nothing; and the cross-graph analysis relates a sub-graph node's *inputs* to the referenced graph's parameters while never examining the output side at all. A sub-graph node could declare any output type whatsoever and no check would object. A test pins this gap so that it cannot be closed by accident and believed to have been closed by design.

= Evaluation <sec:evaluation>

This section evaluates the demonstrator along four dimensions: which unsafe wirings the static analyses reject and by which analysis, what a capability-boundary crossing costs against the envelope the vision asserted without evidence, what an adversarial message can reach once it is inside the graph, and what each enforcement tier actually stops.

*Method.* Every figure in this section is interpolated from a build artifact emitted by a single run of the evaluation harness, which imports the mutation corpus, the benchmark, and the injection scenario rather than re-deriving them. No number below is transcribed by hand. The harness is a regression guard rather than a report: each corpus case pins the verdict it must produce *and the reason class it must be caught by*, and any divergence fails the build instead of rewriting the table. Pinning the reason matters more than pinning the verdict — a pass/fail pin would stay green if trust laundering silently began to be caught as an ordinary type mismatch, which is precisely the regression that would hollow out the central claim. The corpus also pins itself against silent growth: adding an unsafe variant without pinning it is an error, not an uncounted pass.

*Scope.* The corpus is *curated and illustrative*. It contains the unsafe wirings we thought to write down, and the counts below report how many of those were caught. That is evidence the graph-level analyses are implementable and catch the mistakes they target; it is not a soundness result, and no claim is made that the corpus is exhaustive or that an uncaught class does not exist. @sec:threats states this and the other limits in full.

The overhead figures are wall-clock timings from one machine, reported to establish an order of magnitude rather than as portable benchmarks. They were produced on #raw(ev.environment.platform) (#raw(ev.environment.processor)), Python #raw(ev.environment.python), wasmtime #raw(ev.environment.wasmtime).

== Graph-mutation corpus <sec:eval-corpus>

Each case is a graph the validator either accepts or rejects at assembly time, before any node executes. The canonical graphs must be *accepted*: a validator that rejected everything would catch every unsafe wiring and be worthless, so the safe cases are corpus entries in their own right rather than a formality.

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
  caption: [The graph-mutation corpus. Each unsafe case is pinned to the analysis that must catch it, not merely to the fact of rejection.],
) <tab:corpus>

#ev.corpus.canonical_accepted/#ev.corpus.canonical_total safe wirings were accepted and #ev.corpus.mutation_rejected/#ev.corpus.mutation_total unsafe wirings rejected at assembly time, each by its pinned reason class.

The two mutations are chosen to separate a blunt mistake from a subtle one. `bypass_pipeline` wires untrusted input straight into the tool-capable node; the edge simply does not type-check on data shape, and any structural checker would catch it. `launder_trust` is the interesting case: it *repairs* that mismatch by widening the tool-capable node's declared input to `Untrusted<RawMessage>`, after which every edge in the graph is data-compatible. It is nonetheless rejected, as an upward coercion — the node raises trust without being a declared discharger — and it is rejected by the trust lattice rather than by edge typing, which is the property the pin enforces.

This is the corpus's whole point, and its limit. It establishes that the distinction between "type-checks" and "is well-trusted" is real, implementable, and load-bearing on a graph that would otherwise pass. It does not establish that no third kind of mistake exists.

== Capability-boundary overhead <sec:eval-overhead>

The vision asserted a working envelope it had no numbers for: if a node performs on the order of #d.envelope_node_work_ms ms of useful work, a per-crossing cost below roughly #d.envelope_crossing_ms ms keeps total overhead under about #d.envelope_max_overhead. These are the numbers, whichever way they fall.

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

A crossing costs #d.crossing_us µs — #if ev.overhead.within_envelope [within] else [*outside*] the #d.envelope_crossing_ms ms envelope, projecting to #d.projected_overhead overhead on a node doing #d.envelope_node_work_ms ms of work. The measurement was worth making because the typed boundary is not obviously free: the tier's first implementation passed a packed `(ptr, len)` pair into linear memory and let both sides parse the bytes, whereas every crossing measured here marshals typed records, enums, lists, and variants. Typing the boundary did not cost the performance argument.

Two cautions bound the reading. First, these figures should *not* be compared like-for-like with those previously reported for the flat-ABI tier, because the benchmark's timing discipline was corrected at the same time: it now warms each measurement and takes the best of several rounds, where before it timed a single cold pass and so charged JIT and interpreter warm-up to whatever it measured first. Since the per-crossing cost is derived by *differencing* two timings, that defect could distort it by an order of magnitude in either direction. The comparison that survives is the one that matters: typing the boundary did not move the crossing out of its order of magnitude. Second, these are proof-of-concept figures from a Python host and a two-node slice, not a production runtime at graph scale. They establish that the crossing itself is cheap and locate the fixed cost in instantiation; they say nothing about serialisation cost for complex types, or about graphs with hundreds of nodes.

== Prompt-injection attenuation <sec:eval-injection>

An adversarial message instructing the model to call an `exfiltrate` tool is driven through the `CustomerSupport` graph. What matters is not whether the model is fooled — assume it is — but what it can *reach* once fooled. The message traverses #ev.injection.path.len() nodes: #ev.injection.path.map(n => raw(n)).join([ → ]), of which #ev.injection.tiers.values().filter(t => t == "sandbox").len() run on the confined tier and the rest on the host tier.

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, left, center),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*property*], [*result*], []),
    [the tool-capable node received], raw(ev.injection.received_type), tick(not ev.injection.is_untrusted),
    [it received an `Untrusted<_>` value], [#ev.injection.is_untrusted], tick(not ev.injection.is_untrusted),
    [an out-of-scope tool call was refused], [#ev.injection.out_of_scope_call_refused], tick(ev.injection.out_of_scope_call_refused),
    [adversarial text still present in a permitted field], [#ev.injection.adversarial_text_present], [—],
  ),
  caption: [Prompt-injection outcome. The last row is the residual, and it is asserted on the *confined* tier deliberately.],
) <tab:injection>

*The residual, stated plainly.* The last row is not a failure; it is the boundary of the claim. The `Untrusted<RawMessage>` value is consumed at the parse boundary and never reaches the tool-capable node, which receives a #raw(ev.injection.received_type) instead. But the question text itself remains a free-text field, and that field stays adversarial data. The guarantee is therefore *attenuation, not elimination*: the model can still be influenced by that text; it cannot call anything outside `{lookup}`, because the handle refuses. Blast radius drops from arbitrary tool execution to a bad lookup query.

Two things follow that are easy to get wrong in the reading. The confined tier does *not* close this residual — what bounds the damage is the capability scope, not the sandbox — which is why the assertion is made on that tier on purpose, so that stronger enforcement is not misread as a stronger claim. And the attenuation depends on schema discipline, not on the framework alone: a discharging type that retains unbounded free text in a position flowing to a privileged node gives most of it back. The framework supplies the enforcement substrate; disciplined schema design is what makes use of it.

== Enforcement tiers: what each one stops <sec:eval-tiers>

The same escape attempts were run on both tiers. The host-tier column is *expected* to read ESCAPES: host discipline gives a node only its declared handles, but nothing stops a hostile node from reaching around the object model. That gap is the reason the confined tier exists, and it is reported here rather than omitted.

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

The final row is the sharpest: the component imports an interface it was never granted, so it cannot instantiate at all — the refusal lands before any guest code runs. And on the confined tier the capability is *absent, not merely unexposed*. An inference-only node's import set holds only #raw(ev.tiers.inference_node_imports.at(0)), with #ev.tiers.ambient_imports filesystem, socket, environment, or clock imports in it. Confinement is a property of the artifact rather than of how the host happened to configure it — the distinction @sec:sandbox-tier is built to make.

*Fidelity.* Enforcement is unforgeable at the WASM boundary, not at the memory level; CHERI remains a named follow-up (@sec:phase3). Only the nodes ported to the confined tier get it — the rest run on the host tier, which demonstrates the shape of confinement rather than enforcing it. That the two tiers compose in one graph is the incremental-migration path, and it is the reason the host tier's gap is a transitional state rather than a defect of the model.

= Predictions and outcomes <sec:outcomes>

The founding vision @lavi_architecture_2026 made a set of claims about a system that did not exist, and hedged them accordingly: properties that _would_ hold in a sound realisation, guarantees that _would_ be structural. This section states, claim by claim, which of them the demonstrator substantiates, which it substantiates only in part, and which remain exactly as conditional as they were. It is the accounting the frozen-paper arrangement exists to make possible, and it is where a reader should look first if they want to know what has actually changed.

Four statuses are used. *Substantiated* means the artifact backs the claim at the demonstrator's scale, with a test or a measurement behind it. *Partial* means the claim holds under a stated restriction that the vision did not attach to it. *Conditional* means the claim is unchanged: still hedged, still unproven, and still stated in the mood the vision used. *Not attempted* means no work was done and no evidence is offered either way.

#figure(
  table(
    columns: (2.6fr, auto, 1fr),
    align: (left, left, left),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
    table.header([*Prediction from the founding vision*], [*Status*], [*Where*]),

    [Unsafe wirings are rejected statically, before execution], [Substantiated], [@sec:eval-corpus],
    [Trust cannot be laundered by relabelling the consumer], [Substantiated], [@sec:eval-corpus],
    [A node cannot exceed its declared capabilities], [Partial], [@sec:eval-tiers],
    [Nodes have no ambient authority], [Partial], [@sec:eval-tiers],
    [Per-crossing overhead stays inside the stated envelope], [Substantiated], [@sec:eval-overhead],
    [Prompt injection is structurally attenuated], [Substantiated], [@sec:eval-injection],
    [Hierarchical composition follows from the model], [Substantiated], [@sec:subgraph],
    [Capability identity, revocation, and rotation are expressible], [Substantiated], [@sec:identity],
    [Implementations are interchangeable across languages], [Partial], [@sec:sandbox-tier],
    [The _declared_ capability distribution is complete and reviewable], [Substantiated], [@sec:validator],
    [Well-typed wiring implies noninterference], [Conditional], [@sec:phase3],
    [The full type system (graded or decentralised labels)], [Conditional], [@sec:phase1],
    [User-level authorisation threaded through capability injection], [Conditional], [@sec:phase1],
    [Behavioural contracts constrain generated implementations], [Conditional], [@sec:phase2],
    [Memory-level unforgeability on CHERI hardware], [Conditional], [@sec:phase3],
    [Replay and time-travel debugging from boundary logs], [Not attempted], [@sec:phase2],
    [Differential evaluation of the graph at scale], [Not attempted], [@sec:agenda],
    [Agent tooling and the visual graph editor], [Not attempted], [@sec:phase1],
  ),
  caption: [The founding vision's claims and what the demonstrator does to each. Every "Substantiated" is qualified by the demonstrator's scale; see @sec:threats.],
) <tab:outcomes>

== What the demonstrator substantiates <sec:substantiated>

The load-bearing prediction was that a graph carrying capability and trust annotations admits a static analysis strong enough to reject unsafe wirings before anything runs, and that this analysis is implementable with modest tooling rather than requiring a research type system first. That holds. The validator is dependency-free, runs on every commit, and rejects both corpus mutations at assembly time, each by the analysis meant to catch it.

The sharper form of that prediction — that trust cannot be laundered by relabelling the consumer — also holds, and is the result we would keep if forced to keep one. A graph in which *every edge type-checks* is still rejected, because trust is not a property of edges but an order that applies uniformly to edges and node bodies. The vision predicted this would require a flow-sensitive wiring discipline and would not fall out of edge typing; that prediction was correct, and the demonstrator shows the cost of getting it wrong is invisible at the level of edge types.

The performance envelope held with room to spare. The vision asserted, with no measurement behind it, that per-crossing cost under roughly #d.envelope_crossing_ms ms would keep overhead acceptable; a crossing costs #d.crossing_us µs, and it does so while marshalling typed values rather than opaque bytes. Prompt-injection attenuation held in exactly the form the vision claimed it — attenuation, not elimination — and the residual it warned about is the residual we measured.

Hierarchical composition is the case where the artifact was more generous than the prediction. The vision said composition "falls out naturally from the model"; that reads as optimism in a paper with nothing running behind it. It turned out to be accurate in a specific and checkable way: a sub-graph cannot provision authority of its own, not because a rule forbids it, but because the executor holds no backend to provision from. The confinement property we expected to have to enforce had no mechanism by which it could fail.

== What it substantiates only in part <sec:partial>

Three claims hold under restrictions the vision did not attach to them, and stating those restrictions is more useful than the claims.

*A node cannot exceed its declared capabilities* is true on the confined tier and false on the host tier, where a hostile node can read the filesystem, open a socket, or read the environment. The vision described capability injection as though enforcement followed from it; it does not. Enforcement follows from the *artifact*, and only nodes compiled to components get it. The host tier's escapes are recorded as passing tests and reported in @tab:tiers precisely so this does not read as universal.

*Nodes have no ambient authority* holds on the confined tier in a stronger sense than the vision articulated, and the distinction only became visible by building it twice. An earlier version confined nodes under an empty WASI context — genuinely confined, but the modules still *imported* `fd_write` and `path_open`, so confinement was a fact about the host's configuration that a misconfiguration would have silently revoked. The current components import no such function at all. "No ambient authority" turns out to name two different properties, and only the second is worth claiming.

*Implementations are interchangeable across languages* is demonstrated once, not established. `ParseMessage` was regenerated in Rust from the same signature and contract as its Python counterpart with the graph unchanged, which is a real instance of the property. One node is an existence proof, not a claim about the general case, and the contract-incompleteness problem (@sec:phase2) bounds what the general case could mean.

== What remains conditional <sec:conditional>

The type-system claims are untouched. No soundness argument connects well-typed wiring to noninterference; the two-point lattice is a first realisation, not a proof, and the choice between two-point, graded, and Jif-style decentralised labels @myers_decentralized_1997 is open. The vision's conditional mood for these claims was correct and is preserved verbatim in this paper rather than quietly upgraded — which is the single discipline most at risk in a rewrite of this kind, since every other section moved to the present tense around them.

User-level authorisation, on which the confused-deputy attenuation argument depends, remains undesigned. Behavioural contracts — the mechanism that is supposed to make generated implementations verifiable and interchangeable — have no language and no checker; the demonstrator has tests, which is not the same thing. CHERI integration is untouched, so enforcement stops at the WASM boundary. Replay, differential evaluation, agent tooling, and the visual editor were not attempted at all, and this paper offers no evidence about them in either direction.

== What building it revealed that the vision did not see <sec:revealed>

The most useful output of an implementation is the part of the design it corrects, and there are four.

*Revocation had an unnoticed prerequisite.* The vision listed capability revocation as an open problem and reached for the standard answer, caretaker indirection @miller_robust_2006. What it did not notice is that revoking a *specific* handle first requires a way to *name* one. The runtime's natural default provisions one handle per capability *type*, shared across every node declaring it, so there is no instance to revoke without severing every node at once. Capability *identity* had to become expressible in the graph source before revocation was even a well-posed operation. The vision listed the consequence and missed the prerequisite.

*Trust was one rule, not two.* The vision described edge type-compatibility and a trust-discharge check as separate obligations. Implementing them showed they are the same no-upward-coercion order applied in two places, and that treating them separately is what admits the laundering graph. This simplified the design rather than complicating it — a case where the artifact argued the vision into a cleaner position.

*Confinement is a property of an artifact or of a configuration, and the vision conflated them.* The distinction is drawn in @sec:sandbox-tier and its consequence recorded in @sec:partial; it is named again here because it is the clearest instance of a security claim that sounds identical in prose while naming two different guarantees, and only building it twice distinguished them.

*Composition is checked on the input side and unchecked on the output side.* The vision treated the union-alias convention for sub-graph outputs as the simplest of several designs and moved on. In the demonstrator it is the convention that is cheapest to adopt and hardest to verify: `ServiceOutcome` is asserted in the JSON to abbreviate the terminal types, and *nothing checks it* — the cross-graph analysis never examines the output side. That combination is a poor one for the property most worth checking, namely that a sub-graph's boundary type honestly describes what it emits. The gap is pinned by a test so it cannot be closed accidentally, and it is an argument for one of the alternative designs rather than for the convention.

= Related work <sec:related>

Each element of this work has been explored independently; the convergence that makes their synthesis newly practical is the argument of @sec:intro. To our knowledge, no existing system simultaneously provides graph-level capability analysis, trust-propagated type checking across component boundaries, and generated implementations executing within capability-restricted sandboxes; the security-by-construction property emerges from their combination, not from any element alone. This section is inherited from the founding vision @lavi_architecture_2026 with the additions the sharpened claim requires — principally the WASM Component Model's interface layer (@sec:sandboxing), which the confined tier of @sec:sandbox-tier is built directly on.

== Model-driven architecture and its lessons

The Object Management Group's Model-Driven Architecture (MDA) programme @omg_mda_2014, launched in 2001, pursued a superficially similar vision: models as the primary artifact, with code generated from them. MDA foundered on the round-trip engineering problem: models and generated code diverged as soon as developers edited the code directly, and keeping the two synchronised became more expensive than maintaining the code alone. This work avoids this failure mode structurally. The signal graph is not a model _of_ the code; it _is_ the program, at the level of abstraction humans review. Implementation code inside nodes is a generated artifact that can be regenerated without invalidating the graph, because the graph's type signatures and contracts (not the implementation) are the stable interface. There is no round-trip problem because there is no return trip: humans do not edit generated node implementations.

== Architectural modelling: C4 and its ecosystem <sec:c4>

The C4 model @brown_c4_2018 provides a hierarchical approach to software architecture visualisation across four levels of abstraction: Context, Containers, Components, and Code. It has become the most widely adopted lightweight architecture diagramming approach, supported by tools including Structurizr, LikeC4, IcePanel, and Mermaid.

Two recent developments extend C4 toward the role we envision. LikeC4 @likec4_2025 provides an MCP server that exposes the architecture model to AI agents as a queryable knowledge base, transforming static diagrams into an interactive substrate that agents can interrogate. Some practitioners, including the author @lavi_c4_skill_2025, have begun using C4 models as "executable context" for agents, maintaining the architecture model in the repository as the source of truth that constrains agent behaviour.

C4's limitation for our purposes is that it is a _communication_ model, not a _constraint_ model. It describes architecture but does not enforce it. This work replaces the C4 model with a typed signal graph that both describes and enforces; the diagram and the program are the same artifact.

== Effect systems and purity: Haskell, Idris, and beyond <sec:effects>

Haskell demonstrated that purity-by-default with explicit effects is practical for real software @peyton_jones_haskell_2003. The IO monad makes side effects visible in function signatures: a function of type `a → b` is guaranteed pure, while `a → IO b` declares that it performs effects. More recent work (algebraic effect systems as in Koka @leijen_type_2017 and Frank @lindley_be_2017, and dependent type systems as in Idris 2 @brady_idris_2021) makes this more expressive: effects can be parameterised, composed, and reasoned about as first-class values.

Roc @feldman_roc_2025 takes a different but relevant approach: it is a pure functional language in which all side effects are provided by an interchangeable "platform" that the application cannot bypass. A Roc application that targets a web server platform can handle HTTP requests but cannot access the filesystem; the platform boundary is the capability boundary. This is the closest existing language-level analogue to this work's per-node capability injection, though Roc operates at the whole-application level rather than per-component.

A more recent line of language research makes capabilities themselves the type-level currency for effects. Effekt @brachthauser_effects_2020 treats effect operations as _capabilities_: a function can perform only those effects for which it has been passed a capability value, and the type system tracks which capabilities are in scope — an approach its authors call lightweight effect polymorphism. Scala 3's capture checking @boruch-gruszecki_capturing_2023 generalises the idea: types record which capabilities a value _captures_, so a function's signature exposes the authority it may exercise. Both demonstrate that capability tracking can be made ergonomic inside a general-purpose type system, at function granularity within a single program.

This work applies this insight at the _architectural component level_ rather than the language type level. The granularity is coarser (components rather than functions), and the enforcement mechanism is the runtime rather than the compiler. But the principle is identical: effects are declared in signatures, not acquired from ambient context. The formal verification obligation described in @sec:agenda is, in part, the obligation to show that this coarser enforcement is sufficient for the security properties we claim.

== Content-addressed code: Unison <sec:unison>

Unison @chiusano_unison_2025 takes the position that text files are the wrong storage substrate for code from the outset. Definitions are identified by a hash of their abstract syntax tree rather than by name; the codebase is an append-only database of typed ASTs rather than a directory of files. The consequences are practically significant: the codebase is always in a type-checked state, incremental compilation is perfect (the same definition is never compiled twice), and semantically-aware version control eliminates entire classes of merge conflict. Unison also provides an algebraic effect system ("abilities") in which functions declare required effects in their type signatures, enforced by the type system, such that a program can only perform effects for which it has been explicitly given an ability. Version 1.0 was released in 2025, demonstrating that content-addressed, database-backed code storage is production-viable.

A related experiment is Darklang @biggar_darklang_2019, which attempted a holistic programming environment where code, editor, and infrastructure were unified: deployable directly from the structured editor with no separate build or deploy step. Darklang demonstrated genuine developer productivity gains for simple backend services but struggled with the adoption costs of a fully proprietary environment and the difficulty of scaling a bespoke infrastructure layer. Its trajectory is instructive: the vision of a unified, structured development substrate is compelling, but adoption requires either an incremental migration path from existing tools or such overwhelming productivity advantages that developers accept the switching cost. This work learns from this by treating the signal graph as a layer above existing runtimes (WASM, BEAM) rather than a replacement for them.

In a related vein, the Nix package manager @dolstra_purely_2006 and its sibling Guix demonstrate that content-addressed, capability-restricted computation is viable at scale in a different domain: software builds. Nix derivations are pure functions from declared inputs to outputs, with no ambient access to the network or filesystem during builds. The Nix store is a content-addressed database of build artifacts. The result is hermetic, reproducible builds across millions of packages. While Nix operates at the build level rather than the runtime level, it provides a large-scale existence proof that the capability-restricted, content-addressed computational model this work envisions is practical.

This work's treatment of node implementations as compiled artifacts derived from the signal graph is architecturally consistent with Unison's model at the implementation layer. The signal graph itself, however, operates at a different level: Unison's composition model addresses functions and libraries, while ours addresses explicitly wired capability topology. Similarly, Unison's ability system tracks _what category of effect_ a function performs but does not enforce fine-grained authority boundaries — the distinction between a handle scoped to a specific database versus ambient database access, or the propagation of `Untrusted<T>` trust labels. The two approaches are complementary: Unison addresses code storage and effect declaration; this work addresses architectural wiring and trust propagation.

== Live programming with typed holes: Hazel <sec:hazel>

Hazel @omar_hazelnut_2017 @omar_live_2019 is a live functional programming environment built around the principle that every editor state should be statically and dynamically meaningful, even when the program is incomplete. It achieves this through _typed holes_: missing or type-inconsistent expressions are wrapped in holes that carry type information and, in the dynamic semantics, propagate as opaque values through evaluation. The result is that feedback (type errors, live outputs, hole closure information) is available continuously during editing rather than only when a program is complete.

Hazel's relevance to the present work is twofold. First, it provides semantic foundations for the development workflow described in @sec:workflow: an agent proposing a graph transformation will, during the proposal phase, produce a partially-complete graph containing unfilled node signatures. Hazel's hole calculus demonstrates that such partial states can be given well-defined types and evaluated meaningfully, supporting the "project downstream effects" step of the workflow without requiring the entire graph to be complete before any inference is possible. Second, a 2024 paper from the Hazel group @blinn_statically_2024 integrates LLM code generation directly into the typed-hole environment, finding that providing the LLM with static context from the hole's type and typing environment substantially improves generation quality. This is a direct empirical precedent for the claim in @sec:workflow that agents generating node implementations benefit from the semantically rich context that the signal graph's type signatures provide.

== Process isolation and message passing: Erlang/BEAM <sec:beam>

The BEAM virtual machine @armstrong_making_2003, underlying Erlang and Elixir, provides the closest existing model to the runtime we envision. BEAM processes are lightweight, fully isolated (no shared memory), and communicate exclusively by message passing. A process cannot reach into another process's state or access global mutable resources. The "let it crash" philosophy, where individual processes fail and are restarted without system-wide impact, is a direct consequence of isolation.

More broadly, the signal graph's model of isolated components communicating by typed messages is an instance of the actor model @hewitt_universal_1973, and the resemblance to BEAM processes is not coincidental. However, the actor model as typically realised (Erlang, Akka, Orleans) leaves two things implicit: the set of messages an actor may _receive_ is visible in its interface, but the set of external resources it may _access_ is not, and the wiring between actors is determined at runtime by message sends rather than declared statically.

The closest existing prior art to this work's capability-typed composition is Pony @clebsch_deny_2015, which integrates _reference capabilities_ (iso, val, ref, box, trn, tag) directly into the actor-model type system and enforces data-race freedom at compile time. Pony demonstrates that capability annotations can be made first-class in a practical actor language and that the type system can carry them through composition — a validation of the general approach on which this work builds. The point of divergence is the target property: Pony's capabilities govern memory access patterns (aliasing, mutability), whereas the signal graph's capabilities govern external authority (database access, network calls, LLM invocation). The signal graph thus lifts Pony's insight from the memory-reference level to the architectural level, and pairs it with trust propagation and an explicit wiring graph.

This work extends the actor/BEAM insight in two ways. First, we make the message-passing interfaces typed and capability-aware: a component's signature declares not just what data it accepts but what capability objects it requires. Second, we make the wiring of components explicit in the signal graph rather than implicit in application code. The graph serves as a declarative analogue of the supervision tree, expressing component wiring at a level humans can reason about, though failure handling and restart policies require additional specification.

== Capability-based security <sec:capabilities>

The object-capability model @miller_robust_2006 @goos_paradigm_2003 holds that access to a resource requires possession of an unforgeable reference to that resource. Rather than checking permissions against an access control list, a capability system makes the capability itself the proof of authorisation. This model has been implemented at every level of the computing stack: in programming languages (the E language @miller_robust_2006, Google's Caja @google_caja_2012), in operating systems (Capsicum @watson_capsicum_2010, seL4 @klein_sel4_2009), and in runtime environments (Deno @deno_2025, WebAssembly/WASI).

The most directly relevant prior work for our purposes is the treatment of capability-passing in _distributed_ systems, where the additional concern is that network reachability can itself constitute ambient authority. Miller's E language @miller_robust_2006 addressed this by mediating all inter-object communication through explicit references passed through the object graph; no ambient network or global namespace is available. The Agoric platform @agoric_hardened_2023 extends this model to JavaScript through Hardened JavaScript (SES, Secure EcmaScript), demonstrating that object-capability (ocap) discipline is achievable in a mainstream language without requiring a new runtime. Stiegler's _An Introduction to E and the Distributed Object-Capability Model_ @stiegler_introduction_2010 provides an accessible treatment of the distributed case. Our signal graph's explicit edge wiring is the architectural-level analogue of E's reference passing: a node that is not wired to an external network capability handle would have no mechanism for external communication, regardless of the network services that exist at the operating system level — which the confined tier realises and the host tier does not (@sec:eval-tiers).

More recently, AWS's Cedar @cutler_cedar_2024 provides a formally verified authorisation policy language with a capability-aware structure, demonstrating that fine-grained, analysable authority models are viable in production cloud infrastructure. Cedar's approach (expressing policies as analysable programs rather than opaque access-control list (ACL) tables) is philosophically aligned with this work's treatment of capability wiring as a typed, reviewable artifact.

The combination of capability-based security with FRP's signal graph model is, to our knowledge, novel as a whole-system architectural substrate. Existing capability systems enforce authority restrictions at runtime; existing FRP systems enforce dataflow discipline at the type level. The synthesis enforces both simultaneously, making the two disciplines mutually reinforcing rather than independently applied; @sec:evaluation reports how far the demonstrator carries that.

== CHERI: capabilities in hardware <sec:cheri>

Capability Hardware Enhanced RISC Instructions (CHERI) @watson_cheri_2015 implements capability-based memory protection directly in hardware. On a CHERI processor, every pointer is a capability: a hardware-protected value carrying an address, bounds, permissions, and a tag bit checked on every memory operation. Capability forgery (via buffer overflow, type confusion, or integer-to-pointer cast) causes a hardware trap. No software guard is needed.

CHERI is reaching commercial maturity. Arm's Morello chip @arm_morello_2023 demonstrated CHERI on AArch64. Microsoft's CHERIoT @amar_cheriot_2023 adapted CHERI to RISC-V for embedded devices. Codasip @codasip_cheri_2024 has released commercial CHERI RISC-V processor IP. SCI Semiconductor announced the ICENI family, based on CHERIoT-Ibex on RISC-V, in 2024 @sci_iceni_2024 and reached first silicon in March 2026 @sci_first_silicon_2026 — which the company describes as the first commercial CHERI implementation in silicon. The CHERI Alliance @cheri_alliance_2024, with Google as a founding member, was established in 2024 to coordinate adoption.

Three CHERI properties matter for this work. First, _unforgeable capabilities_: a component that does not possess a capability to a memory region cannot acquire one through any means the processor permits. Second, _fine-grained compartmentalisation_: capabilities can be scoped to individual allocations, enabling component isolation within a single process at hardware speed. Third, _demonstrated low porting cost_: a 2021 study ported six million lines of C and C++ (KDE, Qt, X11) to CHERI with changes to 0.026% of source lines @capabilities_limited_cheri_2021. For AI-generated code targeting a CHERI-aware runtime from scratch, the porting cost would be zero (assuming the runtime itself has been ported, a one-time engineering effort). No part of this work has been run on CHERI hardware (@sec:phase3).

== Lightweight sandboxing <sec:sandboxing>

The practical feasibility of per-component isolation has improved dramatically. WebAssembly (WASM) provides capability-based isolation with near-native performance across languages @haas_bringing_2017. Two layers on top of it matter here, and it is worth keeping them distinct, because the substrate we depend on is the more durable of the two. The _WASM Component Model_ @w3c_component_model_2024 is the interface-type layer: components declare their imports and exports as typed interfaces (defined in the WIT interface-definition language), and the runtime links them with type-checked bindings. The _WebAssembly System Interface_ (WASI) is a standard _library_ of such interfaces — for filesystems, clocks, sockets, and the like — built on top of the Component Model. This distinction is directly relevant to the signal graph, and the correspondence is close enough to exploit directly: the proof-of-concept tier described in @sec:implementation expresses each capability kind as its own WIT interface, so that a node's `with` clause _is_ its component's import list and the runtime boundary is a realisation of the node's typed signature rather than a byte protocol beneath it.

WASI is itself a worked precedent for the pattern this work generalises. Its I/O model is explicitly capability-based: a component receives handles to the resources it may access at instantiation, with no ambient access to the host environment, and each such resource — `wasi:filesystem`, `wasi:clocks`, `wasi:sockets` — is a typed interface granted explicitly. That is structurally the same object as our `DBHandle<'knowledge-base', read>` or `LLMClient<inference>`, applied to host-system resources rather than application-level ones. The signal graph does not adopt WASI so much as it recognises WASI's capability interfaces as one instance of capability-as-interface, and extends the same discipline to the application capabilities WASI does not model.

The layering also settles a natural question about longevity, since WASI's interfaces are still in motion. WASI 0.1 (the POSIX-flavoured `wasm32-wasip1` snapshot) is legacy; WASI 0.2 rebased the standard onto the Component Model; WASI 0.3 @wasi_030_2026, ratified in mid-2026, added native async and _removed_ the `wasi:io` package entirely, folding it into the Component Model's canonical ABI; a long-term-stable WASI 1.0 is expected to follow @wasi_roadmap_2026. The interfaces churn — an artifact importing `wasi:io/streams` under 0.2 must migrate for 0.3 — but every version rebases onto the same underlying layer, the Component Model, which is the part advancing toward standardisation. The design consequence for this work is to bet on the substrate, not on any WASI snapshot: the proof-of-concept accordingly defines its own WIT capability interfaces rather than importing WASI's, and is untouched by that interface churn. Where a node genuinely needs a host resource, the corresponding WASI interface (at whatever version) is the right thing to grant it — as a capability, exactly like any other.

Where the guarantee lives is a related subtlety that the same layering clarifies, and it matters in practice. A `wasm32-wasip1` module still _imports_ WASI functions and is confined only because the host supplies an empty context behind them; confinement is then a property of the host's configuration. A component built without a WASI adapter does not import those functions at all, so its confinement is a property of the artifact — the distinction the confined tier of @sec:sandbox-tier is built to make, and the reason it targets a bare component rather than a WASI snapshot. Beyond WASM, Pydantic's Monty @pydantic_monty_2026, a minimal Python interpreter written in Rust, achieves microsecond-scale startup with complete host isolation by default; BEAM processes start in single-digit microseconds; and CHERIoT demonstrates hardware-enforced compartmentalisation with negligible overhead on resource-constrained devices.

CHERI hardware provides a backstop for software sandboxes: even if a sandbox implementation contains a memory safety bug, the hardware prevents capability forgery at the memory level. The result is two complementary enforcement layers (software sandbox and hardware capability), providing overlapping coverage with distinct failure modes.

== Durable execution and replay <sec:durable>

The snapshotting, replay, and time-travel debugging properties described in @sec:time have significant prior art in the durable execution paradigm. Temporal @temporal_2025, Restate @restate_2025, and Azure Durable Functions @microsoft_durable_functions_2025 provide production-grade infrastructure for persisting workflow state, replaying execution from event logs, and resuming after failure. These systems demonstrate that deterministic replay from logged events is practical at scale.

A persistent challenge for durable execution frameworks is nondeterministic interleaving: replay must reproduce the same ordering of concurrent operations that occurred in the original execution, or the replayed state diverges. Temporal addresses this by requiring orchestrator code to be deterministic; Restate uses a journal that records the outcome of each operation. Both approaches work but impose constraints on application code. The signal graph's pure, deterministic propagation semantics would avoid most of this class of problem at the inter-node level: signal propagation order would be determined by graph topology rather than by runtime scheduling, with one residual exception — the merge order at fan-in points, where several upstream nodes feed a single consumer — discussed under replay fidelity in @sec:agenda. Replay fidelity for nodes with internal concurrency or timing dependencies remains an open question (see @sec:agenda).

This work's replay model also differs in granularity and scope: durable execution frameworks replay at the _workflow step_ level, while the signal graph would replay at _capability boundary crossings_, which would provide a finer-grained and more complete record of system inputs. The signal graph also integrates replay with the type system's trust and capability annotations, enabling the replay infrastructure to enforce the same security properties as the live system. These production frameworks validate that event sourcing and deterministic replay are well-understood engineering.

== Spec-driven development <sec:sdd>

The SDD movement, represented by OpenSpec @fission_openspec_2025, GitHub's Spec Kit @github_spec_kit_2025, and AWS's Kiro @aws_kiro_2025, addresses the problem that AI coding agents are unpredictable when requirements live only in chat history. These frameworks create structured, versioned specification artifacts that persist in the repository and provide agents a stable context.

Codespeak @breslav_codespeak_2025, created by Kotlin designer Andrey Breslav, takes this further: developers maintain plain-English specifications that compile via LLM to Python, Go, or TypeScript, treating implementation code as a generated artifact. The framing — "maintain specs, not code" — is close to this work's treatment of node implementations as compiled artifacts derived from the signal graph. However, Codespeak's specifications are untyped prose without capability annotations or trust propagation, so the security-by-construction properties the signal graph provides are outside its scope.

Current SDD frameworks, including Codespeak, treat their spec artifacts and the architecture model as separate concerns. Their outputs are prose documents or natural-language specifications with limited formal structure. This work argues that as these frameworks mature, their output should converge with the signal graph: a proposed change is a transformation of the typed graph, not a separate markdown document. The distinction between "spec" and "architecture" dissolves when the graph is both.

A parallel development at a different level of technical sophistication supports this trajectory. Visual workflow automation platforms (Zapier @zapier_2025, Make.com @make_2025, and n8n @n8n_2025) have achieved mass adoption by letting non-developers build systems as directed graphs of triggers, actions, and conditional branches. n8n's AI Workflow Builder already implements the core interaction loop this work envisions at a higher level of abstraction: a user describes intent in natural language, the AI generates a graph (represented as JSON), and the user reviews and refines the result visually. At the developer-facing end of the same spectrum, agent-orchestration frameworks such as LangGraph @langchain_langgraph_2025 structure LLM applications themselves as explicit graphs of state transitions — a further sign that graph-shaped system definitions are becoming the working representation for AI-era software. These platforms validate the appetite for graph-based system construction and the viability of AI-generated graph definitions. Their limitation is the absence of the properties this work requires: typed interfaces, capability restrictions, trust propagation, and formal security guarantees. As teams scale from internal automations to customer-facing AI agents, the gap between workflow automation and production-grade architectural rigour becomes acute. That trajectory converges on the kind of typed, capability-aware graph substrate we propose.

= Research agenda <sec:agenda>

The demonstrator establishes that the graph-level analyses and capability confinement are implementable. It does not deliver the language, the proofs, or the tooling. This section sets out what remains, organised in three phases of increasing scope and a realistic dependency ordering: Phase 1 designs the language and its type system, Phase 2 hardens the result for meaningful deployment, and Phase 3 addresses the formal and hardware questions. Each item is an open problem, and where the demonstrator has narrowed one, the narrowing is stated so the remaining question is not overclaimed as smaller than it is.

== Phase 1: the language and its type system <sec:phase1>

*The signal graph language.* Design the capability-annotated signal graph language: its type system, its expression of trust tainting, its composition rules. The target is a language expressive enough to encode realistic system architectures while remaining amenable to visual rendering and agent manipulation. Arrowized FRP @nilsson_functional_2002 and algebraic effect systems @leijen_type_2017 are the primary formal references. A key decision is the degree of dependent typing required: Idris 2 or Agda for full expressiveness, or a more restricted system (a Haskell-like type system with phantom types for trust levels) for tractability. The demonstrator uses the restricted system; the Phase 3 verification work may require the full one.

*The trust lattice, and the conditions it must satisfy.* The demonstrator realises a two-point lattice `Untrusted ⊑ Trusted` with no upward coercion and discharge as the sole sanctioned upward move (@sec:validator). What remains open is the choice among two-point, graded (`Untrusted ⊑ Sanitised ⊑ Trusted`), and Jif-style decentralised-label @myers_decentralized_1997 designs. The condition any successor must meet can be stated concretely, and is worth stating because it is exactly what a locally-sound-but-non-compositional label system loses: the flow relation used by the wiring check (`required ⊑ provided`, with a node's output label a monotone function of the meet of its input labels) must be *transitive*, so that a path of individually well-typed edges is itself well-typed, and *monotone*, so that composing nodes cannot manufacture trust the parts did not have. Compositionality of noninterference follows from standard results in information-flow security #cite(<sabelfeld_language-based_2003>, supplement: [§5]), but the signal graph's wiring model must be shown to satisfy the conditions those results require — an adaptation, not a mechanical application. The two-point lattice satisfies both trivially, which is precisely why it is weak evidence for a richer one.

*Error handling, conditional flow, and fan-out.* The concrete graph demonstrates basic conditional routing and error routing, but real systems require richer patterns: fan-out to multiple consumers, error propagation chains, and fallback logic. Arrowized FRP provides combinators for choice and fan-out (`ArrowChoice`, `&&&`), but their integration with capability annotations and trust tainting has not been worked out. A graph language that cannot express "on payment failure, notify the user and log the error" without escaping to imperative code would not be viable.

*Node-local state.* Many real components need persistent local state between invocations: session caches, rate-limit counters, accumulated aggregations. In FRP, state is modelled through feedback loops and signal accumulators; the interaction between stateful combinators, capability annotations, and the deterministic replay property has not been analysed, and a node maintaining implicit internal state may violate the assumptions that enable the replay and verification claims. The language must define whether state is an explicit feedback edge, a stateful combinator, or a capability-mediated external store — and which choice preserves the security and replay properties.

*Hierarchical capability routing.* When a parent provisions a capability to a sub-graph, the sub-graph must route it to the internal nodes that require it, and only those. Three designs are visible: (i) a flat parameter list the parent matches by type, with internal fan-out by convention; (ii) named capability slots the parent binds explicitly; (iii) structural matching on capability types, routing handles automatically to every matching `with` clause. Option (i) is now settled *at the runtime* (@sec:subgraph), which is the narrowest available claim: it is implementable and sufficient to run the composition, not demonstrably the right choice. It is the option requiring no new language surface, which is why a demonstrator can reach it without prejudging the design — and a flat list matched by type is also exactly where aliasing ambiguity lives, which is the argument for (ii) or (iii). The demonstrator's per-node identity map (@sec:identity) resolves the *naming* step without committing to any of the three, and carries identity across a single composition level rather than an arbitrary hierarchy.

*Sub-graph output aggregation.* The dual problem at the output side is more open than the input side, and the demonstrator sharpened rather than settled it. When a sub-graph's terminals emit distinct types, the boundary must collapse them into the single type the parent declares. The options mirror the input side: (i) define the boundary output as the union of terminal types, so `ServiceOutcome = DeliveryConfirmation | EscalationTicket` is an alias and no aggregation node is required; (ii) declare named output ports the parent wires individually; (iii) introduce an explicit aggregation node inside the sub-graph. The demonstrator runs on (i) and shows exactly where it is thin: the language has no alias mechanism, so the relation between the name and the types it abbreviates is verified by nothing, and the cross-graph analysis never examines the output side at all. Option (i) is the cheapest to adopt and the hardest to verify, which is a poor combination for the property most worth checking. The multi-terminal case — where a run reaches several terminals and there is no single boundary value — is refused by the runtime rather than resolved, and is a design question, not an implementation detail.

*User-level authorisation threaded through capability injection.* The confused-deputy attenuation argument depends on user-scoped capabilities being bound at the graph boundary and propagated downstream as part of the injected handle. Whether capabilities carry an authenticated principal, whether they compose under delegation, and how sub-graph boundaries preserve the principal across composition are all undesigned. This matters because the graph-level security argument leans on capabilities being both scoped to a resource *and* bound to an authorised principal; a weak binding would undermine the confused-deputy and privilege-escalation claims of @sec:security.

*Graph evolution and type-system evolution.* When a node's signature changes, downstream consumers may break; the language must define compatibility rules for signature evolution and support versioned interfaces at sub-graph boundaries to enable independent team ownership. Distinctly, the type system will itself need to evolve — new trust levels, new capability kinds, refined subtyping — and migration of existing graphs across type-system versions, with preservation of verified properties, is an open problem the design should anticipate.

*Agent tooling and developer experience.* Build the workflow that takes a natural-language change description, proposes a graph transformation, generates node implementations, and submits them for automated verification, extending existing SDD tooling to operate on typed graph artifacts rather than prose. Alongside it, the visual graph editor and diff viewer: capability edge additions, trust boundary crossings, and sanitisation gaps must be visually salient. This is inseparable from *graph-scale comprehension*, which the demonstrator does nothing to address — the concrete example has nine nodes and real systems have hundreds. Hierarchical decomposition is the expected approach, but the interaction between hierarchical abstraction, capability wiring, and trust propagation across sub-graph boundaries has not been designed, and a type error deep in a sub-graph's wiring must produce an error message comprehensible at the level the developer is working at.

== Phase 2: hardening and deployment <sec:phase2>

*Shallow verification.* Develop tooling to confirm that generated node implementations satisfy their declared contracts — which first requires a contract language, of which the demonstrator has none. Three techniques cover complementary concerns. _Property-based testing_ establishes type-level invariants across random inputs; _contract testing_ checks node-local pre- and post-conditions on representative traces, giving concrete evidence for properties the static type system cannot express; and _architectural fitness functions_ @ford_building_2017 verify cross-cutting properties of the assembled graph — capability-scope constraints, trust-zone integrity, absence of forbidden wirings — that belong to the composition rather than any single node. The obligation is deliberately bounded: type conformance, contract satisfaction, and graph-level structural invariants, not arbitrary program-property verification.

*Contract incompleteness.* Bounding that work is a problem the demonstrator cannot reach but which limits the code-as-compiled-artifact claim directly. Contracts are partial specifications: two implementations can satisfy the same contract and still differ observably — in latency, in resource consumption, in which variant they emit on inputs the contract does not pin down. Regeneration can therefore change production behaviour within the slack the contract leaves, with no verification step failing. Tightening contracts narrows the slack at the cost of authoring burden and verification tractability. Characterising which classes of behavioural difference are operationally significant, and what contract discipline makes regeneration safe with respect to them, is open.

*Event log infrastructure and replay fidelity.* Design the structured event logging that capability boundary crossings produce automatically, define the formal conditions under which replay fidelity holds, and characterise the classes of failure that violate it. The assumption that a boundary event log is a complete and deterministic record holds for single-threaded deterministic nodes and degrades for nodes with internal concurrency or timing dependencies. Fan-in is the inter-node instance of the same problem: where several upstream nodes feed one consumer, arrival order is a scheduling artifact rather than a topological property, so the log must record the realised merge order and the runtime must reproduce it. Perfect replay is not the claim; materially better fidelity than conventional logging, with the failure classes characterised and managed, is.

*Migration path.* Design the incremental adoption route for existing systems. The minimal entry point is wrapping an existing service as an opaque node with a declared capability signature — a boundary describing what the service *does* without requiring internal restructuring, analogous to declaring a foreign function interface. Over time an opaque node can be decomposed into sub-nodes with narrower signatures. The two-tier composition of @sec:tiers is the demonstrator's evidence that such intermediate states are workable, and it also shows why naming the graduation honestly matters: opaque wrappers and host-tier nodes provide *architectural visibility* — their authority is explicit and reviewable — while the enforcement of @sec:eval-tiers applies only to nodes actually ported to the confined tier. The benefit curve is graduated: visibility at the first step, structural enforcement earned as wrappers are decomposed and confined.

*Covert channels.* A node granted a permitted capability can encode information into its legitimate outputs — the choice of query, the timing of invocations, the shape of emitted events — through channels the type system does not model. The `Untrusted<T>` discipline addresses explicit data flow, and noninterference results handle the class of flows the type system observes; general covert-channel elimination is a known-hard problem and is not a target. The pragmatic aim is characterisation: naming which channels the model closes, which it narrows, and which remain out of scope.

*Revocation and rotation, completed.* The demonstrator implements targeted, opt-in revocation and rotation on the host tier and carries revocation across to the confined tier (@sec:identity). Two parts remain: sandbox-tier *rotation* — re-pointing over the same typed boundary — and the graph-transformation or redeployment form of both operations, which is undesigned. This is operations-adjacent work that the migration story needs.

== Phase 3: formal foundations and hardware <sec:phase3>

*Type-system soundness.* The security properties of @sec:security depend entirely on the type system being sound: every well-typed graph must satisfy noninterference and capability confinement. This is the obligation the demonstrator most conspicuously does not discharge, and a soundness bug would propagate to every layer of the defence-in-depth stack, since the runtime's capability injection is configured by the type system's analysis. Before a mechanised proof for the core calculus, property-based testing of the type system itself — random graph generation with expected type errors, fuzzing of the wiring checker — is the cheap validation. A first slice of this runs today: the test suite generates random trust labellings over the two-point lattice and asserts that an edge is rejected on trust grounds exactly when it is an upward coercion. That is a worked instance of the discipline, not a substitute for it.

*Compilation correctness.* For the compilation from signal graph semantics to capability-restricted WASM, confirm that component boundaries, capability signatures, and trust annotations are preserved across the production boundary. This is a bounded correctness claim about a well-defined transformation, closer in kind to CompCert @leroy_formal_2009 than to general program verification — but CompCert took a decade. The realistic near-term target is a mechanised preservation proof for a simplified subset of the language, sufficient to validate the approach and identify the hard cases. The minimal set of invariants required to guarantee the security properties of @sec:security in the production runtime must be identified before the full scope is fixed.

*CHERI integration.* Design the mapping from architectural capabilities — typed handles injected at node boundaries — to CHERI hardware capabilities at the memory level, using CHERI's fine-grained compartmentalisation to enforce node isolation below the WASM boundary, and characterise graceful degradation on non-CHERI hardware. CHERIoT @amar_cheriot_2023 provides a reference architecture; the WASM Component Model's capability interfaces provide the natural software interface above which CHERI enforcement is applied. This is what would move the confined tier's enforcement from unforgeable-at-the-WASM-boundary to unforgeable-at-the-memory-level.

*Distributed authority.* The signal graph controls capability flow within a deployment, but a node wired to a network capability can communicate with any reachable service and potentially acquire authority out-of-band that the graph does not model. The E language @miller_robust_2006 and Agoric's Hardened JavaScript address this through reference-based communication discipline; this work inherits the same open question for the distributed case. Scoping to a single deployment boundary is the pragmatic approach for Phases 1 and 2; the distributed extension is a later research question.

= Threats to validity <sec:threats>

The demonstrator is small and the claim in @sec:claim was scoped to what it can carry. This section states the limits explicitly, because the failure mode of a paper like this one is not a false claim but a true claim read more broadly than it was made.

== Construct validity: what the corpus measures <sec:threat-construct>

*The corpus is curated, and counts are not coverage.* @tab:corpus reports that #ev.corpus.mutation_rejected of #ev.corpus.mutation_total unsafe wirings were rejected. That ratio is #d.mutations_caught_pct by construction: the corpus contains the mistakes we thought to write down, and we wrote down mistakes we expected the analyses to catch. A fully-caught curated corpus reads as a soundness proof unless it says otherwise, and it is not one. The honest reading is narrow — the analyses are implementable and catch the classes they target — and no claim is made that an uncaught class does not exist.

*Reason-class pinning mitigates but does not resolve this.* Requiring `launder_trust` to be caught by the trust lattice rather than by edge typing means the corpus cannot stay green while the mechanism under test quietly stops working. That is a real guard against rot, and it is why the pins exist. It says nothing about mistakes absent from the corpus.

*Two graphs, one domain.* Both canonical graphs describe an AI customer-support pipeline, chosen because untrusted input, graduated LLM access, and fine-grained capability distinctions are all visible in it. It is a domain selected to display the properties under test. Whether the analyses are as informative on graphs whose security structure is less legible is untested.

== Internal validity: the measurements <sec:threat-internal>

*The overhead figures are from one machine and a two-node slice.* They are wall-clock timings on #raw(ev.environment.platform), reported to establish an order of magnitude, not as portable benchmarks. The supported claim is that a crossing costs tens of microseconds and therefore sits well inside the asserted envelope — not the specific figure.

*The per-crossing cost is a differenced quantity, which is fragile.* It is derived by differencing two warm timings through one component, so any systematic cost landing in one term and not the other is charged directly to the boundary. That this is not hypothetical is the subject of @sec:eval-overhead: an earlier benchmark timed a single cold pass, which was enough to distort the figure by an order of magnitude.

*Instantiation and compilation costs are reported but not amortised.* The per-node instantiation cost is the tier's fixed price today; instance pooling would reduce it, and has not been implemented. Serialisation cost for complex types at node boundaries is not measured at all.

== External validity: scale and generalisation <sec:threat-external>

*Nine nodes, not hundreds.* The concrete graph has nine nodes and the composition graph three services. Every claim about reviewability, comprehension, and the graph being "visible at a glance" is made at that scale, and graph-scale comprehension is an unaddressed Phase 1 obligation (@sec:phase1). The visual programming and model-driven traditions supply ample evidence that this is where such systems become difficult, and the demonstrator offers no evidence that this one does not.

*Two nodes on the confined tier, not all of them.* The enforcement results of @sec:eval-tiers apply to nodes compiled to components. The rest run on the host tier, where the same escape attempts *succeed*. A reader who takes "the demonstrator confines nodes" as a property of the system rather than of the ported nodes has the wrong picture — the two-tier arrangement is a migration path, and the host tier's gap is its cost.

*A Python host and a proof-of-concept runtime.* There is no differential evaluation, no snapshotting, no production deployment, and no concurrent execution. The runtime propagates signals along an active path in a single thread.

== Threats to the security argument itself <sec:threat-security>

These are the limits most consequential for how the paper should be read.

*No soundness result.* Nothing here connects well-typed wiring to noninterference. The validator implements a lattice; it does not prove that graphs well-typed under that lattice have the property the lattice is supposed to deliver. Every security claim in this paper is therefore a claim about *what the implemented checks reject*, not about what a sound type system would guarantee.

*Enforcement stops at the WASM boundary.* Confinement on the confined tier is unforgeable at that boundary and not at the memory level. A sandbox escape via a `wasmtime` defect is out of scope, and CHERI remains a named follow-up rather than an implemented layer.

*The free-text residual is real and is not closed by anything here.* @tab:injection reports that adversarial text survives in a permitted field on the confined tier. That row is asserted deliberately so that stronger enforcement is not misread as a stronger claim. Prompt injection is attenuated — the blast radius drops from arbitrary tool execution to a bad lookup query — and what bounds it is the capability scope, not the type and not the sandbox.

*Covert channels and distributed authority are out of scope (@sec:phase2, @sec:phase3).* A node with a permitted capability can encode information in the timing, shape, or ordering of its legitimate outputs; a node with a network capability can in principle acquire authority out-of-band that the graph does not model. Neither is addressed.

*The output side of composition is unchecked.* A sub-graph node may declare any output type and no analysis will object (@sec:subgraph). This is a defect in the demonstrator rather than in the model, but any claim about composition being statically checked must be read as applying to the input side only.

== Threats from the method <sec:threat-method>

The demonstrator was implemented by an AI agent against author-directed specifications, and this paper was AI-drafted under the same direction (see the note on process). Two consequences deserve naming. An artifact and its evaluation produced by the same process risk agreeing with each other for reasons unrelated to the truth of the claim — which is the reason the evaluation harness pins verdicts *and reason classes* and fails the build on divergence, rather than reporting whatever it finds. And a paper drafted alongside the artifact it describes is exposed to drift between prose and code, which is why the figures in @sec:evaluation are interpolated from a build artifact rather than transcribed, and why the properties this paper asserts are, wherever practical, backed by tests in the repository rather than by sentences in the paper.

Neither measure substitutes for independent replication, which has not occurred.

= Conclusion <sec:conclusion>

The founding vision @lavi_architecture_2026 argued that AI coding agents had removed the historical obstacle to graph-based code representations, and that the opportunity this creates is not merely a better diagram but a substrate in which the architecture model, the security policy, and the program are one artifact. It made that argument with nothing running behind it, and hedged accordingly.

This paper reports the demonstrator built to test it. Unsafe wirings are rejected at assembly time, before any node runs, each by the analysis meant to catch it — including the laundering case that type-checks on every edge and is caught instead as a lattice violation. Node bodies compiled to WebAssembly components import exactly the capability interfaces their signatures declare and nothing else, so confinement is a property of the artifact rather than of the host's configuration; escape attempts that succeed on the host tier are refused there. A capability-boundary crossing costs #d.crossing_us µs, inside the envelope the vision asserted without evidence, while marshalling typed values rather than opaque bytes. Hierarchical composition executes, and a sub-graph cannot mint authority of its own because there is no mechanism by which it could.

The distance remaining is larger than the distance covered, and @sec:outcomes and @sec:threats are the parts of this paper we would most want read. No soundness argument connects well-typed wiring to noninterference; the corpus is curated, so its counts are evidence of implementability rather than of coverage; the host tier's escapes are a real gap that the two-tier arrangement makes transitional rather than acceptable; and prompt injection is attenuated, not eliminated — adversarial text still reaches the tool-capable node in a permitted field, and what bounds the damage is the capability scope. The contract language, the user-level authorisation binding, replay, the agent tooling, and CHERI enforcement are all untouched.

What the exercise most changed is the design rather than the confidence. Building it showed that trust checking and edge typing are one order rather than two, that revocation is not well-posed until capability *identity* is expressible in the graph source, that "no ambient authority" names two different guarantees of which only one is worth claiming, and that the cheapest convention for sub-graph outputs is the one hardest to verify. None of those corrections were visible from the vision paper's vantage point, and all of them came from the artifact arguing back. That is the case for the arrangement this research program uses — a frozen record of what was predicted, a living document reporting what was found, and an evaluation that fails the build when the two stop agreeing — as much as it is a case for the signal graph itself.

// Appendices

#set heading(numbering: none)

= Annex A: Areas for collaboration <sec:collaboration>

_This research program is an invitation. The synthesis it describes spans several domains that no single team is likely to cover. This annex identifies the expertise each phase requires, as a guide for potential collaborators._

== Phase 1: the language and type system

- *Type theory and functional programming:* algebraic type systems, arrowized FRP, algebraic effect systems. Experience with Haskell, Idris, or Agda. The signal graph's type system is the foundation; getting it wrong here propagates to every later phase.
- *Systems programming:* WASM Component Model and WASI toolchains, capability-based I/O models, runtime implementation in Rust or C++.
- *AI agent tooling:* structured agent workflows, tool use, MCP (Model Context Protocol).
- *Developer experience design:* visual graph editors, diff viewers, reviewer cognitive load. This is as important as the formal foundations.

== Phase 2: hardening

- *Formal methods:* property-based testing (QuickCheck, Hypothesis), contract testing, lightweight specification (TLA+, Alloy).
- *Distributed systems and observability:* structured logging, distributed tracing, causal ordering @lamport_time_1978, OpenTelemetry.
- *Security engineering:* capability-based security, supply chain threat models, prompt injection as an attack class.

== Phase 3: formal foundations

- *Proof assistants:* Coq or Lean 4 at theorem-proving level, for the bounded compilation correctness claim.
- *Computer architecture:* CHERI instruction set architecture (ISA) extensions, CHERIoT hardware-software co-design. The Cambridge CHERI group is the primary external knowledge source.

// Bibliography
#bibliography("/citations.bib", style: "ieee")
