# paper-corpus

## ADDED Requirements

### Requirement: No paper states that the artifact lacks a capability the artifact has
Every living paper SHALL describe the artifact's capabilities as they stand at build time. A
paper SHALL NOT state that the demonstrator lacks a capability it has; where a capability
exists but is weaker than the corpus once anticipated, the paper SHALL state the *restriction*
rather than the absence.

This closes the gap the corpus's other guards leave open. Interpolation prevents a *number*
from drifting and pinned verdicts prevent a *mechanism* from silently regressing, but a
sentence asserting an absence stays green forever after the thing is built. When a change adds
a capability, correcting every "the demonstrator has no X" claim across both living papers is
part of that change, not a later sweep.

#### Scenario: A newly built capability is swept through the prose

- **WHEN** a change gives the artifact a capability a living paper previously described as
  absent, undesigned, or unbuilt
- **THEN** that change also replaces each such statement with the capability's actual
  restriction, in both living papers

#### Scenario: An accounting verdict reflects the artifact

- **WHEN** the accounting records a prediction as *conditional* or *not attempted*
- **THEN** no evidence for that prediction exists in the artifact at build time; a prediction
  the artifact has partial evidence for is recorded as *partial* with its restriction stated
