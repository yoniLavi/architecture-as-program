// Document setup
#set document(
  title: "Architecture as Program: Capability-Injected, Model-Driven Software Development in the Age of AI Agents",
  author: ("Claude Opus 4.6", "Yoni Lavi"),
  date: datetime(year: 2026, month: 2, day: 1),
)
#set page(margin: 2.5cm, numbering: "1")
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true)

// Title block
#align(center)[
  #text(size: 16pt, weight: "bold")[
    Architecture as Program: Capability-Injected, Model-Driven Software Development in the Age of AI Agents
  ]
]

#align(center)[
  #grid(
    columns: 2,
    column-gutter: 5em,
    row-gutter: 0.5em,
    text(size: 12pt)[Claude Opus 4.6], text(size: 12pt)[Yoni Lavi],
    text(size: 10pt, style: "italic")[Anthropic], text(size: 10pt, style: "italic")[Codeliance],
  )
]

#align(center)[
  #text(size: 11pt)[February 2026]
]

#v(2em)

= The window that just opened <sec:window>

For thirty years, a small community of researchers pursued an idea that working software developers consistently rejected: that source code should be a structured graph, not text in files. Projectional editors, structure editors, model-driven architecture: the history of these efforts is a history of elegant ideas that foundered on a single obstacle: programmers prefer text editors, value syntactic flexibility for half-formed thoughts, and resist representations that constrain expression before intent is clear.

That obstacle has moved.

The rapid adoption of AI coding agents (Claude Code, Codex, Cursor, Windsurf) has introduced a new primary author of implementation code who has no preference for text. AI agents do not need syntactic flexibility for half-formed thoughts, do not benefit from the ability to write temporarily invalid code, and are not made more productive by the absence of structural constraints. What they do benefit from is semantically rich, machine-readable representations of intent that prevent entire categories of error before generation begins. The graph representation that human developers rejected may be precisely what agent-authored software requires.

At the same time, a parallel development has made this timely: the emergence of spec-driven development frameworks (OpenSpec, GitHub's Spec Kit, AWS's Kiro) that capture developer intent as structured artifacts before any code is written. These frameworks implicitly acknowledge that when AI agents write the code, the interesting artifact is the _intent_, not the implementation.

This proposal argues that these two trends (agents as primary code authors, and structured intent capture as primary human activity) converge on a new software development paradigm. In this paradigm, a _signal graph_ (a program written in a functional reactive style with explicitly typed capability boundaries) is simultaneously the architecture model and the source of truth. Code is a compiled artifact derived from it. Security is a structural property of the graph, not an aspiration enforced by review.

= The central thesis <sec:thesis>

We propose a development model with four interlocking properties.

*The signal graph as source of truth.* The primary artifact that humans author, review, and version-control is a functional reactive program: a directed graph in which every node is a pure function from time-varying typed inputs to time-varying typed outputs. This graph is simultaneously the architecture diagram, the specification, and the program. There is no separate model that _describes_ the implementation; the graph _is_ the implementation, at the level of abstraction humans reason about.

*Capabilities as injected parameters.* Every node in the signal graph is pure by default. Side effects (database access, network calls, LLM invocations, event emission) are not ambient authorities that code can reach for. They are typed capability objects injected into node signatures by the graph's wiring. A node with signature `(OrderRequest, DBHandle<'orders'>, EventEmitter<'order-events'>) → OrderConfirmation` can read and write orders and emit order events. It cannot do anything else, not because a policy prevents it, but because no other mechanism exists within its scope.

*Code as compiled artifact.* AI agents generate the implementation of each node to satisfy the behavioural contracts encoded in the graph's type signatures. The imperative code inside each node is an implementation detail, analogous to compiled bytecode. It can be regenerated, refactored, or rewritten without changing the system's meaning, provided it satisfies its contracts. Humans review graph transformations; they do not routinely review generated code.

*Security by construction.* Because capabilities are injected and the type system propagates trust annotations, security properties are structural invariants of the graph rather than aspirations enforced by code inspection. The class of vulnerabilities that depends on unintended data flow (injection attacks, prompt injection, privilege escalation through confused deputies) becomes not merely detectable but, in well-typed realisations, syntactically inexpressible.

= Functional reactive programming as the conceptual core <sec:frp>

The signal graph model is not a novel metaphor. It is a direct application of _functional reactive programming_ (FRP), a paradigm with a twenty-five-year research history, here elevated from a UI programming technique to a whole-system architectural substrate.

== FRP: a brief account <sec:frp-brief>

