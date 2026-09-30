# Tasks

## 1. The derivation's negative control

- [x] 1.1 Add `NEGATIVE_CONTROLS` to `poc/evaluate.py`: `hostile_ungranted` held against
      `ParseMessage`'s `with` clause, pinned to over-grant exactly `aap:caps/kb-read`
- [x] 1.2 Add `check_controls()`; `run()` refuses to write the artifact if a control is
      not caught, or is caught for a different interface
- [x] 1.3 Report the control in `dist/evaluation.md` and `evaluation.json`, separate
      from the agreeing rows
- [x] 1.4 Tests: the real control is caught; a control that agrees fails the pin; a
      control caught on the wrong interface fails the pin

## 2. Paper 2

- [x] 2.1 Abstract and conclusion: scope the opening claim; `crossing_us` → `crossing_magnitude`
- [x] 2.2 §4.1: report the negative control, interpolated
- [x] 2.3 §6.2: CAmkES/capDL, conceding the stronger link and stating the difference
- [x] 2.4 §6.1: Language-Based Agent Control
- [x] 2.5 §6.6: McCann's purity gate and Wassette
- [x] 2.6 Date line; single-line title-block note so pandoc keeps its spaces

## 3. Paper 3

- [x] 3.1 Date line
- [x] 3.2 Lattice agenda item: Filament keeps the lattice user-defined

## 4. Records

- [x] 4.1 `citations.bib`: Klein et al. 2018, Kuz et al. 2010, Zhou et al. 2026, McCann 2026,
      Wassette, Filament
- [x] 4.2 `docs/PRIOR-ART.md`: debts resolved; new findings recorded
- [x] 4.3 `docs/ROADMAP.md` "Start here" refreshed
- [x] 4.4 Publication checklist and Zenodo metadata in this change directory
- [x] 4.5 `AGENTS.md` test count

## 5. Verification

- [x] 5.1 `make build`, `check-citations`, `check-freeze`, `check-hedges`, pre-commit green
- [x] 5.2 Rendered PDF/MD read at the changed passages
- [x] 5.3 `openspec validate prepare-paper-2-publication --strict`

## 6. Found in the doing

- [x] 6.1 Abstract: "only the latter survives a misconfigured deployment" referred to the host's
      configuration, which inverts the claim; now "the former"
- [x] 6.2 §6 opening: "generated implementations executing within capability-restricted sandboxes"
      implied the demonstrator generates bodies; "generated" removed
- [x] 6.3 `scripts/resolve-crossrefs.lua`: pandoc 3.11 parses a centred prose block as a `Div`,
      which the filter silently dropped, taking the living papers' process and corpus notes out of
      the Markdown and HTML. Now kept under an opt-in `keep-centred-notes` metadata flag that only
      Papers 2 and 3 set, so Paper 1's outputs are byte-identical to a build from the pre-change
      commit (checked for the Markdown, the HTML, and the PDF text)

## 6b. Found by the review rounds after the merge (30 September 2026)

- [x] 6.4 The injection refusal was a host-tier probe outside the reported run; it is now read
      from a run with a fooled model, on each tier, and pinned
- [x] 6.5 The tier table's host column was mostly literals and its confined denials could not
      have read otherwise; every host cell is now an attempt, and each confined denial is pinned
      to its discriminating error
- [x] 6.6 Assembly validated a graph alone, so the runtime executed compositions the
      cross-graph checks reject; it now validates a graph with every graph it executes
- [x] 6.7 `ungranted_imports` checks ambient imports against each node's clause; `wasi_imports`
      could not see a clock
- [x] 6.8 Capability narrowing disclosed as checked, not enforced (attenuation at the routing
      point is recorded in the ROADMAP as the next change for this paper)
- [x] 6.9 Spec deltas for `signal-graph-runtime`, `trust-typing`, and `evaluation`
- [x] 6.10 Trust laundering through a sum variant, through a type constructor, and across a
      composition boundary: the lattice is now checked per variant, deeply, and with trust
      kept at the boundary; `launder_trust_via_variant` pinned in the corpus
- [x] 6.11 A caller-supplied sub-graph is validated against its parent before it runs; a
      sub-graph node's `requires` is checked
- [x] 6.12 The tier table is pinned in the build (`check_escapes`), its ungranted and HTTP
      denials discriminate, and the demo prints the same pinned table
- [x] 6.13 The principal requirement stops claiming intersection-narrowing is implemented
- [x] 6.14 Name collisions no longer skip the cross-graph checks: graph names must be unique
      in a batch, a graph cannot contain a node of its own name, and a resolved sub-graph must
      carry its node's name
- [x] 6.15 The injection refusal pin requires each tier's own reason (a widened scope failed
      for a different reason and still passed); pins for the tier table, the discriminating
      denials and the refusal are shown firing in tests
- [x] 6.16 The paper discloses that trust enters only where a node declares it: what a handle
      returns is unlabelled, so indirect injection is invisible to the lattice (§7.4, §2.1,
      §6.1)
