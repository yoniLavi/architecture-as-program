# evaluation Specification

## Purpose
Define the evaluation the demonstrator must be able to show for itself: one reproducible, generated artifact
consolidating the graph-mutation corpus, the capability-boundary overhead, and the prompt-injection outcome
across both enforcement tiers — pinned so that a regression fails the build, and scoped so that a curated
corpus cannot be read as a soundness proof.
## Requirements
### Requirement: The demonstrator ships a reproducible evaluation artifact
The repository SHALL produce, as a build output, a reproducible evaluation artifact that consolidates the
demonstrator's evidence: the accept/reject verdicts of the graph-mutation corpus, the capability-boundary
overhead measurements, and the prompt-injection attenuation outcome across the host and sandbox enforcement
tiers. The artifact SHALL be generated from the existing corpus, benchmark, and demonstration rather than
hand-maintained, so its contents cannot drift from the code that produces them. The artifact SHALL state that
the corpus is curated and illustrative and SHALL report both tiers honestly, so it cannot be read as a
soundness proof or a stronger guarantee than the demonstrator provides.

#### Scenario: The evaluation artifact is generated on build
- **WHEN** the build runs
- **THEN** the evaluation artifact is produced from the corpus, benchmark, and demonstration
- **AND** it reports the corpus accept/reject counts, the overhead figures, and the host-vs-sandbox tier
  outcomes

#### Scenario: The artifact does not overclaim
- **WHEN** a reader consults the evaluation artifact
- **THEN** it states the corpus is curated and illustrative and reports the host tier's escapes as a recorded
  gap alongside the sandbox tier's confinement

### Requirement: The evaluation pins expected verdicts as a regression guard
The evaluation SHALL pin, for each mutation in the corpus, its expected verdict, and SHALL fail if the actual
verdict diverges, so the evaluation guards the demonstrator's central claims against regression rather than
merely reporting a snapshot.

#### Scenario: A divergent verdict fails the evaluation
- **WHEN** a mutation's actual verdict differs from its pinned expected verdict
- **THEN** the evaluation fails rather than emitting a passing report

### Requirement: The evaluation artifact includes canonical execution traces

The evaluation harness SHALL emit execution traces of the prompt-injection scenario on both enforcement tiers as part of its `dist/` outputs, and SHALL pin structural properties of those traces as regression guards in the established pinned-verdict style: at minimum, that the untrusted taint reaches the tool-capable node through a permitted field (the free-text residual) on the confined tier, and that the discharge node is the sole point where trust is raised. A divergence SHALL fail the build rather than rewrite the artifact.

#### Scenario: Canonical traces are emitted on build

- **WHEN** the evaluation harness runs
- **THEN** `dist/` contains schema-valid traces of the prompt-injection scenario for the host tier and the confined tier, alongside `evaluation.md` and `evaluation.json`

#### Scenario: The free-text residual is pinned in trace data

- **WHEN** the confined-tier injection trace no longer shows adversarial data reaching the tool-capable node through a permitted field, or shows trust raised anywhere but the declared discharge node
- **THEN** the build fails, so stronger enforcement cannot be silently misread as a stronger claim and trust discharge stays observably unique

### Requirement: Contract violations are a distinct pinned reason class
The evaluation harness SHALL treat a contract violation as its own reason class, distinct from an edge
type mismatch and from a trust-lattice violation, so that a corpus case pinned to a contract violation
cannot stay green if it begins to be caught by a different analysis.

#### Scenario: A contract case is pinned to its own reason class
- **WHEN** the corpus contains a case whose fault is a contract violation
- **THEN** the harness pins that reason class, and a divergence fails the build

### Requirement: The evaluation reports the graph-to-binary derivation as a pinned figure
The evaluation harness SHALL report, for each node ported to the confined tier, the interface
set derived from that node's `with` clause in the canonical graph, the interface set its built
component actually imports, and whether the two agree — and SHALL fail the build on any
divergence rather than emitting a passing report. This is the demonstrator's lead claim, so it
SHALL have evidence in the evaluation artifact and not only in the test suite.

#### Scenario: The derivation is reported per node

- **WHEN** the evaluation harness runs
- **THEN** the evaluation artifact reports, per ported node, the derived interface set, the
  actual import set, and their agreement

#### Scenario: An over-granting world fails the build

- **WHEN** a component imports an interface its node's `with` clause did not grant, or fails to
  import one the clause did grant
- **THEN** the evaluation fails, so an over-grant cannot ship as a passing figure
