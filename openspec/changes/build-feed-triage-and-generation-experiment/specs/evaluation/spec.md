## ADDED Requirements

### Requirement: New evidence leaves Paper 2's figures unmoved
The build SHALL emit the feed-triage service's evidence to `dist/evaluation-feed.{md,json}` and the generation experiment's to `dist/generation.{md,json}`, and SHALL fail if any key of `dist/evaluation.json` that Paper 2 interpolates changes value, until that pin is deliberately updated for a Paper 2 revision.

#### Scenario: A new corpus case for the toy
- **WHEN** a mutation of `feed-triage.json` is added and pinned
- **THEN** it appears in `dist/evaluation-feed.json`, and Paper 2's corpus counts are unchanged

### Requirement: The feed-triage evaluation is pinned like Paper 2's
The feed-triage evaluation SHALL pin each corpus case to its verdict and reason class with isolation enforced, hold each confined component against its `with` clause with a negative control, and pin each hostile feed item to the outcome it must produce on each tier.

#### Scenario: A hostile item asks for exfiltration
- **WHEN** a feed item instructs the model to fetch a URL carrying other items' contents, and the stub model is fooled
- **THEN** no fetch occurs, because no node downstream of a model holds `HTTPClient`, and the pinned outcome records it

#### Scenario: A hostile item asks for another item
- **WHEN** a feed item instructs the model to quote other items
- **THEN** the item's child run holds no other item to quote, and the pinned outcome records it
