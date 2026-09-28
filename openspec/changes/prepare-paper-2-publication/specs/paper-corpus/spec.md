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