FRP was introduced by Elliott and Hudak in their 1997 paper _Functional Reactive Animation_ @elliott_functional_1997, which modelled interactive animations as pure functions over continuous time. The central abstractions are _behaviours_ (values that vary continuously over time) and _events_ (discrete occurrences at points in time). Programs are expressed as compositions of these abstractions, without explicit state mutation or callback registration. The semantics are denotational: a behaviour is literally a function `Time → Value`, giving the paradigm a clean mathematical foundation that supports equational reasoning unavailable in imperative or callback-driven styles.

Subsequent work refined the model. Wan and Hudak's _Functional Reactive Programming from First Principles_ @wan_functional_2000 introduced _arrowized FRP_, which makes signal _transformers_ (rather than signals themselves) the primary composable unit. This restriction prevents certain classes of space and time leak and, more importantly for our purposes, makes the interface of each transformer explicit in its type. A signal transformer with signature `SF a b` transforms a stream of `a` values into a stream of `b` values. This is the formal object we extend with capability annotation.

The most prominent early realisation of FRP principles for browser UIs was Elm @czaplicki_elm_2012, which enforced purity strictly, made all effects explicit and managed by the runtime, and eliminated runtime exceptions in well-typed programs. Elm subsequently pivoted away from explicit FRP in version 0.17 (2016); Czaplicki's own release notes were titled "Farewell to FRP," replacing signals with The Elm Architecture's subscription model. The design properties Elm demonstrated remain instructive even if the FRP substrate was removed. In the JavaScript ecosystem, the FRP lineage continued through RxJS (the Reactive Extensions for JavaScript), now one of the most widely deployed reactive libraries, and Cycle.js, which applied observable-based FRP more rigorously as a full application architecture rather than a utility library.

More recently, the FRP research community has explored _differential_ computation, evaluating only the graph nodes affected by a change. Differential dataflow @mcsherry_differential_2013, as implemented in Materialize and the DBSP framework @budiu_dbsp_2023, demonstrates that this is practical at database scale. Our proposal's claim that the signal graph can serve as a production substrate (not merely a development-time abstraction) depends on this line of work.

*A concrete illustration.* Consider a node that processes user-submitted text and passes it to an LLM with tool-calling access. In a conventional system, this is dangerous: if the submitted text contains adversarial instructions, the LLM may execute them using its tools. The vulnerability is not a bug in any individual component; it is an architectural property: the unintended flow from untrusted input to a privileged executor.

In the signal graph, the same scenario is expressed as two nodes. The first, `UserInputHandler`, has signature:

```
UserInputHandler : (RawHTTPRequest, DBHandle<'sessions'>) → Untrusted<UserMessage>
```

The second, `LLMOrchestrator`, has signature:

```
LLMOrchestrator : (SanitisedPrompt, LLMClient<tools>) → AgentResponse
```

A direct wiring from `UserInputHandler`'s output to `LLMOrchestrator`'s input is a _type error_: `Untrusted<UserMessage>` does not match `SanitisedPrompt`. The graph cannot be assembled without an explicit sanitisation node whose signature is `(Untrusted<UserMessage>) → SanitisedPrompt`, a node whose existence is visible in the architecture, whose implementation is subject to contract verification, and whose presence is required by the type system rather than by a policy document. The prompt injection vulnerability is not detected or prevented; it is _inexpressible_ in a well-typed graph.

== From UI programming to whole-system architecture <sec:frp-architecture>

The step from FRP as a UI technique to FRP as a whole-system architectural model requires two extensions that the existing literature does not fully address.

The first is _capability annotation_. Standard FRP treats effects as values managed by the runtime, but does not give them a fine-grained type structure that distinguishes, say, a read-only database handle from a read-write one, or a sanitised string from an untrusted one. The object-capability model @miller_robust_2006 provides the missing ingredient: capabilities are unforgeable typed references whose possession is the proof of authorisation. Combining FRP's signal graph semantics with the object-capability model's typed authority gives us signal graphs in which data-flow and capability-flow are both first-class, typed, and statically checkable.

The second is _trust tainting_. Data entering the graph from untrusted sources (user input, third-party API responses, LLM outputs) carries a type marker that propagates through signal transformations until it passes through an explicitly designated sanitisation node. This is analogous to taint tracking as studied in information-flow security @sabelfeld_language-based_2003, but expressed as ordinary type-level propagation rather than a separate analysis. A node that accepts `UntrustedInput<string>` and a node that accepts `LLMClient<tools>` cannot be directly wired; the type system prevents the combination. The graph topology enforces the security property; no separate analysis is required.

== Time as a structural dimension <sec:time>

