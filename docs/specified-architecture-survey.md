# Survey: specified architecture (S1–S4) — provers, agent-written proofs, resource bounds, edge contracts

Written 18 November 2026 for `openspec/changes/explore-specified-architecture`. House style
follows `docs/PRIOR-ART.md`: each entry says what the work is, cites it, and says **what
changes for us, or plainly that nothing does**. "Preprint" means arXiv with no peer-reviewed
venue shown on the page I read. **UNVERIFIED** marks anything I could not check against a
primary source. GitHub was unreachable for part of the session, so some release facts come
from project sites rather than release pages, and I say which.

**What a prover faces here.** I looked at two node crates (`poc/sandbox/rust/lib_send_money`,
`node_parse_message`) before reading anything else:
- Each body sits under `wit_bindgen::generate!` (wit-bindgen 0.59), a procedural macro. It
  generates canonical-ABI glue: unsafe pointer lowering and lifting, `export!`, and an `impl
  Guest`.
- Host calls such as `payments::send(..)` and `inference_llm::infer(..)` are generated
  extern functions.
- The banking library goes through `lib_common`, which is `serde_json::Value`, `Map` and
  `String` formatting throughout.
- The feed and support nodes are smaller. `ParseMessage` is a `match` on a lowered string, a
  hand-rolled tokenizer over `chars()`, and `take(512)`.

No tool surveyed below will verify the macro output or `serde_json`. Every route that works
starts by **extracting a pure core**: a function with no `wit_bindgen` and no `serde`, which
takes the model's reply and the other host results as ordinary arguments. The `run` shell then
calls that core and performs the effects. This is the main practical finding, and it applies
to every prover below.

---

## 1. Proof-carrying code

**Necula & Lee, *Safe Kernel Extensions Without Run-Time Checking*, OSDI 1996 (best paper).**
<https://www.usenix.org/conference/osdi-96/safe-kernel-extensions-without-run-time-checking>
- The code producer must supply a formal proof that the code obeys the consumer's safety
  policy, and the kernel checks the proof before running the code.
- They report a one-time validation cost of 1–3 ms.

**Necula, *Proof-Carrying Code*, POPL 1997**, pp. 106–119. DOI 10.1145/263699.263712
(title and author checked on Crossref).

**Appel, *Foundational Proof-Carrying Code*, LICS 2001.** DOI 10.1109/LICS.2001.932501
(checked on Crossref). It moves the trusted base out of the verification-condition
generator and the type system, down to a logic and the machine semantics.

**What changes for us.** The design note says "proof-carrying code", and the shape fits
exactly.
- **The roles map one-to-one.** The agent is the untrusted producer. The gate is the
  consumer. The certificate must be checkable without trusting whoever wrote it.
- **Two lessons follow for the gate.**
  1. The consumer must own the safety policy. In our terms, the gate, not the agent, derives
     the theorem statement from the graph's contract. If the agent writes the statement, the
     check is meaningless. This is the specification-gaming risk in §3.
  2. Necula-style PCC trusts its VC generator. Appel's FPCC exists because that trusted
     base held bugs. Our analogue is the Rust→prover translation: Aeneas/Charon, or Verus's
     own VC generation. The design note already lists it as trusted. FPCC is the citation
     for why that entry matters.
- **Lean and Verus differ here.** A Lean proof is a certificate in Necula's sense: an object
  a small kernel re-checks. A Verus "proof" is annotations, which the consumer re-checks by
  running all of Verus plus Z3. That is PCC-shaped, but with a much larger trusted base.

---

## 2. Rust verification tools

### Verus
- **What it is.** SMT-based (Z3) deductive verification of Rust. Specs and proofs are written
  in Rust syntax inside a `verus!{}` macro: `requires`/`ensures`, ghost and tracked (linear)
  state, `spec`/`proof`/`exec` modes.
