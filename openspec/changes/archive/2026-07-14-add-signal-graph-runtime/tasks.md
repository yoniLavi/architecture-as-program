## 1. Scaffolding & dependencies
- [x] 1.1 Create `poc/` package; add optional `poc` dependency group (Anthropic SDK) to
      `pyproject.toml` without touching the stdlib-only validator/parser import graph
- [x] 1.2 Wire `poc/` into pytest paths; confirm `make build` and existing tests are unaffected

## 2. Capability handles
- [x] 2.1 Implement handle objects with scope-enforcing surfaces: `InferenceLLM` (no tools),
      `ToolLLM([...])` (named tools only), `ReadDBHandle` (read-only), `ResponseChannel` /
      `EventEmitter` (write-only sinks)
- [x] 2.2 Provide a deterministic offline model backend (`StubLLM`) for reproducible runs
- [x] 2.3 Tests: each handle rejects out-of-scope operations (inference-LLM tool call, read-handle
      write, wrong tool name)

## 3. Graph loading & assembly
- [x] 3.1 Load `graphs/customer-support.json`; build the node/edge structure
- [x] 3.2 Reuse `graph_validator` to gate assembly; bind each node to exactly its declared handles
- [x] 3.3 Tests: canonical graph assembles; two unsafe-wiring variants are rejected at assembly time
      (`bypass_pipeline` on edge typing, `launder_trust` on trust propagation)

## 4. Node implementations & execution
- [x] 4.1 Implement the vertical's non-LLM nodes (ReceiveMessage, FetchContext, SendReply, …)
- [x] 4.2 Implement the LLM-backed nodes (ParseMessage, ModerateContent, GenerateResponse) against
      the `claude-api` reference; add the `--live` flag (`AnthropicBackend`, model `claude-opus-4-8`)
- [x] 4.3 AI-generate `ParseMessage` from its signature+contract; commit the generation prompt
      (`poc/generated/parse_message.prompt.md`) and resulting code as artifacts
- [x] 4.4 Topological executor that propagates signals along the active path
- [~] 4.5 **Adjusted:** rather than recording fixtures from a live run, the default backend is a
      deterministic offline stub. Same benefit (reproducible, network-free CI), less machinery.
      Spec updated to match. The `--live` path exists but has **not been exercised** — no API call
      has been made from this repo yet.
- [x] 4.6 Tests: benign message → `DeliveryConfirmation` (offline), deterministic

## 5. Prompt-injection demonstration
- [x] 5.1 Executable demo script: benign vs adversarial message through the pipeline (`poc/demo.py`)
- [x] 5.2 Assert inference-only nodes are never offered a tool and `GenerateResponse` never receives
      the `Untrusted[RawMessage]` value
- [x] 5.3 Print the enforcement-fidelity disclaimer (host-discipline now; sandbox/CHERI later)
- [x] 5.4 Tests covering the attenuation assertions, **including** an explicit test asserting the
      free-text residual is real (`test_free_text_residual_is_real_and_acknowledged`)

## 6. Wrap-up
- [x] 6.1 `poc/README.md`: how to run (offline + live), what is and is not enforced
- [x] 6.2 Fold findings back into the proposal: @sec:phase1 (runtime demonstrator + its
      host-discipline limit), Technical Note A coercion problem (trust laundering is caught only by
      an independent trust rule), Technical Note A hierarchical capability routing (handle aliasing
      by capability *type*, motivating capability *identity* at the boundary)
- [x] 6.3 Run ruff + full pytest + `make build`; all green (82 tests + 11 subtests)

## Findings for Technical Note A (input to task 6.2)
1. **Trust discharge is only as strong as the discharging schema.** `ParseMessage` discharges trust
   on the strength of an LLM classification, but the bounded free-text `question` field survives and
   reaches the tool-capable node. The capability scope — not the type — is what bounds the damage.
   This sharpens, and empirically confirms, the proviso already in §5.
2. **Trust laundering is a distinct failure mode from type mismatch.** Widening a consumer's input
   type to `Untrusted<T>` makes the edge type-check; only a separate trust-propagation rule rejects
   it. This is the coercion problem of Technical Note A showing up in practice, and it is evidence
   that the rule must be enforced *independently* of edge typing, not as a consequence of it.
3. **Single-data-input-per-node is load-bearing.** The validator rejects nodes with >1 data input,
   which made the executor trivial (a data-driven walk, no join semantics). Real graphs will need
   fan-in, and fan-in reintroduces the merge-order problem already flagged under replay fidelity.
4. **Capability provisioning is graph-level, not node-level.** Handles are provisioned once per
   graph and shared by every node that declares the same capability *type*. Two nodes declaring
   `DBHandle<'knowledge-base', read>` get the *same* handle object. That is fine for read-only
   handles but is exactly the aliasing question flagged under hierarchical capability routing.