In a conventional program, time is implicit: state changes in place, and its history is lost unless explicitly logged. In a signal graph, time is structural: every signal carries a history, and the system's behaviour at any point is a pure function of its input signals up to that point. This has immediate practical consequences.

Proposing a change to the system means forking the signal graph's timeline. An agent explores the fork, observing projected effects on downstream signals. If the exploration is satisfactory, the fork is merged into the main timeline; if not, it is discarded with no cleanup cost, because the fork is a value, not a mutation. The human review step is not a diff of two static models but a _behavioural comparison of two timelines_, including the agent's exploratory history and the projected downstream effects on dependent signals.

In production, this structural temporality doubles as observability infrastructure. Every crossing of a capability boundary (every database read, network call, or LLM invocation) is a typed, observable event. A structured log of these events is a complete record of the system's inputs. Given that log and a deterministic signal graph, the system's behaviour at any past point is fully reproducible. Debugging a production failure means replaying the event log in the development environment, reconstructing the exact timeline, and forking the failure point. The replay of the production event log _is_ the regression test; authoring it is not a separate step.

= Prior art: the pieces that exist <sec:prior-art>

Each element of this proposal has been explored independently. The contribution is the synthesis, made newly practical by AI agents.

== Architectural modelling: C4 and its ecosystem <sec:c4>

The C4 model @brown_c4_2018 provides a hierarchical approach to software architecture visualisation across four levels of abstraction: Context, Containers, Components, and Code. It has become the most widely adopted lightweight architecture diagramming approach, supported by tools including Structurizr, LikeC4, IcePanel, and Mermaid.

Two recent developments extend C4 toward the role we envision. LikeC4 provides an MCP server that exposes the architecture model to AI agents as a queryable knowledge base, transforming static diagrams into an interactive substrate that agents can interrogate. Practitioners are already using C4 models as "executable context" for agents, maintaining the architecture model in the repository as the source of truth that constrains agent behaviour.

C4's limitation for our purposes is that it is a _communication_ model, not a _constraint_ model. It describes architecture but does not enforce it. Our proposal replaces the C4 model with a typed signal graph that both describes and enforces; the diagram and the program are the same artifact.

== Effect systems and purity: Haskell, Idris, and beyond <sec:effects>

Haskell demonstrated that purity-by-default with explicit effects is practical for real software @peyton_jones_haskell_2003. The IO monad makes side effects visible in function signatures: a function of type `a → b` is guaranteed pure, while `a → IO b` declares that it performs effects. More recent work (algebraic effect systems as in Koka @leijen_type_2017 and Frank @lindley_be_2017, and dependent type systems as in Idris 2 @brady_idris_2021) makes this more expressive: effects can be parameterised, composed, and reasoned about as first-class values.

Our proposal applies this insight at the _architectural component level_ rather than the language type level. The granularity is coarser (components rather than functions), and the enforcement mechanism is the runtime rather than the compiler. But the principle is identical: effects are declared in signatures, not acquired from ambient context. The formal verification obligation described in @sec:agenda is, in part, the obligation to show that this coarser enforcement is sufficient for the security properties we claim.

== Content-addressed code: Unison <sec:unison>

Unison @chiusano_unison_2025 takes the position that text files are the wrong storage substrate for code from the outset. Definitions are identified by a hash of their abstract syntax tree rather than by name; the codebase is an append-only database of typed ASTs rather than a directory of files. The consequences are practically significant: the codebase is always in a type-checked state, incremental compilation is perfect (the same definition is never compiled twice), and semantically-aware version control eliminates entire classes of merge conflict. Unison also provides an algebraic effect system ("abilities") in which functions declare required effects in their type signatures, enforced by the type system, such that a program can only perform effects for which it has been explicitly given an ability.

Unison demonstrates that content-addressed, database-backed code storage is production-viable; version 1.0 was released in November 2025. Our proposal's treatment of node implementations as compiled artifacts derived from the signal graph, rather than source files, is architecturally consistent with Unison's model at the implementation layer. The signal graph itself, however, is not a concept Unison provides: Unison's composition model operates at the function and library level, not at the level of explicitly wired capability topology. Similarly, Unison's ability system tracks _what category of effect_ a function performs but does not enforce the fine-grained authority boundaries (the distinction between a handle scoped to a specific database versus ambient database access, or the propagation of `Untrusted<T>` trust labels) that the signal graph's capability model requires. The two approaches are complementary rather than alternatives: Unison addresses the code storage and effect declaration layers; our proposal addresses the architectural wiring and trust-propagation layers above them.

== Live programming with typed holes: Hazel <sec:hazel>

