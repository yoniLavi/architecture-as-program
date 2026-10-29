## ADDED Requirements

### Requirement: Text quoted out of context states a measurement's magnitude, not one run's value
The demonstrator paper's abstract and conclusion SHALL state a single-machine measurement as its
interpolated magnitude rather than as the value one run produced. Those passages are the ones
quoted without their evaluation section — an archive record takes the abstract verbatim — so a
per-run value there becomes a fixed claim that the next build contradicts. The per-run value
SHALL remain in the evaluation section, beside the environment that produced it.

#### Scenario: The abstract names a magnitude
- **WHEN** the abstract or conclusion refers to the capability-crossing cost
- **THEN** it interpolates the magnitude from the evaluation artifact, and the per-run value
  appears only in the evaluation section

### Requirement: A claim about what architecture models do not do is scoped against the strongest precedent
No living paper SHALL state as universal that architecture models do not constrain the artifacts
built from them. Where a paper makes that contrast, it SHALL scope it, and the related-work
section SHALL cite and distinguish the strongest known precedent in which an architecture
description does determine authority — currently seL4's CAmkES and capDL, whose correspondence
is proved rather than tested — stating where that precedent is the stronger result.

#### Scenario: The contrast is scoped and the precedent is cited
- **WHEN** a reader reads the demonstrator paper's abstract, conclusion, or related work
- **THEN** the claim that architecture models describe but do not constrain is scoped, and
  CAmkES/capDL is cited with the difference and its greater strength stated

## MODIFIED Requirements

### Requirement: No paper states that the artifact lacks a capability the artifact has
Every living paper SHALL describe the artifact's capabilities as they stand at build time, or
as they stood at a commit the paper names. A paper SHALL NOT state that the demonstrator lacks
a capability it has at the point the paper describes; where a capability exists but is weaker
than the corpus once anticipated, the paper SHALL state the *restriction* rather than the
absence.

A paper that names a commit SHALL say so once, where a reader orients, and SHALL name there
the capabilities built since that it does not report, so that its statements of absence read
as dated rather than current. This is how a paper reaches a fixed published state while the
repository keeps growing; it was adopted on 29 October 2026, when the demonstrator paper,
then awaiting publication, had been overtaken by work it does not report (node-local state,
fan-in, a generative contract mode, generated bodies at scale). The alternative, sweeping each
absence into a restriction, would have moved verdicts in the accounting on evidence the paper
does not present.

This closes the gap the corpus's other guards leave open. Interpolation prevents a *number*
from drifting and pinned verdicts prevent a *mechanism* from silently regressing, but a
sentence asserting an absence stays green forever after the thing is built. When a change adds
a capability, correcting every "the demonstrator has no X" claim in every living paper that
describes the artifact at build time is part of that change, not a later sweep.

This requirement rests on review and no check enforces it, which is recorded here because it
has already failed once undetected: the change that built principal binding left three passages
of the demonstrator paper (§2.3, and §2.5 twice, in its August 2026 numbering) calling the binding *undesigned*, and they were
found four days later by a tightening pass that had no mandate to look for them. The evaluation
harness guards only the *overstating* direction — a paper cannot claim what the artifact cannot
do, because the harness runs the artifact — and there is no artifact against which to decide
that a sentence understates. The sweep is therefore a step in any change that lands a
capability, and the absence of a check on it SHALL stay stated rather than assumed.

#### Scenario: A newly built capability is swept through the prose

- **WHEN** a change gives the artifact a capability a living paper previously described as
  absent, undesigned, or unbuilt, and that paper describes the artifact at build time
- **THEN** that change also replaces each such statement with the capability's actual
  restriction, in every such paper

#### Scenario: A paper dated to a commit

- **WHEN** a living paper names the commit it describes
- **THEN** it says so once, where a reader orients, and names the capabilities built since
  that it does not report
- **AND** its statements of absence and its accounting verdicts are read as of that commit

#### Scenario: An accounting verdict reflects the artifact

- **WHEN** the accounting records a prediction as *conditional* or *not attempted*
- **THEN** no evidence for that prediction exists in the artifact at the point the paper
  describes; a prediction the artifact has partial evidence for is recorded as *partial* with
  its restriction stated

#### Scenario: The understating direction is known to be unguarded

- **WHEN** the corpus's drift guards are described, in documentation or in a paper
- **THEN** the overstating direction is attributed to the evaluation harness and the
  understating direction to the per-change sweep, rather than both being left to look checked
