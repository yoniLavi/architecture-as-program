## ADDED Requirements

### Requirement: A join's output trust is bounded by the meet of its inputs
A node joining several inputs SHALL be rejected if it emits an output more trusted than its least-trusted input, unless it is a declared discharger, so that one untrusted input among clean ones taints the output.

#### Scenario: One tainted input in a join
- **WHEN** a join takes two clean inputs and one `Untrusted<_>` input and declares a clean output without `discharges_trust`
- **THEN** validation rejects it as a trust-lattice violation, and the corpus case is pinned to that reason class

#### Scenario: A tainted join with a tainted output
- **WHEN** the same join declares an `Untrusted<_>` output
- **THEN** validation accepts it

### Requirement: A per-item map lifts trust element-wise
A per-item sub-graph node SHALL be validated element-wise, so that `List<Untrusted<T>>` maps to whatever the child graph declares for one element, and only a discharger inside the child can raise an element's trust.

#### Scenario: Laundering past the child
- **WHEN** a per-item node declares `List<Summary>` output while its child graph emits `Untrusted<Summary>` and holds no discharger
- **THEN** validation rejects it, pinned to the trust lattice or cross-graph signature class

## MODIFIED Requirements

### Requirement: Trust discharge is a declared, typed transformation
The type system SHALL permit raising trust only at a node explicitly declared as a discharger, and
SHALL treat discharge as producing a distinct output type rather than as silently dropping a label. A
node not declared as a discharger SHALL NOT emit a higher-trust output than its input.

#### Scenario: Only a declared discharger may lower trust
- **WHEN** a node consumes an `Untrusted<_>` input and emits a non-`Untrusted` output (raising the
  data's trust; the scenario's title predates the lattice's orientation)
- **THEN** the graph is well-typed only if that node is declared as a discharger
- **AND** the discharge yields a distinct refined type, so downstream nodes see the discharged type,
  not a relabelled original

#### Scenario: A tool-capable node is not a discharger and takes no untrusted input
- **WHEN** a node holding a tool-scoped client consumes `Untrusted<_>`, whether or not its outputs stay
  untrusted and whether or not it is declared a discharger
- **THEN** the graph is rejected
- **AND** A node holding a tool-scoped `LLMClient<[...]>` SHALL NOT be declared a discharger, and
  SHALL NOT consume `Untrusted<_>` input: untrusted data reaches a tool-capable node only after an
  upstream discharger.

#### Scenario: A tool-scoped client is not routed into an inference-only slot
- **WHEN** a parent routes an `LLMClient` into a sub-graph whose node declares it inference-only
- **THEN** A parent SHALL NOT route a tool-scoped client into a sub-graph's inference-only slot. The
  validator refuses it statically, so the sink rule, which reads declared clauses, sees every node that
  holds a tool client; the refusal does not rest on the routing point's attenuation, which would deliver
  only an inference view.