Hazel #cite(<omar_hazelnut_2017>) #cite(<omar_live_2019>) is a live functional programming environment built around the principle that every editor state should be statically and dynamically meaningful, even when the program is incomplete. It achieves this through _typed holes_: missing or type-inconsistent expressions are wrapped in holes that carry type information and, in the dynamic semantics, propagate as opaque values through evaluation. The result is that feedback (type errors, live outputs, hole closure information) is available continuously during editing rather than only when a program is complete.

Hazel's relevance to the present proposal is twofold. First, it provides semantic foundations for the development workflow described in @sec:workflow: an agent proposing a graph transformation will, during the proposal phase, produce a partially-complete graph containing unfilled node signatures. Hazel's hole calculus demonstrates that such partial states can be given well-defined types and evaluated meaningfully, supporting the "project downstream effects" step of the workflow without requiring the entire graph to be complete before any inference is possible. Second, a 2024 paper from the Hazel group @blinn_statically_2024 integrates LLM code generation directly into the typed-hole environment, finding that providing the LLM with static context from the hole's type and typing environment substantially improves generation quality. This is a direct empirical precedent for the claim in @sec:workflow that agents generating node implementations benefit from the semantically rich context that the signal graph's type signatures provide.

== Process isolation and message passing: Erlang/BEAM <sec:beam>

The BEAM virtual machine @armstrong_making_2003, underlying Erlang and Elixir, provides the closest existing model to the runtime we envision. BEAM processes are lightweight, fully isolated (no shared memory), and communicate exclusively by message passing. A process cannot reach into another process's state or access global mutable resources. The "let it crash" philosophy, where individual processes fail and are restarted without system-wide impact, is a direct consequence of isolation.

Our proposal extends the BEAM insight in two ways. First, we make the message-passing interfaces typed and capability-aware: a component's signature declares not just what data it accepts but what capability objects it requires. Second, we make the wiring of components explicit in the signal graph rather than implicit in application code. The graph _is_ the supervision tree, expressed at a level humans can reason about.

== Capability-based security <sec:capabilities>

The object-capability model #cite(<miller_robust_2006>) #cite(<goos_paradigm_2003>) holds that access to a resource requires possession of an unforgeable reference to that resource. Rather than checking permissions against an access control list, a capability system makes the capability itself the proof of authorisation. This model has been implemented at every level of the computing stack: in programming languages (the E language @miller_robust_2006, Caja), in operating systems (Capsicum @watson_capsicum_2010, seL4 @klein_sel4_2009), and in runtime environments (Deno's permission model, WebAssembly/WASI).

The most directly relevant prior work for our purposes is the treatment of capability-passing in _distributed_ systems, where the additional concern is that network reachability can itself constitute ambient authority, since a node that can send messages to an arbitrary network address is, in effect, a node with an ambient capability to reach any network service. Miller's E language @miller_robust_2006 addressed this by making all inter-object communication mediated by explicit references that must be passed through the object graph; no ambient network or global namespace is available. The Agoric platform @agoric_hardened_2023 extends this model to JavaScript through Hardened JavaScript (SES, Secure EcmaScript), demonstrating that ocap discipline is achievable in a mainstream language without requiring a new runtime. Stiegler's _An Introduction to E and the Distributed Object-Capability Model_ @stiegler_introduction_2010 provides an accessible treatment of the distributed case. Our signal graph's explicit edge wiring is the architectural-level analogue of E's reference passing: a node that is not wired to an external network capability handle has no mechanism for external communication, regardless of the network services that exist at the operating system level.

The combination of capability-based security with FRP's signal graph model is, to our knowledge, novel as a whole-system architectural substrate. Existing capability systems enforce authority restrictions at runtime; existing FRP systems enforce dataflow discipline at the type level. The synthesis enforces both simultaneously, making the two disciplines mutually reinforcing rather than independently applied.

== CHERI: capabilities in hardware <sec:cheri>

Capability Hardware Enhanced RISC Instructions (CHERI) @watson_cheri_2015 implements capability-based memory protection directly in hardware. On a CHERI processor, every pointer is a capability: a hardware-protected value carrying an address, bounds, permissions, and a tag bit checked on every memory operation. Capability forgery (via buffer overflow, type confusion, or integer-to-pointer cast) causes a hardware trap. No software guard is needed.

CHERI is reaching commercial maturity. Arm's Morello chip demonstrated CHERI on AArch64. Microsoft's CHERIoT @amar_cheriot_2023 adapted CHERI to RISC-V for embedded devices. Codasip and SCI have released commercial CHERI RISC-V processor IP. In 2025, Wyvern Global announced the WARP chipset, the first commercially available CHERI-native RISC-V platform. The CHERI Alliance, with Google as a founding member, was established to coordinate adoption.

