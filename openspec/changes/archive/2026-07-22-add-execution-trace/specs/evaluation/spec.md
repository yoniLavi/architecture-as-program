## ADDED Requirements

### Requirement: The evaluation artifact includes canonical execution traces

The evaluation harness SHALL emit execution traces of the prompt-injection scenario on both enforcement tiers as part of its `dist/` outputs, and SHALL pin structural properties of those traces as regression guards in the established pinned-verdict style: at minimum, that the untrusted taint reaches the tool-capable node through a permitted field (the free-text residual) on the confined tier, and that the discharge node is the sole point where trust is raised. A divergence SHALL fail the build rather than rewrite the artifact.

#### Scenario: Canonical traces are emitted on build

- **WHEN** the evaluation harness runs
- **THEN** `dist/` contains schema-valid traces of the prompt-injection scenario for the host tier and the confined tier, alongside `evaluation.md` and `evaluation.json`

#### Scenario: The free-text residual is pinned in trace data

- **WHEN** the confined-tier injection trace no longer shows adversarial data reaching the tool-capable node through a permitted field, or shows trust raised anywhere but the declared discharge node
- **THEN** the build fails, so stronger enforcement cannot be silently misread as a stronger claim and trust discharge stays observably unique
