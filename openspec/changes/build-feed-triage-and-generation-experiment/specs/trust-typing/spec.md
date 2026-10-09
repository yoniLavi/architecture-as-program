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