- [x] 6.17 The demo no longer reports the cross-graph case as a false failure
- [x] 6.18 A sink rule: a node holding a tool-scoped client may neither consume `Untrusted<_>`
      nor be declared a discharger (both passed before); capabilities may not appear in data
      positions (a handle passed along an edge passed before); contract paths cannot reach
      dunders. Corpus cases `launder_trust_by_declaration`, `untrusted_into_tool_node`,
      `delegate_via_edge` pinned
- [x] 6.19 The principal is recorded, not bound: six paper sites corrected and three hedge pins
      re-seeded deliberately (they had overshot in the overstating direction on 5 August)
- [x] 6.20 The trust-typing spec's direction corrected (discharge *raises* trust)
- [x] 6.21 The sink rule's bypass by narrowing closed (no tool client into an inference-only
      slot; `route_tool_into_inference_slot` pinned); reason classes identified by their own
      check's message and pinned by presence, so the sink rule cannot mask the lattice (a
      test removes the lattice and the pin fails); the prompt-injection row moved to
      *Partial* under §5.1's definition (the vision counted retrieved content as untrusted)
- [x] 6.22 A repeated role label in a sum hid its second variant from the edge check, and raw
      untrusted input reached the tool node; the parser now rejects it
      (`launder_via_duplicate_role` pinned). The narrowing check's message no longer carries
      the sink rule's phrase, so `route_tool_into_inference_slot` is attributed to the check
      that catches it; a test removes the sink rule and its own pins fail
- [x] 6.23 A whole-output edge from a labelled sum passed variant completeness but never fired
      (a policy violation swallowed silently); labelled boundary outputs, duplicate edges and
      cycles were accepted; a node could run twice. All rejected or refused now;
      `hide_branch_behind_whole_edge` pinned. The inspector screenshots regenerated (the paper
      figure showed three cases), with long case names wrapping at underscores. The corpus
      records which cases review found (`found_by_review`, interpolated in §4.2 and §7.1)
- [x] 6.24 A partly labelled sum hid its unlabelled variant from variant completeness, and the
      runtime dropped it silently; the parser rejects such a sum
      (`hide_branch_behind_unlabelled_variant` pinned) and the runtime refuses a value no edge
      carries. The user-level authorisation row moved from *Partial* to *Not attempted* (no
      authority decision consults the principal); rotation's scope stated beside its row; the
      schema proviso's hedge drops "unbounded" (the bounded question field carries the residual),
      re-seeding its pin
- [x] 6.25 §5 checked against Paper 1's text (round K): §1 no longer says the vision did not
      predict the derivation (it deferred it to a Phase 3 proof); the reworded "declared
      distribution" row restored to the vision's "complete and sole description" (Partial);
      rows added for predictions the table omitted (compilation preserves signatures,
      graduated migration, injection ill-typed, OS compartments, property-based testing;
      snapshotting joined to replay); the ambient-authority correction restated as the
      substrate's failure, not the sentence's, and the aggregation correction as the alias
      convention's; Fuchsia's component framework cited in §6.2
- [x] 6.26 The runtime chose its entry node by file order, so a validated gate listed after
      the node it guards was skipped and an unreached node never ran; a graph now has exactly
      one entry, the node no edge reaches, taking the boundary input (validator and runtime;
      `unreached_audit_node` pinned). A contract compared an `Enum` field raw against string
      literals, so membership over `intent` was always false and blamed the body; a member now
      compares as its value. §3.3.3 says "set membership" and that a postcondition cannot
      see which variant was emitted
- [x] 6.27 Round L: the `ServiceOutcome` correction reclassified as not counted (the artifact
      keeps the vision's union convention; the unchecked alias was the demonstrator's gap), so
      §5.2 reports two corrections; the identity/revocation/rotation row moved to *Partial*;
      row labels aligned with Paper 1 (trust annotations, Jif-style labels, "without a declared
      discharge"); the entry must take the boundary as its only data input; the HTTP
      allowlist refuses backslashes, userinfo, and non-HTTP schemes, and matches hosts
      case-insensitively
- [x] 6.28 Round M: the laundering row moved to *Partial* (its restriction is the one that makes
      the injection row Partial); §1.1 says the derivation fixes the *kinds* of authority. The
      harness now fails a mutation that carries a reason class it does not declare (`also`),
      after three mutations were found also leaving a node unreached; they are rewired to
      isolate their fault. The hedge guard ignores Typst comments, so a pinned passage cannot
      survive only inside one. §3.2.1 says the derivation compares interface names
- [x] 6.29 Round N (no major finding on either side; the review loop stops here): the hedge
      guard scans Typst comments properly (attached and nested); pruned mutations drop their
      layout entries, and an error no reason class claims now fails the evaluation; §4.2 marks
      where the review-found cases end; §6.2 says capDL's proof is refinement; §1.1 says which
      half of "by construction" is constructed; §4.4 names the misleading reply

## 7. Publication (handed over from `merge-and-condense-papers`, 30 September 2026)

- [ ] 7.1 Author's end-to-end read of the merged paper
- [ ] 7.2 Upload per `publication-checklist.md`, with *Continues* as the only relation to
      Paper 1
- [ ] 7.3 `openspec archive prepare-paper-2-publication --yes` (after ticking 7.1–7.2)
