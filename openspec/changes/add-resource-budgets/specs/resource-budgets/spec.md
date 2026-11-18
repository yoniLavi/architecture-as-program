## ADDED Requirements

### Requirement: A handle can carry a budget scope
The type grammar SHALL accept budget arguments (`Calls`, `Tokens`, `Requests`, `Bytes`) as trailing scope arguments on their handle kinds, and a budgeted handle SHALL be assignable only to a slot whose budget is at least as large.

#### Scenario: A child declares a smaller call budget
- **WHEN** a parent routes `LLMClient<inference, Calls<'5'>>` to a child slot declared `LLMClient<inference, Calls<'3'>>`
- **THEN** the composition validates

#### Scenario: A child declares a larger call budget
- **WHEN** a parent routes `LLMClient<inference, Calls<'3'>>` to a child slot declared `LLMClient<inference, Calls<'5'>>`
- **THEN** the validator rejects the composition as a widening

### Requirement: Budgets are metered, not copied, at composition
A child's budget SHALL draw on its parent's meter, so the calls, tokens, requests or bytes spent by a whole sub-graph never exceed the budget the parent was granted.

#### Scenario: The child spends the parent's budget
- **WHEN** a parent granted `Calls<'3'>` routes it to a child that makes four calls
- **THEN** the fourth call is refused with `BudgetExhausted`

### Requirement: Budget exhaustion is not a capability error
Exhaustion of any budget, including the existing `uses` counter, SHALL raise `BudgetExhausted`, which is not a `CapabilityError`. A resource failure, an incomplete host binding and an ungranted import SHALL each keep their own error.

#### Scenario: A spent counter is not a security fault
- **WHEN** a node exhausts its `uses` counter
- **THEN** the error raised is `BudgetExhausted`
- **AND** an `except CapabilityError` handler does not catch it

### Requirement: A confined node can run under a store budget
A node SHALL be able to declare a `budget` of fuel, memory and a deadline, enforced by the confined tier's engine, with every fuel figure stated together with its one-check-interval overshoot.

#### Scenario: A runaway guest is stopped
- **WHEN** a confined node that loops forever runs under a fuel budget
- **THEN** it is stopped and the error is classed as fuel exhaustion
- **AND** the fuel consumed exceeds the budget by at most one check interval
