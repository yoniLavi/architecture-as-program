# Tasks

## 1. Must fix — the accounting and the interpolation discipline

- [x] 1.1 **(M1a)** Paper 3 `tab:outcomes`: move *Behavioural contracts constrain generated
      implementations* from `Conditional / —` to `Partial / contract layer`
- [x] 1.2 **(M1b)** Paper 3 `tab:outcomes`: move *User-level authorisation threaded through
      capability injection* from `Conditional / —` to `Partial / principal binding`
- [x] 1.3 **(M1c)** Paper 3 §3.2: "Three claims hold under restrictions" → five, with a
      paragraph each for the contract layer and the principal binding, restrictions stated
      sharply enough not to read generously
- [x] 1.4 **(M1d)** Paper 3 §3.3: drop contracts and user-level authorisation from the
      still-conditional list
- [x] 1.5 **(M1e)** Paper 3 §5.1 (`User-level authorisation…`): rewrite around what §3.4 of
      Paper 2 built; the open half is the *typed/static* form and attenuation
- [x] 1.6 **(M1f)** Paper 3 §5.2 (`Shallow verification`): "a contract language, of which the
      demonstrator has none" → the demonstrator has one; what is missing is verification
- [x] 1.7 **(M1g)** Paper 3 abstract: prose counts → seven / five / three / four; verify the
      sum is nineteen and that §6.1's "Nineteen claims" and the conclusion's "seven
      substantiated" still hold
- [x] 1.8 **(M2)** Paper 2: correct all five "no/absent/undesigned contract language"
      passages (§2.3, §2.4, §3 opening, §3.3.2, conclusion) against §3.5 and §7.5
- [x] 1.9 **(M3)** Paper 2 §4.1: remove the hand-typed "The two mutations"; cover all four
      mutations; fix "no third kind of mistake exists"

## 2. Should fix — argument and evidence

- [x] 2.1 **(S5a)** `poc/evaluate.py`: add a derive-and-compare block (per node: derived
      interfaces, actual imports, agreement) to `run()` and `serialise()`, pinned so a
      divergence fails the build; extend `render()` for `dist/evaluation.md`
- [x] 2.2 **(S5b)** `tests/test_poc_evaluate.py`: cover the new block and its pin
- [x] 2.3 **(S5c)** Paper 2 §4.4: add a table interpolating the derivation figures, so the
      lead result has evidence in the Evaluation section
- [x] 2.4 **(S4)** Paper 2: add the contract layer to §1.2 contributions and to §5
      ("Established"), so §3.5 is no longer an orphan
- [x] 2.5 **(S6)** Paper 2 §4.1 and §7.1: "unsafe wirings" → language covering the
      unevaluatable-contract case, which is not a wiring
- [x] 2.6 **(S7)** Paper 2 §2.4: `ServiceOutcome` names nothing in the artifact — state the
      spelled union at first mention
- [x] 2.7 **(S8)** Paper 2 §2.1: "AI agents generate the implementation of each node" →
      conditional, per §2's own stated convention and the conclusion
- [x] 2.8 **(S9)** Paper 2 §2.5: hedge the CHERI clause
- [x] 2.9 **(S10)** Paper 2 §7.3: cite the graph-tooling claim (Dagster, Airflow, Enso, …);
      add bib entries
- [x] 2.10 **(S11)** Paper 2 §3.7: trim the replay discussion of Paper 3's accounting
      framing ("does not move that verdict"); keep the technical granularity argument

## 3. Nice to have

- [x] 3.1 **(N1)** Paper 2 §4.4 typo: "the growth cost it no special case"
- [x] 3.2 **(N2)** Paper 2 §4.4: "The last two rows" hand-indexes `ev.tiers.escapes` — name
      the probes instead
- [x] 3.3 **(N3)** `papers/README.md` and `AGENTS.md`: Paper 2's citable PDF slug is
      `lavi-2026-confinement-by-construction.pdf`, per the Makefile
- [x] 3.4 **(N4)** `AGENTS.md`: the `ServiceOutcome` bullet says "Nothing checks that alias"
      — the check exists; and the Paper 2 structure list omits §3.5 (contracts)
- [x] 3.5 **(N6)** Paper 2 abstract: one paragraph break to reduce density

## 4. Gate

- [x] 4.1 `make build` green (tests, freeze guard, evaluation pins, both living papers)
- [x] 4.2 `scripts/check-citations.py` clean
- [x] 4.3 Consistency sweep: Paper 3's prose counts sum to nineteen and match
      `tab:outcomes`; no paper claims the artifact lacks a capability it has
- [ ] 4.4 **Not done — Paper 2's length.** The review's target is the low-to-mid 30s;
      Paper 2 went 40pp → 41pp. The §3.7 replay trim, the conclusion's de-duplicated
      "not established" paragraph, and two accounting-framing cuts in §3.4/§3.6 removed
      roughly 250 words, and the §4.1 derivation section, the §7.1 mapping-table
      limitation, and the contract corrections added roughly 700. Shedding a page needs
      ~450 more words, and the remaining redundancy sits in material the corpus's own
      rules protect (stated limitations, hedges) or in §2.5/§6.3, which need rewriting
      rather than trimming. This belongs in a dedicated tightening pass
      (`/tighten-proposal 2`), not in a review-fix change that is otherwise adding
      required evidence.
