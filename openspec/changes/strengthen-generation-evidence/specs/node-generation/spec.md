## ADDED Requirements

### Requirement: A registered run fixes its design before any trial
The generation harness SHALL refuse to run a registered run unless a registration naming its pretexts, cells, trial count and one primary outcome is committed and unmodified, and SHALL record that commit in every trial of the run.

#### Scenario: The registration is edited after trials began
- **WHEN** the registration file differs from its committed version
- **THEN** the harness refuses to run and names the difference

#### Scenario: A reader checks what was planned
- **WHEN** the report presents a registered run
- **THEN** it names the registration's commit, states the primary outcome first, and lists the secondary outcomes as registered

### Requirement: Post-hoc trials are never pooled with registered ones
The generation report SHALL present trials from an arm added after results were read in their own table, labelled as post hoc, and SHALL NOT combine their counts with those of a registered run.

#### Scenario: The same pretext appears in both
- **WHEN** a pretext was run post hoc and again in a registered run
- **THEN** the two sets of trials are reported side by side and not summed

### Requirement: The stated rule can be withheld
The harness SHALL be able to give a task that lists the node's interfaces without stating that the list is a limit, differing from the standard task in that sentence alone, so that compliance with a stated rule can be told apart from the absence of any reach.

#### Scenario: The two variants are compared
- **WHEN** the rule-stated and rule-withheld tasks for one node are generated
- **THEN** they differ in the sentence that states the rule and nowhere else

### Requirement: The harness runs at low priority by default
The generation harness SHALL lower its own scheduling priority, and that of every process it spawns, to the lowest the operating system offers unless explicitly told not to, and SHALL bound its parallelism, so that a long run does not degrade other work on the machine.

#### Scenario: A default run
- **WHEN** the harness starts a run without the opt-out flag
- **THEN** it and its child processes run at the lowest priority, and no more trials run at once than the default bound

### Requirement: A green body is compared with the body it replaces
For each generated body that passes the pipeline, the harness SHALL run it and the hand-written body on the inputs generated from the node's contract and report whether their outputs and effects are equal, as information that does not gate the trial.

#### Scenario: A body that calls a model
- **WHEN** a generated body and the hand-written one word their prompts differently
- **THEN** the comparison uses a model stand-in whose reply does not depend on prompt wording, so the difference reported is in what each body does with the reply

#### Scenario: A body differs and is green
- **WHEN** a generated body's output differs from the hand-written body's on some input
- **THEN** the trial stays green, and the report records that it differs and on which input