- **Citations.**
  - Lattuada et al., *Verus: Verifying Rust Programs using Linear Ghost Types*, OOPSLA 2023
    (DOI 10.1145/3586037 resolves at the ACM DL; title not re-checked).
  - Lattuada, Hance, … Parno, *Verus: A Practical Foundation for Systems Verification*,
    SOSP 2024, DOI 10.1145/3694715.3695952 (checked on Crossref; Distinguished Artifact
    Award, per [MSR](https://www.microsoft.com/en-us/research/?p=1099821)).
- **Current release.** Weekly point releases. The latest stable is `0.2026.11.02.8bf68ee`,
  with a rolling pre-release `0.2026.11.17.a1e2bd6`
  ([releases](https://github.com/verus-lang/verus/releases)).
- **Install footprint.** `INSTALL.md` lists **prebuilt binaries for macOS 14 arm**: unzip,
  clear Gatekeeper, then run `./verus`, which asks for a specific pinned rustup toolchain
  (the example shows 1.86.0) ([INSTALL.md](https://github.com/verus-lang/verus/blob/main/INSTALL.md)).
  - **UNVERIFIED:** whether that pinned toolchain can build wit-bindgen 0.59's output. This
    matters only if the core lives in the same crate as the shell.
- **Library coverage.**
  - `Vec` and `String` have specs in `vstd` through `assume_specification`.
  - `String` is an external type with a few specified methods (`as_str`, `clone`, `eq`,
    `is_ascii`) ([vstd string.rs](https://docs.rs/crate/vstd/latest/source/string.rs),
    [vec.rs](https://docs.rs/crate/vstd/latest/source/std_specs/vec.rs)).
  - Closures go through `call_requires`/`call_ensures`. `Fn`/`FnOnce` are stronger than
    `FnMut` ([guide: exec closures](https://verus-lang.github.io/verus/guide/exec_closures.html)).
  - Host calls fit `#[verifier::external_body]` or `external_fn_specification`, which the
    guide lists as **assumptions**
    ([guide: TCB](https://verus-lang.github.io/verus/guide/tcb.html)).
  - The 2 November release notes mention tightening a `no-cheating` mode. The reference
    documents it only for `assume`.
    **UNVERIFIED** whether it rejects `external_body`
    ([attributes](https://verus-lang.github.io/verus/guide/reference-attributes.html)).
- **Official guidance on LLM-written proofs**
  ([guide](https://verus-lang.github.io/verus/guide/llmforverusproof.html)):
  - Claude Sonnet/Opus 4.5 "fill in proof annotations for most lemmas in existing Verus
    projects".
  - LLM proofs run 2–3× longer than human ones, and some runs cost "a few hundred dollars for
    one function".
  - Models struggle with inductive invariants and **"code produced by procedural macros"**.
  - Cheat detection is a diff-grep for `assume`/`admit`/`external_body`/`axiom`, plus
    spec-change detection that "requires parser support".
- **Industrial use** at Microsoft and Amazon. This comes from secondary summaries only
  (**UNVERIFIED**).

### Aeneas (with Charon), Rust → Lean 4
- **What it is.** Charon lowers safe Rust (from MIR) to LLBC. Aeneas then translates LLBC
  into a pure functional model. Lean and HOL4 are the "most mature" backends, beside F\* and
  Coq ([README](https://github.com/AeneasVerif/aeneas)). Specs and proofs are ordinary Lean
  theorems about the extracted functions, which return in a `Result` monad.
- **Citation.** Ho & Protzenko, *Aeneas: Rust Verification by Functional Translation*, ICFP
  2022 / PACMPL ([MSR page](https://www.microsoft.com/en-us/research/publication/aeneas-rust-verification-by-functional-translation/);
  DOI 10.1145/3547647 resolves at the ACM DL, title not re-checked). The README also cites an
  ICFP 2024 soundness result for its borrow checking.
- **Limits** ([README](https://github.com/AeneasVerif/aeneas),
  [intro](https://aeneasverif.github.io/aeneas)):
  - safe Rust only, so no `unsafe` and no concurrency;
  - no `return` inside nested loops, and no `break`/`continue` to an outer loop;
  - no generic instantiated with a mutable reference;
  - **function pointers and closures are "ongoing work"**; traits are supported;
  - std and dependency functions need hand-written models.

  A third-party tracker citing Charon issue #142 lists `dyn Trait` and *string literals*
  among unsupported features. That list is undated (**UNVERIFIED**, possibly stale), and if
  current it bites on `ParseMessage`'s `match` on `&str`.
- **Install.** OCaml 5 through opam, a Charon checkout pinned to `charon-pin` (built with
  rustup or Nix), and a Lean toolchain copied from `backends/lean` (README). There are no
  binary releases. This is heavier than Verus, and the Lean toolchain pin drifts.
- **Production use with AI provers.**
  - *Klaus, Conejero, Tolmach, A Rust-to-Lean Verification Pipeline with AI Provers: An
    Experience Report.* Accepted at the AIMACS workshop at CAV 2026
    ([arXiv:2605.30106](https://arxiv.org/abs/2605.30106)).
    - It verifies Plonky3/RISC Zero pieces, with Aristotle and Aleph closing some
      obligations.
    - It reports "toolchain drift" and "Aeneas/Hax extraction limits". The abstract gives
      **no aggregate success rate**.
  - *Ho, Fournet, Protzenko et al., Scaling Verification of Cryptographic Software with
    Aeneas, Rust, and Lean.* **Preprint**, September 2026
    ([arXiv:2609.15648](https://arxiv.org/abs/2609.15648)).
    - It verifies 16.7 KLOC of SymCrypt Rust (SHA-3, ML-KEM) with a 237 KLOC Lean
      development.
    - "Agents autonomously write formal proofs." The abstract gives no rate.
  - *Aegis / EasyProver*: Rust → Aeneas → Lean, 2,045 program pairs, 52.7% of 2,000
    statements proved in 30 minutes each. I found this **only in press summaries**
    ([aiweekly](https://aiweekly.co/alerts/easyprover-nears-saturation-on-lean-verification-benchmarks));
    the primary paper was not found. **UNVERIFIED.**

### hax (Cryspen)
- Rust → F\* (stable), Rocq (experimental) and Lean.
- **hax 0.4 (29 September 2026) replaced its Lean backend with Charon + Aeneas**; the old one
  survives as `legacy-lean` ([hax blog](https://hax.cryspen.com/blog/archive/2026/)).
- **What changes for us:** for Lean, hax is now a packaging of Aeneas, not an alternative.

### Kani
- **What it is.** A bit-precise bounded model checker (CBMC) for Rust, including `unsafe`.
- **Specs.** Experimental function contracts (`requires`/`ensures`), loop contracts,
  quantifiers and stubbing, which extend it to unbounded proofs.
- **Citation.** Delmas et al., *Kani: A Model Checker for Rust*, ASE 2026 Industry Showcase
  ([arXiv:2607.01504](https://arxiv.org/abs/2607.01504)). It reports "16,000 harnesses
  verified per code change" in the Rust std verification campaign.
- **Install.** `cargo install kani-verifier && cargo kani setup`, with a **prebuilt
  `aarch64-apple-darwin`** ([install guide](https://model-checking.github.io/kani/install-guide.html)).
  Current version number **UNVERIFIED**.
- **LLM results.**
  - KaPilot (Ant Group) generates Kani harnesses for unsafe Rust, DOI 10.1145/3832239. I saw
    no rate (**UNVERIFIED**).
  - HarnessLLM (**preprint**, [arXiv:2607.22161](https://arxiv.org/pdf/2607.22161)) reports
    82.67% first-round harness success. I did not confirm that it targets Kani
    (**UNVERIFIED**).
- **What changes for us.** Kani is the one tool that could check the *whole* compiled node,
  wit-bindgen glue included, because it handles `unsafe`. But its result is a model
  checker's verdict, not a certificate, and it is bounded unless contracts are added.
  - It is the natural **test oracle for the extraction step**: check that `run` and the
    extracted core agree on bounded inputs.
  - It is not the S3 gate.

### Creusot
- **What it is.** Deductive verification through Why3. Specs are written in Pearlite, a
  Rust-embedded spec language.
- **Citation.** Denis, Jourdan & Marché, ICFEM 2022, LNCS 13478
  ([HAL](https://hal.ccsd.cnrs.fr/LMF/hal-03737878v1)).
- **Status.** Monthly releases; latest **0.14.0, 13 October 2026**. 0.11.0 announced a
  VerifyThis 2026 win ([devlog](https://devlog.creusot.rs/)). It needs nightly Rust (the
  0.10.0 notes: `nightly-2026-01-29`).
- **LLM-written proofs:** I found no reported rates.

### Prusti
- **What it is.** Viper-based. Astrauskas, Müller, Poli & Summers, OOPSLA 2019
  ([Zenodo artifact](https://zenodo.org/records/3363914)).
- **Status unclear.** A July 2025 listing marks it "Not Maintained", and aggregators show
  commits into 2026. I could not reach GitHub to check. **UNVERIFIED.** I would not build on
  it.

**What changes for us (§2 overall).**
- **The candidates narrow to Verus or Aeneas/Lean**, with Kani as an oracle beside them.
  Creusot is viable, but has no LLM evidence and needs a nightly toolchain. Prusti is out.
- **Neither candidate will take the crates as they stand.**
  - Aeneas rejects `unsafe`, and the guide says Verus agents struggle on proc-macro output.
  - Both need the host calls stated as assumed specs, and those join the trusted base, as
    the design note already says.
- **Hence the pure-core extraction.**

---

## 3. LLM- and agent-written proofs: where things stand

All figures are as reported. They are **not comparable across benchmarks**.

**Verus**
- **AutoVerus.** Yang et al., OOPSLA 2025 ([arXiv:2409.13082](https://arxiv.org/abs/2409.13082v3)).
  It proves >90% of **Verus-Bench** (150 tasks), more than half within 30 s or 3 LLM calls.
- **SAFE.** Chen et al., *Automated Proof Generation for Rust Code via Self-Evolution*,
  ICLR 2025 ([proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/b2e20d7402c9985eae4ba924c65370a8-Abstract-Conference.html)).
  - A fine-tuned open model reaches 70.50% on a human-written benchmark, against GPT-4o's
    24.46% ([MSR](https://www.microsoft.com/en-us/research/publication/automated-proof-generation-for-rust-code-via-self-evolution/)).
  - With self-debugging, the arXiv version reports 79.14% on VerusBench.
- **VeruSAGE.** Yang, Neamtu, Hawblitzel, Lorch & Lu, **preprint**
  ([arXiv:2512.18436](https://arxiv.org/abs/2512.18436)).
  - **VeruSAGE-Bench** has 849 proof tasks from eight Verus-verified systems. The best
    agent/LLM pairing solves >80% of them, at ~7.2 min per task.
  - It also completes >90% of a set of proof tasks human experts had not yet finished.
- **VeruSyn.** Di et al., **preprint** ([arXiv:2602.04910](https://arxiv.org/abs/2602.04910)).
  6.9M synthesised Verus programs. A fine-tuned Qwen2.5-Coder-32B is "favourable" against
  Claude Sonnet 4.5 on cost versus quality.
- **Rust-Prover.** Serbanuta, Xu, Stefanescu & Radoi, *Solving VeriContest with a
  Lean-Backed Rust Verifier*, **preprint**, October 2026
  ([arXiv:2610.03994](https://arxiv.org/abs/2610.03994)).
  - It translates **Verus specs plus the Rust code into Lean** (its own translator, not
    Aeneas). Agents prove the theorems, and the Lean kernel checks them.
  - Results:
    - All 1,325 theorems of 1,007 VeriContest problems are proved.
    - 1,259 come from one sub-32-hour run on Claude Opus 5.5, at a median of 3.2 min and
      $1.17 per proof.
    - The Lean translations match Rust on all 21,413 test cases.
    - The benchmark's own Verus first-attempt rate was 13.95%.
  - This is the strongest data point yet for "Lean as the proof language for Rust, written
    by agents", but it comes from one group with its own translator, and is unreviewed.

**Lean and Dafny verified-code benchmarks**
- **VERINA.** Ye et al., ICML 2025; revised version at ICLR 2026
  ([arXiv:2505.23135](https://arxiv.org/pdf/2505.23135)).
  - 189 Lean tasks.
  - Best single-trial rates: o3 reaches 72.6% correct code, 52.3% sound-and-complete specs,
    and **4.9% proofs**. With Lean feedback, o4-mini reaches 22.2% proofs at pass@64 on the
    basic subset.
  - The paper's conclusion: proof is the bottleneck.
- **Vericoding benchmark.** Bursuc, … Tegmark, **preprint**
  ([arXiv:2509.22908](https://arxiv.org/abs/2509.22908)).
  - 12,504 specs.
  - Off-the-shelf success: **Dafny 82%, Verus 44%, Lean 27%.**
- **FVAPPS.** Dougherty & Mehta, **preprint**
  ([arXiv:2502.05714](https://arxiv.org/pdf/2502.05714)). 4,715 Lean samples. Sonnet proves
  30% and Gemini 18% of 406 theorems. VERINA criticises it for LLM-generated specs with no
  human validation.
- **miniCodeProps.** Lohn & Welleck, NeurIPS 2024 SafeGenAI workshop
  ([arXiv:2406.11915](https://arxiv.org/pdf/2406.11915)). About 25% in v1. v2 says provers
  "fail to prove nearly all of the medium and hard properties".
- **Clover.** Sun, Sheng, Padon & Barrett, SAIV 2024, DOI 10.1007/978-3-031-65112-0_7
  ([abstract](https://theory.stanford.edu/~barrett/pubs/SSP+24-abstract.html)).
  - A Dafny consistency checker across code, spec and docstring, accepting up to 87% of
    correct instances.
  - It reports zero false positives on adversarial incorrect programs, and found 6 wrong
    programs in MBPP-DFY-50.

**Lean theorem proving (mathematics), for calibration only**
- DeepSeek-Prover-V2: 88.9% on miniF2F-test at pass@8192, 49/658 PutnamBench
  ([arXiv:2504.21801](https://arxiv.org/abs/2504.21801)).
- Kimina-Prover Preview: 80.7% at pass@8192
  ([arXiv:2504.11354](https://export.arxiv.org/abs/2504.11354)).
- Goedel-Prover-V2, ICLR 2026: 32B model 88.1% at pass@32 (90.4% with self-correction),
  86 PutnamBench at pass@184
  ([arXiv:2508.03613](https://arxiv.org/pdf/2508.03613)).
- Seed-Prover, **preprint**: miniF2F 99.6%, PutnamBench 331/657, 5/6 of IMO 2025
  ([arXiv:2507.23726](https://www.arxiv.org/abs/2507.23726)).
- Aristotle (Harmonic), **preprint**: formally verified Lean solutions to 5/6 of IMO 2025
  ([arXiv:2510.01346](https://arxiv.org/abs/2510.01346)).
- AlphaProof, Hubert et al., *Nature*, November 2025: IMO 2024 silver level with
  AlphaGeometry 2 ([Google Research](https://research.google/pubs/olympiad-level-formal-mathematical-reasoning-with-reinforcement-learning/)).
- Not checked: "Gauss" (Math Inc.) and Kimina-Prover's full release. Both **UNVERIFIED**.

**Specification gaming.**
- **VERINA scores specs separately** (soundness and completeness against tests), and only
  ~half of generated specs pass.
- **Clover** exists because a generated spec can be consistent with wrong code.
- *Certified Program Synthesis with a Multi-Modal Verifier* (Feng, … Müller, Sergey,
  **preprint**, [arXiv:2604.16584](https://arxiv.org/abs/2604.16584)) says its spec
  validation "uncovers defects in existing reference benchmarks". The abstract does not name
  which ones. A search summary attributed the defects to VERINA and CLEVER, but I could not
  confirm it (**UNVERIFIED**).
- The vericoding paper's weak-spec remark appears in a search summary only (**UNVERIFIED**).
- The Verus guide's own cheat list (§2) is the practitioners' version of the same risk.

**What changes for us.**
1. **The headline rates are proof-only rates against a fixed, human-written spec.**
   - AutoVerus, VeruSAGE and Rust-Prover all prove a spec they were given.
   - Where the model also writes the spec (VERINA, vericoding, FVAPPS), rates fall to
     5–44%, and the spec is the weak point.
   - Our design already has the right shape: the theorem statement is **generated from the
     graph's contract**, and the agent writes body and proof only. The pilot should keep
     that and pin the statement by hash, as the registered generation run pins task hashes.
     Report "spec supplied" rates, never compare them to "spec generated" rates, and expect
     ~45–90% on small nodes, not 5%.
2. **The gate must reject cheats mechanically.**
   - In Lean: run `#print axioms` on the theorem and reject `sorryAx`, `Lean.ofReduceBool`
     and `Lean.trustCompiler` ([Lean reference: Axioms](https://lean-lang.org/doc/reference/4.33.0/Axioms/)).
     Also reject any new `axiom` or `opaque` outside the host-model file, and check that the
     theorem statement is byte-identical to the generated one.
   - In Verus: grep the diff for `assume`/`admit`/`external_body`/`axiom`, and diff the specs
     (guide). The Verus check is weaker because Verus has no kernel object to audit.
3. **Weak contracts make weak proofs.**
   - The closed vocabulary (`poc/contracts.py`) can say `amount <= 500` and
     `recipient in [...]`. It cannot relate output to input.
   - S3 theorems therefore need a statement language a little wider than the run-time
     contract: a quantified effect bound such as "every `send` in the effect list has
     `recipient ∈ payees`". That is still a statement the gate generates, not one the agent
     writes.

---

## 4. Resource-aware analysis

**AARA / RAML.**
- Hoffmann, Aehlig & Hofmann, *Multivariate Amortized Resource Analysis*, POPL 2011,
  pp. 357–370 ([bibtex](https://bibtex.github.io/POPL-2011-HoffmannAH.html)). A type-based
  analysis that infers polynomial bounds by linear programming, implemented in RAML for a
  first-order OCaml fragment.
- Survey: Hoffmann & Jost, *Two decades of automatic amortized resource analysis*, MSCS 32
  (2022), DOI 10.1017/S0960129521000487
  ([Cambridge](https://www.cambridge.org/core/journals/mathematical-structures-in-computer-science/article/two-decades-of-automatic-amortized-resource-analysis/9A47A8663CD8A7147E2F17865C368094)).

**AARA for Rust.** Lian & Wang, *Automatic Linear Resource Bound Analysis for Rust via
Prophecy Potentials (RaRust)*, OOPSLA 2025, Distinguished Paper
([arXiv:2502.19810](https://arxiv.org/abs/2502.19810)).
- It infers *linear* bounds for safe Rust with borrows, loops and recursion.
- It proves soundness on a "Resource-Aware Borrow Calculus", a variant of **LLBC, the same
  intermediate language Charon emits for Aeneas**.
- Prototype availability and input format: **UNVERIFIED**.

**Cost in separation logic.**
- Charguéraud & Pottier: time credits in CFML/Coq for union-find
  ([MSR page](https://www.microsoft.com/en-us/research/?p=192748)).
- Mével, Jourdan & Pottier, *Time Credits and Time Receipts in Iris*, LNCS (ESOP) 2019
  ([record](https://ouci.dntb.gov.ua/works/4ObRBgm7); venue named ESOP by convention,
  publisher page not checked).
- **Lean:** I found no established cost-semantics library.
  - A Zulip thread (December 2025) discusses a tick-counting monad and a CSLib
    time-complexity proposal
    ([Zulip](https://leanprover-community.github.io/archive/stream/113489-new-members/topic/Verifying.20Time.20Complexity.20of.20Functions.html)).
  - *Resource-Bounded Type Theory* (**preprint**,
    [arXiv:2512.06952](https://arxiv.org/abs/2512.06952)) is a graded-modality framework
    with a Lean tie-in.

**Bounds on WASM execution cost.**
- Shortt, Felty & Somayaji, *Bounding the Execution Cost of WebAssembly Functions*, VSTTE
  2025 preprint ([PDF](https://systemf.epfl.ch/etc/vstte2025/preprints/Bounding%20the%20Execution%20Cost%20of%20WebAssembly%20Functions.pdf)).
  - Static worst-case-cost bounds for over 107,000 functions, "based on the formalization of
    WebAssembly".
  - The tool itself is not claimed to be verified.
- `finite-wasm` instruments gas and stack and tests its analysis against an interpreter
  ([docs.rs](https://docs.rs/finite-wasm/0.3.1/finite_wasm)). That is testing, not proof.

**What changes for us.**
- **S4's "count of handle calls" is the easy case.** It is a linear bound, and usually a
  constant: `SendMoney` calls `send` once.
- **AARA tells us the technique scales to symbolic bounds.** RaRust shows it works on
  Rust's LLBC. But neither is a certificate a gate can check. They are trusted analysers.
- **For a PCC-shaped gate, a counted call bound is better proved as a theorem** in the
  chosen prover (§7). AARA and RaRust are prior art to cite, and possibly an oracle, not the
  mechanism.
- **Instruction counts stay with fuel (S1).** The WASM WCET work suggests a static bound is
  possible, but no surveyed tool gives a checkable certificate.

---

## 5. Meters, space banks, and their descendants

**KeyKOS.** Bomberger, Frantz, Frantz, Hardy, Hardy, Landau & Shapiro, *The KeyKOS
Nanokernel Architecture*, USENIX Micro-kernels workshop 1992
([PDF](https://pdos.csail.mit.edu/6.828/2009/readings/keykos.pdf);
[researchr](https://researchr.org/publication/BombergerFHHLS92)). I read the text:
- "A meter key provides the holder with the right to execute for the unit of time held by
  the meter." Meters subdivide into submeters, and every domain holds one.
- Applications that allocate "hold a key to a space bank". Banks create subbanks: "If your
  department has bought the right to a megabyte of storage, it is given a key to a space bank
  that holds 256 page keys."

**EROS.** Shapiro, Smith & Farber, *EROS: a fast capability system*, SOSP 1999, DOI
10.1145/319151.319163 (from a Keio Pure record) ([PDF](https://courses.cs.washington.edu/courses/cse551/19wi/readings/eros-sosp99.pdf)).
I did not re-read its space-bank section.

**seL4 MCS.** Lyons, McLeod, Almatary & Heiser, *Scheduling-Context Capabilities*, EuroSys
2018 ([PDF](https://sel4.systems/Research/pdfs/scheduling-context-capabilities.pdf)).
- Scheduling contexts are capability-protected objects holding a budget and a period. A
  partial context caps CPU at budget/period, using sporadic-server replenishment
  ([MCS tutorial](https://docs.sel4.systems/Tutorials/mcs.html)).
- Functional verification of MCS is expected around mid-2027, per a May 2026 Heiser talk
  ([slides](https://trustworthy.systems/publications/papers/Heiser_26%3Artas.slides.pdf)).
  That is a stated target.

**Fuchsia job policy.** `zx_job_set_policy` offers allow/deny/kill on *conditions*
(`ZX_POL_NEW_VMO`, `ZX_POL_NEW_CHANNEL`, …) and timer slack. **It sets no quantities**: no
CPU or memory quota ([reference](https://fuchsia.dev/reference/syscalls/job_set_policy)).

**Wasmtime fuel and epochs.**
- Fuel is "completely deterministic". Epochs are non-deterministic (wall-time) and cost
  "around a 10% slowdown"; fuel "imposes more overhead … than epochs do"
  ([interrupting Wasm](https://docs.wasmtime.dev/examples-interrupting-wasm.html)).
- From the `Config` docs ([Config](https://docs.wasmtime.dev/api/wasmtime/struct.Config.html)):
  - fuel works by instrumenting generated code;
  - each operator's cost is configurable (`operator_cost`);
  - "fuel instrumentation is somewhat expensive", and epochs can be faster "up to 2-3x" in
    some measurements;
  - "fuel accounting is not precise when WebAssembly traps".

**What changes for us.**
- **KeyKOS is the exact precedent for S1 and D5.** Meters and banks are *capabilities that
  subdivide*, and subdividing a meter spends from the parent. That is D5's point: budgets do
  not narrow like sets. The citation supports treating a budget as a spendable sub-handle,
  not a scope annotation.
- **seL4 MCS is the modern, formally targeted descendant**, for CPU only.
- **Fuchsia is not a precedent for budgets.** Drop it, or cite it only for condition
  policies.
- **For the S1 spike:**
  - Use fuel for determinism, so an overrun reproduces in a test.
  - Measure fuel's cost against `CROSSING_BAND_*`. Wasmtime publishes no fuel overhead
    figure, only "more than epochs", so the measurement is new.
  - Class trap-time fuel imprecision as a stated limit.
  - Epoch deadlines bound wall-clock time and are non-deterministic by design. That suits
    a limit, not a reproducible test.

---

## 6. Checking contracts across edges

- **Interface automata.** de Alfaro & Henzinger, FSE 2001, DOI 10.1145/503209.503226
  ([ISTA record](https://research-explorer.ista.ac.at/record/4622)). Input assumptions and
  output guarantees, with automatic compatibility checking between interfaces.
- **Contract-based design.** Benveniste et al., *Contracts for System Design*, Foundations
  and Trends in EDA 12(2–3), 2018, DOI 10.1561/1000000053
  ([summary](https://nowpublishers.com/article/DownloadSummary/EDA-053)). The standard
  assume–guarantee algebra: composition, refinement, compatibility.
- **JSON subschema checking.** Habib, Shinnar, Hirzel & Pradel, *Finding Data Compatibility
  Bugs with JSON Subschema Checking*, ISSTA 2021, DOI 10.1145/3460319.3464796
  ([arXiv](https://arxiv.org/abs/1911.12651v2); tool:
  [jsonsubschema](https://github.com/ibm/jsonsubschema)).
  - It decides "every instance of s1 validates against s2" by canonicalising both schemas,
    then using **type-specific checkers, with no SMT**.
  - It found 43 previously unknown bugs.
- **Dafny/Boogie** check call-site preconditions against callee postconditions through SMT.
  No specific paper is cited here, so take this as general background, not a checked
  source.

**What changes for us (S2).**
- **The vocabulary is per-path.** I read the grammar in `poc/contracts.py`: every atom
  (`path op literal`, `path in [...]`, `present(path)`, `len(path) op int`) constrains **one
  path against a literal**.
  - Implication between conjunctions is therefore decidable *per path* in a non-relational
    domain: intervals with excluded points for `!=`, finite sets for `in`, a presence flag,
    and an interval on `len`.
  - Meet the producer's atoms per path, then check that each consumer atom contains the
    result. This confirms D3's "interval and set reasoning alone".
- **It is the same move as jsonsubschema**: canonicalise, then check per type. Cite that
  paper as prior art for an SMT-free containment checker. Cite Benveniste for the
  vocabulary: compatibility and refinement.
- **Cases the S2 spike should test on purpose:**
  1. Whether a comparison atom on an absent path is false. If so, it implies `present`.
  2. Mixed-type comparisons, such as a string against an int literal.
  3. Field renaming across an edge, where the producer's output path differs from the
     consumer's input path.
  4. The per-variant split on sum types.
  5. `!=` on an unbounded domain.

  None of them breaks decidability. Each is a place a hand-rolled checker can be wrong.

---

## 7. Recommendation: the prover for S3 and S4

### Honest comparison

| | **Aeneas → Lean 4** | **Verus** |
|---|---|---|
| Certificate the gate checks | A Lean term checked by the kernel; audit with `#print axioms`. PCC in Necula's sense. | Annotations re-checked by Verus + Z3. No independent certificate. |
| Trusted base | Charon + Aeneas translation; hand-written host models; Lean kernel | Verus VC generation, Z3, `vstd` assumed specs, rustc |
| Fit to these crates | Rejects `unsafe` (all wit-bindgen glue). Closures in progress. String literals possibly unsupported (UNVERIFIED). `serde_json` untranslatable. | Proc-macro code is a stated weak spot. `serde_json` unverifiable. `String` thinly specified. |
| macOS arm64 install | opam/OCaml 5 + pinned Charon + pinned Lean; no binaries | Prebuilt macOS-arm zip + pinned rustup toolchain |
| Agent evidence (spec supplied) | Strong but unquantified (SymCrypt, zkEVM; Aeneas). Rust-Prover's 1,325/1,325 is Lean with its **own** translator, not Aeneas. Aegis 52.7% UNVERIFIED. | Quantified and reviewed: AutoVerus >90% (150 tasks), SAFE ~79%, VeruSAGE >80% (849 tasks). Official LLM guidance. |
| Agent evidence (spec generated) | Lean 27%, VERINA proofs 4.9% | Verus 44% (vericoding) |
| S4 route | A theorem about the extracted function (see below) | **Tracked linear ghost tokens**: each host call `requires` a token, so N tokens prove at most N calls. Native to Verus's "linear ghost types". |

### Recommendation

**Choose Lean via Aeneas for S3 and S4, with one condition: prove a pure core, not the node.**
Spend half a day first establishing that Aeneas translates that core. If it does not, the
fallback is Verus on the same core.

**Why Lean.**
1. **The gate becomes real PCC.** It checks a kernel term, it can audit the axioms
   mechanically, and the agent cannot weaken anything without the axiom list or the
   statement hash changing. With Verus, the gate's integrity depends on a grep and a spec
   diff (the guide says spec-change detection "requires parser support").
2. **Agents are now good at Lean in exactly this shape:** Rust translated to Lean, with a
   fixed theorem.
   - SymCrypt and zkEVM report agent-written proofs at scale, and Rust-Prover reports
     near-saturation.
   - Raw Verus rates are better *documented*, but the newest results suggest the gap has
     closed when the spec is supplied. Two caveats keep this from being a verdict: the
     strongest Lean result is a preprint, and its translator is not Aeneas.
3. **Author experience.** It makes hand-written proofs, D3's step one, cheap to write.

**Why "pure core".** Both tools fail on these crates as written:
- Aeneas fails on wit-bindgen's `unsafe` glue and `serde_json`.
- Verus is weak on proc-macro output and also cannot verify `serde_json`.

**The pattern.**
- Move the decision logic into a small `core` module in the crate, or a sibling crate. It
  uses no `wit_bindgen`, no `serde`, fixed-width integers, `Vec<u8>` or `&str` without
  literals if Charon refuses them, and no closures.
- Its signature takes **every host result as an argument**, including the model's reply.
  For example, `fn decide(order: Order, reply: Reply, payees: &[Payee], cap: u64) ->
  Vec<Effect>`.
- It returns the effects as data.
- The `run` shell parses, calls `decide`, and performs each effect with the matching host
  call. The shell is a few lines, trusted, and listed as such. **Kani or the trace's call
  layer can check that the shell performs exactly the effects `decide` returns.**

This is what makes the design note's "for every response r" literal. `reply` is a universally
quantified argument of the theorem, so the theorem reads `∀ reply, ∀ e ∈ decide …, e.payee ∈
payees ∧ e.amount ≤ cap`.

**S4 under this pattern.** A bound on the number of calls becomes `(decide …).length ≤ k`,
an ordinary functional lemma in Lean.
- It needs no cost semantics, no time credits and no Lean resource library, because effects
  are data. Lean has no mature resource library anyway (§4).
- The trace's call layer already records per-use calls. The design note's check that the
  trace never exceeds the proved bound applies directly. A bound exceeded at run time would
  indict the shell or the trusted base, not the core.
- Multiply by the S1 per-call scope (tokens per call, enforced at the crossing) for the
  combined bound, as the design note proposes.

**The limit of this route.** It covers nodes whose host calls do not depend on the results
of earlier calls within the same run. Where a node loops through calls, such as a tool loop
whose next call depends on the reply, the core must be written as a step function `state ×
reply → state × Option<Effect>`. The bound becomes a bound on iterations, and that is where
Verus's tracked tokens are the more natural tool. None of the current crates does this, as
far as I read them (`ParseMessage` makes one inference call, `SendMoney` one send).

**Viable S4 route?**
- **Yes, for call counts**, by the effects-as-data lemma in Lean, checked against the trace.
- **Yes for instruction counts only at run time**, through fuel in S1. No surveyed tool
  yields a checkable certificate for a WASM instruction bound.
- RaRust and AARA are the citations for symbolic bounds if a node ever needs one. They are
  trusted analysers, not certificates.

**Risks to state up front.**
1. Aeneas may reject even the core: string literals, `chars()`, or a std function with no
   model. That is why the half-day check comes first.
2. The Lean toolchain pin and Aeneas's own pin will drift, as the experience report says.
   Install it in its own environment under `spikes/`, per D2.
3. The extraction is a refactor of evidence-bearing crates. Paper 2's nine components are
   pinned. Do the spike on copies in `spikes/specified-architecture/`, never in
   `poc/sandbox/rust/`.
4. Translation fidelity is part of the trusted base. Rust-Prover checked its Lean
   translations against 21,413 test cases. The spike should differential-test the extracted
   Lean against the Rust core on the contract's inputs, as `poc/generation/differential.py`
   already does for bodies.