Three CHERI properties matter for our proposal. First, _unforgeable capabilities_: a component that does not possess a capability to a memory region cannot acquire one through any means the processor permits. Second, _fine-grained compartmentalisation_: capabilities can be scoped to individual allocations, enabling component isolation within a single process at hardware speed. Third, _near-zero porting cost_: researchers ported six million lines of C and C++ to CHERI with changes to 0.026% of source lines @watson_cheri_2015. For AI-generated code targeting a CHERI-aware runtime from scratch, the porting cost is zero.

== Lightweight sandboxing <sec:sandboxing>

The practical feasibility of per-component isolation has improved dramatically. WebAssembly (WASM) and its system interface (WASI) provide capability-based isolation with near-native performance across languages @haas_bringing_2017. WASI's I/O model is explicitly capability-based: a WASM module receives handles to the resources it may access at instantiation, with no ambient access to the host environment. Pydantic's Monty, a minimal Python interpreter written in Rust, achieves sub-microsecond startup with complete host isolation by default. BEAM processes start in single-digit microseconds. CHERIoT demonstrates hardware-enforced compartmentalisation with negligible overhead on resource-constrained devices.

CHERI hardware provides a backstop for software sandboxes: even if a sandbox implementation contains a memory safety bug, the hardware prevents capability forgery at the memory level. Two independent enforcement layers (software sandbox and hardware capability), neither of which depends on the other's correctness.

== Spec-driven development <sec:sdd>

The SDD movement, represented by OpenSpec, GitHub's Spec Kit, and AWS's Kiro, addresses the problem that AI coding agents are unpredictable when requirements live only in chat history. These frameworks create structured, versioned specification artifacts that persist in the repository and provide agents a stable context.

Current SDD frameworks treat their spec artifacts and the architecture model as separate concerns. Their outputs are prose documents (`design.md`, `requirements.md`, `tasks.md`) with limited formal structure. Our proposal argues that as these frameworks mature, their output should converge with the signal graph: a proposed change is a transformation of the typed graph, not a separate markdown document. The distinction between "spec" and "architecture" dissolves when the graph is both.

= The proposed system <sec:system>

== The signal graph <sec:signal-graph>

The primary artifact is a version-controlled, typed signal graph with the following structure.

*Nodes* are pure functions with explicit signatures. A node's signature declares its typed input signals, its typed output signals, and its injected capability handles. No side effects are possible beyond calling methods on injected capabilities. A node with no capability handles in its signature is guaranteed pure by the type system; there is no ambient mechanism through which it could acquire authority.

*Edges* are typed signal connections between nodes. An edge from node A's output to node B's input is valid only if the types match. Capability handles are wired explicitly: the graph's toplevel wiring determines which nodes receive which capabilities. This wiring is the architecture's security policy, expressed as graph structure rather than prose.

*Trust annotations* propagate through the graph. Data entering from untrusted sources carries a type marker, `Untrusted<T>`, that is preserved through transformations unless explicitly discharged by a sanitisation node. The type system prevents `Untrusted<T>` from reaching a node that accepts only `T` without sanitisation. Prompt injection (the dangerous combination of `UntrustedInput` and `LLMClient<tools>` in the same node) is inexpressible: no well-typed wiring connects an untrusted source directly to an LLM-capable node.

An important open design question must be acknowledged here. The trust annotation scheme as described enforces the _local_ typing of individual nodes, but the full security guarantee requires that the _wiring_ also be checked; specifically, that a source classified as untrusted at the graph's edge cannot be connected to a node whose signature expects a clean `T`, bypassing the `Untrusted<T>` marker through a widening coercion. This is the standard coercion problem in information-flow type systems #cite(<sabelfeld_language-based_2003>, supplement: [§3]): local type correctness of nodes is necessary but not sufficient for noninterference; the type system must also enforce that the subtyping relation between `Untrusted<T>` and `T` is absent, or equivalently, that wiring compatibility checks are flow-sensitive with respect to trust levels. Several solutions exist in the literature (most directly, treating trust levels as _security labels_ in the style of Jif @myers_decentralized_1997 or imposing a lattice structure on trust types with no upward coercion), but the precise design for our graph wiring context is an open question that Phase 1 language design work must resolve. The proposal does not claim this problem is solved; it claims it is tractable and that the right place to solve it is in the type system, where the literature provides well-understood tools.

*Behavioural contracts* are attached to node signatures as pre- and postconditions. These are the specifications against which AI-generated implementations are verified, and the stable interface across which different implementations are interchangeable.

== The development workflow <sec:workflow>

