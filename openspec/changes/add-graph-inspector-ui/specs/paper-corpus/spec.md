## ADDED Requirements

### Requirement: The demonstrator paper reports the inspector without overclaiming the editor prediction

The demonstrator paper SHALL report the graph inspector in its implementation section and SHALL update the predictions-and-outcomes accounting to record the visual-editor/tooling prediction as at most **partially** substantiated, stating in the same passage that the inspector views and runs graphs but does not author them, and that graph authoring from the UI remains open in the research agenda. Any paper statement about the inspector's behavior SHALL correspond to a tested requirement of the `graph-inspector` capability.

#### Scenario: The verdict stays bounded

- **WHEN** the paper's §5 accounting describes the tooling prediction after the inspector lands
- **THEN** the verdict is partial, the inspector-not-editor restriction appears with it, and no passage upgrades the visual-editor prediction to substantiated

#### Scenario: Paper claims about the inspector are backed

- **WHEN** the paper asserts a behavior of the inspector (rendering from canonical sources, server-side execution, taint visibility)
- **THEN** that behavior is pinned by a requirement and test in the `graph-inspector` capability, in the same claims-backed-by-artifact discipline as §3 and §4
