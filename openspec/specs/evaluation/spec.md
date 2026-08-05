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

### Requirement: The overhead measurement is pinned to its order of magnitude
The evaluation harness SHALL pin the measured per-crossing cost to a band, and SHALL refuse to write
the evaluation artifact when a measurement falls outside it, rather than emitting a figure the papers'
stated magnitude contradicts. Because the excursions this guards against are transient, the harness
SHALL re-measure before treating one as real, and SHALL fail only on a sustained excursion.

The band SHALL be enforced where the artifact is written and not inside the run itself. The evaluation's
other pins guard properties of the code, which must hold wherever it runs; this one guards a measurement,
whose usability is a fact about the machine that took it, and a caller that publishes no figure SHALL NOT
be failed by a loaded machine.

The band's ceiling SHALL coincide with the boundary of the magnitude the papers state, so that no
measurement admitted by the band can name a different one.

#### Scenario: A contaminated measurement does not reach the artifact
- **WHEN** the per-crossing cost measures outside the band on every attempt
- **THEN** no evaluation artifact is written, and the failure names the band and says whether the
  likely cause is a loaded machine or a genuine change in the cost

#### Scenario: A transient excursion is retried rather than failing the build
- **WHEN** one measurement falls outside the band and a subsequent one falls inside it
- **THEN** the harness reports the measurement inside the band and the build proceeds

#### Scenario: A run that publishes no figure is unaffected by the band
- **WHEN** the evaluation is run by a test rather than to produce the artifact
- **THEN** an out-of-band measurement does not fail it

#### Scenario: Widening the band is a deliberate act
- **WHEN** the measured cost has genuinely moved out of the pinned band
- **THEN** the band is re-pinned deliberately, because the papers state the figure's magnitude and
  widening the band edits a claim

### Requirement: The evaluation emits the magnitude of every figure a paper states in prose
The evaluation harness SHALL emit, alongside a measured figure, the magnitude a paper states for it in
prose, derived from the same measurement. A magnitude is a claim about a measurement exactly as the
figure is, so it SHALL NOT be maintained by hand in a paper while the figure beside it is interpolated.

#### Scenario: The magnitude is derived, not transcribed
- **WHEN** the evaluation artifact's data is serialised
- **THEN** it carries the crossing cost's magnitude as a pre-formatted string derived from the same
  measurement as the figure

#### Scenario: The magnitude and the figure cannot disagree
- **WHEN** a paper states the crossing cost's magnitude and its value in the same document
- **THEN** both are interpolated from one run, and no admitted measurement makes them name different
  magnitudes