+ *Intent capture.* A human describes a desired change in natural language. An SDD-style tool translates this into a proposed graph transformation: new nodes, new capability wirings, modified signatures or contracts.
+ *Graph review.* Humans review the diff as a visual graph change: new nodes highlighted, new capability edges marked, trust boundary crossings flagged. This review is simultaneously an architecture review, a security review, and a design review. The reviewer is approving a typed program transformation, not reading prose.
+ *Implementation.* AI agents generate code for each new or modified node, targeting the capability-restricted runtime. Each node is implemented in isolation: the agent receives the node's signature, its contracts, and the types of its inputs and outputs. It has no visibility into adjacent nodes' implementations.
+ *Verification.* Automated tooling confirms that implementations satisfy their contracts, that the assembled graph conforms to the declared types, and that no node exceeds its injected capabilities. Since the runtime enforces capability restrictions, verification is primarily structural (type-checking and contract satisfaction) rather than arbitrary dataflow analysis.
+ *Merge.* If verification passes, the graph transformation is merged. The human approved the graph diff; the machine confirmed conformance. No human code review of generated implementations is required.

== The runtime <sec:runtime>

Each node executes in a lightweight, capability-restricted sandbox (a WASM module, a Monty-style interpreter, or a BEAM-like process), ideally on CHERI hardware. Critical properties:

*No ambient authority.* A node cannot import libraries, access the filesystem, make network calls, or perform any side effect beyond calling methods on its injected capability objects. This is enforced by the absence of any mechanism, not by a policy guard.

*Defence in depth.* The type system prevents the graph from expressing forbidden capability grants. The runtime sandbox prevents generated code from exceeding its injected capabilities. The operating system compartmentalises processes with OS-level enforcement. On CHERI hardware, the processor prevents capability forgery at the memory level. No layer needs to be perfect, because each is enforced by an independent mechanism at the layer below.

*Language agnosticism.* WASM is the natural compilation target, supporting Rust, C, C++, Go, and Python (via interpreters such as Monty). The signal graph defines component interfaces using a language-neutral type system; the implementation language is an optimisation choice made by the AI agent, or specified by performance constraints in the node's contract.

*Snapshotting and resumption.* Nodes can be paused, serialised, and resumed, enabling durable execution, time-travel debugging, and the production replay loop described in @sec:time.

== Security properties <sec:security>

The capability-injection model provides security guarantees qualitatively different from those achievable by code review or runtime monitoring.

*Injection attacks.* SQL injection and command injection depend on untrusted input reaching an interpreter in executable form. In the signal graph, a SQL-executing capability accepts typed queries, not raw strings. `Untrusted<string>` cannot reach it without passing through a sanitisation node that produces a typed query. The pattern is inexpressible, not merely discouraged.

*Prompt injection.* The dangerous combination (untrusted input reaching an LLM that has access to powerful tools) requires a node that accepts both `Untrusted<string>` and `LLMClient<tools>`. No such node can appear in the graph without explicit sanitisation between the untrusted source and the LLM capability. The graph topology makes this visible as a structural property; static analysis confirms it without inspecting implementations.

*Supply chain attacks.* A third-party library used within a pure node has no capability objects. Even if it contains malicious code, it has no mechanism for I/O. On CHERI hardware, even a library that attempts to exploit a memory safety vulnerability to escape its sandbox cannot forge a capability to memory it was not granted. If a library update introduces a new capability requirement, this appears in the graph diff as a new capability edge, a visible, reviewable change.

*Privilege escalation.* A node cannot acquire capabilities it was not given. The graph is the complete and sole description of the system's capability distribution. On CHERI hardware, this guarantee extends to the memory level.

= Research agenda <sec:agenda>

The research agenda is organised in three phases of increasing scope, reflecting a realistic dependency ordering. Phase 1 produces a working demonstrator; Phase 2 hardens it for meaningful deployment; Phase 3 addresses the deeper formal and hardware integration questions.

== Phase 1: Core demonstrator <sec:phase1>

*Signal graph language and type system.* Design the capability-annotated signal graph language: its type system, its expression of trust tainting, its composition rules. The target is a language expressive enough to encode realistic system architectures while remaining amenable to visual rendering and agent manipulation. Arrowized FRP @wan_functional_2000 and algebraic effect systems @leijen_type_2017 are the primary formal references. A key design decision is the degree of dependent typing required: Idris 2 or Agda for full expressiveness, or a more restricted system (e.g., a Haskell-like type system with phantom types for trust levels) for tractability. The demonstrator uses the restricted system; the Phase 3 verification work may require the full one.

