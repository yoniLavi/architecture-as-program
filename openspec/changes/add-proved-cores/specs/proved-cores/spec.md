## ADDED Requirements

### Requirement: The gate owns every proved node's statement
For each proved node, the gate SHALL generate the theorem statement and its prose from the graph (the node's contract, its capability clause and its call budget) and pin both by hash; a proof SHALL be accepted only against that pinned statement.

#### Scenario: A contract changes
- **WHEN** a node's `ensures` is edited in the graph
- **THEN** its generated statement and prose change, and the old proof is refused until it is redone

### Requirement: The gate checks the compiled environment, not printed output
The gate SHALL build the proof in a sandbox with no network and no writes outside the build directory, SHALL confirm the compiled statements are unchanged after the build, and SHALL audit in a separate process that never elaborates the proof file.

#### Scenario: A proof file redefines the axiom report
- **WHEN** a proof file uses `macro_rules` to make `#print axioms` print a clean list over `sorry` proofs
- **THEN** the gate refuses it, naming `sorryAx`

#### Scenario: A proof file writes outside the build
- **WHEN** a proof file's `#eval` writes a file into the repository during the build
- **THEN** the write is denied and the gate refuses the proof

#### Scenario: A theorem of the wrong type
- **WHEN** the named theorem proves `True` instead of the pinned statement
- **THEN** the gate refuses it

### Requirement: A proved node's effects carry what its scope constrains
A proved core's effect log SHALL carry the value its capability scope constrains (a lookup's tool, a payment's payee), and its generated statement SHALL state that every effect lies within the granted scope.

#### Scenario: The tool-loop node
- **WHEN** GenerateResponse's statement is generated
- **THEN** it states that every lookup's tool is the granted one, for every model reply

### Requirement: A proved call bound narrows the declared budget
Where a node's proved call bound is smaller than its declared `Calls` budget, the runtime SHALL meter it at the proved bound; a proof SHALL never widen a declared budget.

#### Scenario: A proved bound below the declared budget
- **WHEN** a node declares `Calls<'5'>` and its proof bounds it at 3
- **THEN** the node runs under a meter of 3
