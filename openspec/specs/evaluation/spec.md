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

The band's ceiling SHALL be a decade boundary, so that no measurement the band admits names a magnitude
above the one the papers state. The band admits the upper half of the decade below as well, so the papers SHALL
interpolate whichever magnitude a run names rather than state one in their own hand.

The overhead SHALL be measured in CPU time, not wall-clock time: the CPU time of the measuring
thread for every call into a component, and the CPU time of the whole process for compilation,
which wasmtime spreads over worker threads. The machine that builds the corpus is shared and never
idle, and wall-clock time charges the time a measurement spent waiting for a core to whatever it
measured (decided 29 October 2026, when a build on a loaded machine read 83µs for a crossing that
reads ~25µs on a quiet one; thread CPU time on the same machine read ~50µs). CPU time does not
remove the slowdown of running on a contended core, so the band stays, and the artifact and the
papers SHALL name the clock.

#### Scenario: The benchmark runs on a loaded machine
- **WHEN** the overhead is measured while other work competes for the cores
- **THEN** the time the measuring thread spent waiting for a core is not charged to the boundary
- **AND** the artifact and the paper name the clock, and do not claim that contention has been
  removed from the figure

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

### Requirement: The derivation gate is shown rejecting a real binary
The evaluation harness SHALL hold at least one real, built component that imports an interface
its node's `with` clause does not grant against that clause, through the same derivation code
path as the agreeing rows, and SHALL pin both that it is caught and the interface it is caught
for. A gate that is only ever shown agreeing is indistinguishable from one that cannot fail, so
the failing direction SHALL have evidence from a real binary in the artifact and not only from a
constructed fixture in the test suite.

#### Scenario: The negative control is caught
- **WHEN** the evaluation harness runs
- **THEN** the negative control's component is reported as over-granting exactly its pinned
  interface, separately from the agreeing rows

#### Scenario: A negative control that stops being caught fails the build
- **WHEN** a negative control agrees with its `with` clause, or is caught for an interface other
  than the pinned one
- **THEN** the evaluation fails and no artifact is written

### Requirement: Every reported outcome is measured where it is reported, and could have read otherwise
The evaluation harness SHALL compute each reported outcome from the run, tier, and object the report
attributes it to, and not from a separate probe. It SHALL count a denial as evidence only when the denial's
detail is the discriminating one, the reason that could not appear had the attempt reached the host. An
outcome that could not have read otherwise on the machine that built it is not evidence, and SHALL fail the
build rather than be reported as a denial. Specifically:
- the prompt-injection refusal SHALL be read from a run of the reported graph on the reported tiers, with a
  model that demands the out-of-scope tool, and SHALL be pinned on each tier;
- each host-tier escape SHALL be an attempt the harness performs, not a literal;
- a confined filesystem or socket denial SHALL count only when the guest reports the operation unsupported,
  and an environment denial only while the harness has set the variable being read;
- an ungranted-capability denial SHALL count only for the capability failure, never for a resource failure,
  and only when it names the interface the component was built to over-grant; an off-allowlist denial only
  when it names the allowlist and the host;
- the injection refusal SHALL carry each tier's own reason (the host handle's scope check; the confined
  guest's report), so that a widened scope, which fails for another reason, is reported;
- the tier table SHALL be pinned in the build: a confined escape, or a host cell that stops escaping, fails
  it;
- the ambient-import figures SHALL be computed against each node's own `with` clause;
- each reason class SHALL be identified by its own check's message, and a case SHALL pin the class that
  must be *present* among its rejection's classes, so a second check firing on the same graph cannot mask
  a first that stopped firing (the sink rule once satisfied the lattice's signature, and the lattice could
  be removed with every laundering case still green).

#### Scenario: A denial for the wrong reason fails the build
- **WHEN** a confined escape probe is denied with a detail other than its discriminating one (for example,
  file not found or connection refused rather than unsupported)
- **THEN** the evaluation fails, and no artifact is written

#### Scenario: The injection refusal regresses on one tier
- **WHEN** a fooled model's out-of-scope tool call is not refused in the run on one of the tiers
- **THEN** the evaluation fails, rather than rendering a cross in the paper's table