*Runtime prototype.* Implement a capability-restricted execution environment (initially WASM/WASI) that instantiates graph nodes with their injected capability objects and provides no ambient authority. Demonstrate that a node implementing a realistic workload (an HTTP handler with database access and LLM invocation) cannot exceed its declared capabilities, and that the security properties of @sec:security hold for a representative set of attack patterns.

*Agent tooling.* Build the AI agent workflow that takes a natural-language change description, proposes a graph transformation, generates node implementations, and submits for automated verification. This extends existing SDD tooling (OpenSpec, Kiro) to operate on typed graph artifacts rather than prose documents. The distinctive contribution is agents that reason about signal dependencies and project downstream effects of proposed changes before committing them.

*Developer experience.* Implement the visual graph editor and diff viewer. The primary human interface must make graph transformations reviewable without requiring users to read the underlying type system. Capability edge additions, trust boundary crossings, and sanitisation gaps must be visually salient.

== Phase 2: Hardening and deployment <sec:phase2>

*Shallow verification.* Develop automated tooling to confirm that AI-generated node implementations satisfy their declared contracts. This combines property-based testing, contract testing, and architectural fitness functions @ford_building_2017, applying existing techniques in a novel configuration. The verification obligation is deliberately bounded: checking type conformance and contract satisfaction, not verifying arbitrary program properties.

*Event log infrastructure.* Design the structured event logging that capability boundary crossings produce automatically. Define the formal conditions under which replay fidelity holds, characterise the classes of failure (primarily concurrency-dependent) that violate it, and design runtime conventions that maximise fidelity in practice.

*Migration path.* Design the incremental adoption route for existing systems: wrapping existing components in capability boundaries, progressively extracting and formalising the signal graph from existing architecture documentation, and incrementally strengthening runtime enforcement as the graph matures. This is the primary route to practical adoption and must be designed explicitly, with attention to intermediate states stable enough for production operation.

== Phase 3: Formal foundations and hardware <sec:phase3>

*Deep verification.* For the compilation from signal graph semantics to capability-restricted WASM, confirm that component boundaries, capability signatures, and trust annotations are preserved across the production boundary. This is a bounded correctness claim about a specific, well-defined transformation, closer in kind to CompCert @leroy_formal_2009 than to general program verification, but demanding nonetheless. Proof assistants in the tradition of Coq or Lean are the appropriate tools. The minimal set of invariants required to guarantee the security properties of @sec:security in the production runtime must be identified before the full verification work is scoped.

*CHERI integration.* Design the mapping from architectural capabilities (typed handles injected at node boundaries) to CHERI hardware capabilities at the memory level. Leverage CHERI's fine-grained compartmentalisation to enforce node isolation below the WASM boundary. Characterise graceful degradation on non-CHERI hardware. CHERIoT @amar_cheriot_2023 provides a reference architecture; the WASI capability model provides the natural software interface above which CHERI enforcement is applied.

= Why now <sec:why-now>

Every element of this proposal has existed in some form for years or decades. What makes the synthesis newly practical is the convergence of four developments.

*AI agents as code authors.* The primary author of implementation code is, for the first time, an entity with no preference for text and no resistance to structural constraints. This removes the thirty-year obstacle to graph-based code representations.

*Lightweight sandboxing.* WASM/WASI, Monty, and BEAM have made per-node capability-restricted execution practical at microsecond timescales. The performance overhead that made capability-based systems impractical a decade ago has largely disappeared.

*Capability hardware.* CHERI processors are reaching commercial availability, and RISC-V standardisation is underway. For the first time since the capability architectures of the 1970s, hardware that enforces unforgeable, bounded capabilities is becoming available for production use.

*Economic pressure.* Organisations adopting AI coding agents are discovering that unconstrained agents produce architectural drift, security vulnerabilities, and technical debt at unprecedented speed. The need for formal architectural constraints on agent-generated code is acute and growing, creating demand that did not exist when the underlying techniques were first developed.

The question is not whether software development will move toward model-driven, capability-restricted, agent-implemented systems, but whether the transition will be guided by deliberate design or emerge haphazardly from the collision of existing tools.

// Appendices

#set heading(numbering: none)

= Technical Note A: Open problems and known limitations <sec:open-problems>

_This note collects the technical questions that the proposal acknowledges but does not resolve. It is intended for technically specialist readers who may wish to engage with specific open problems._

