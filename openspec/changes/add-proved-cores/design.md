# Design

## Decisions

- **D1. The gate owns the statements; the prover owns only proofs.** This is
  proof-carrying code, as in the spike. The gate generates each statement and its prose
  from the graph (contract, capability clause, budget), and pins both by hash.
- **D2. The gate checks what the kernel holds, never what a file prints.** The hardened
  gate is carried over whole:
  - the pinned code builds first and its `.olean` files are hashed;
  - the proof builds in a sandbox with no network and no writes outside the build
    directory;
  - the hashes are re-checked;
  - a separate audit process (`Audit.lean`) checks the exact statement type, walks the
    axioms over the compiled terms, and replays every non-library constant through the
    kernel.
  - `sandbox-exec` is deprecated on macOS. CI on Linux needs an equivalent (bubblewrap or
    a container); D2 names the property, not the tool.
- **D3. Effects carry what a scope constrains.** A lookup carries its tool and a payment
  its payee, so the capability clause can be stated over the effect log. This is the
  lesson of `respond_spec`.
- **D4. Statements are total where they can be.** Partial correctness is used only for a
  loop over a `Host`. There, termination is the call bound's job, enforced at run time by
  the `Calls` budget.

## Open questions (answered in task 0.1)

1. **What does a proof earn in the graph?** (Deferred from the spike as its Q2.)
   Recommended: a proved `requires` on a discharged edge (`add-contract-composition-check`)
   may skip its run-time check, and nothing else changes. Every other run-time check stays.
2. **Must `make build` run the prover?** Recommended: no. Proofs are verified by an
   opt-in `make proofs`, and in CI where the toolchain is installed. `make build` checks
   that the committed proofs' hashes match their statements, as `make wasm` and the
   committed components work now.
3. **Agent-written proofs as evidence?** Recommended: yes, as a registered run in the
   style of Paper 3, with statements fixed before any call and the hardened gate deciding.
   It runs on the Max subscription, with no paid spend.
4. **Which nodes after the three spiked ones?** Recommended: the capability-holding
   nodes of the feed-triage service, where a model reply reaches an effect.