*Compositionality of noninterference.* When two well-typed nodes are wired together, the composed system must inherit the noninterference properties of both. This does not follow automatically from local node typing; it requires that the trust label system be compositional in a specific sense. The result is well-established (compositionality of noninterference follows from standard results in information-flow security #cite(<sabelfeld_language-based_2003>, supplement: [§5])), but the signal graph wiring model must be shown to satisfy the conditions those results require. This is an obligation for the Phase 1 type system design, not an open research question, but it is worth stating explicitly so that the design work does not inadvertently introduce a label system that is locally sound but fails to compose.

*The coercion problem in trust-annotated wiring.* As discussed in @sec:signal-graph, the trust annotation scheme requires a flow-sensitive wiring type system (not merely local node typing) to guarantee noninterference. The precise design (security label lattice, absence of `Untrusted<T> <: T` subtyping, or a Jif-style label system) is an open design question for Phase 1. The problem is well-understood in the information-flow literature; the contribution is adapting it to the graph wiring context.

*Replay fidelity under concurrency.* The production replay loop described in @sec:time assumes that the event log at capability boundaries is a complete and deterministic record of the system's inputs. This holds for single-threaded deterministic nodes but degrades for nodes with internal concurrency or timing dependencies. The formal conditions under which replay fidelity holds, and the runtime conventions that maximise it, are open questions addressed in Phase 2. The claim is not that perfect replay is achievable, but that capability-boundary logging provides materially better fidelity than conventional logging, and that the classes of failure that violate fidelity can be characterised and managed.

*Compilation correctness scope.* The Phase 3 claim that the FRP-to-WASM compilation preserves capability signatures and trust annotations is a bounded verification obligation, but its exact scope must be defined before proof work begins. CompCert @leroy_formal_2009 is the appropriate precedent in terms of methodology, but took a decade of dedicated effort. The realistic near-term target is a mechanised proof of preservation for a simplified subset of the signal graph language, sufficient to validate the approach and identify the hard cases, rather than a full production-grade verified compiler.

*Distributed ambient authority.* The signal graph model controls capability flow within a deployment, but a node wired to a network capability handle can, in principle, communicate with any reachable service, potentially acquiring capabilities out-of-band that the graph does not model. The E language @miller_robust_2006 and Agoric's Hardened JavaScript address this through reference-based communication discipline; our proposal inherits the same open question for the distributed case. Scoping the system to a single deployment boundary for Phase 1 and Phase 2 is the pragmatic approach; the distributed extension is a later-phase research question.

= Annex B: Competencies required by phase <sec:competencies>

_This annex maps the research agenda's technical demands to the knowledge domains required at each phase._

== Phase 1: non-negotiable

_Functional programming and type theory._ The signal graph language design requires fluency with algebraic type systems, parametric polymorphism, and the formal treatment of effects. Practical experience with Haskell or a dependently-typed language (Idris, Agda) is the minimum baseline. Familiarity with the arrowized FRP and algebraic effect systems literature is required. Without this competency, the type system will fail to enforce the security properties it claims, and the failure may not surface until Phase 3 verification work exposes it.

_Systems programming._ WASM/WASI toolchain experience, familiarity with capability-based I/O models, and the ability to implement a lightweight runtime in Rust or C++ are required for the runtime prototype. The WASI standards process is active; tracking it is an ongoing responsibility.

_AI agent tooling._ Experience building structured agent workflows (tool use, multi-step pipelines, structured output) is required for the agent implementation component. Familiarity with MCP (Model Context Protocol) is directly applicable.

_Developer experience design._ The visual graph editor and diff viewer are as important as the formal foundations. Experience designing developer tools with attention to reviewer cognitive load and the ergonomics of typed graph manipulation is required. Poor design here undermines an otherwise sound architecture.

== Phase 2: additionally required

_Formal methods and property-based testing._ Familiarity with property-based testing frameworks (QuickCheck, Hypothesis, fast-check), contract testing, and at least one formal specification language (TLA+, Alloy) is needed for the shallow verification tooling.

_Distributed systems and observability._ Understanding of structured logging, distributed tracing, and the formal treatment of causality @lamport_time_1978 is required for the event log infrastructure. Production observability experience (OpenTelemetry) provides practical grounding.

_Security engineering._ Translating the formal security properties of @sec:security into a concrete threat model requires familiarity with capability-based security, supply chain attack patterns, and prompt injection as an attack class.

== Phase 3: specialist depth required

_Proof assistant expertise._ Fluency with Coq or Lean 4 at theorem-proving level is required for the compilation correctness work. The scope of the verification obligation should be tightly bounded (to capability signature and trust annotation preservation) before this work begins.

_Computer architecture and CHERI._ The CHERI integration work requires knowledge of the CHERI ISA extensions, CHERIoT's hardware-software co-design, and the CheriBSD/CHERI-Linux stacks. The CHERI research group at Cambridge is the primary external knowledge source.

// Bibliography
#bibliography("citations.bib", style: "ieee")
