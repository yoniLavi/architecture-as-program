/-
S3's theorem statements: the specification side of the gate.

Written by the gate (here, by hand, from the graph's contracts and the node's
documented behaviour), pinned by hash in `../statements.sha256`, and never edited
by whoever writes the proofs. `Proofs.lean` proves each `Prop` below as stated;
`../check.sh` refuses a proof file that declares an axiom, or whose theorems
depend on any axiom beyond Lean's standard three.

`x ⦃ r => P r ⦄` is Aeneas's total-correctness triple: `x` returns `ok r` (no
panic, no overflow, no divergence) and `P r` holds.
-/
import Cores

open Aeneas Aeneas.Std Result
open cores

namespace Statements

/-- **DropSeen.** For every batch of ids and every set of recorded ids: the body
returns (no panic), every id it keeps came in and was not recorded, it keeps each
id once, and it keeps every id that came in and was not recorded. -/
def drop_seen_spec : Prop :=
  ∀ (items recorded : alloc.vec.Vec Std.U64),
    drop_seen items recorded ⦃ out =>
      (∀ x ∈ out.val, x ∈ items.val ∧ x ∉ recorded.val) ∧
      out.val.Nodup ∧
      (∀ x ∈ items.val, x ∉ recorded.val → x ∈ out.val) ⦄

/-- **SummariseItem's summary, for every model reply.** For every reply and every
limit: the body returns, the summary is at most `limit` code points, and it holds no
line break (LF, CR, VT, FF, NEL, LS, PS). At `limit = 400` this is the graph's
`ensures len(summary) <= 400`, proved rather than checked. -/
def one_line_spec : Prop :=
  ∀ (reply : alloc.vec.Vec Std.U32) (limit : Std.Usize),
    one_line reply limit ⦃ out =>
      out.val.length ≤ limit.val ∧
      (∀ c ∈ out.val, c.val ∉ [0x0A, 0x0B, 0x0C, 0x0D, 0x85, 0x2028, 0x2029]) ⦄

/-- The two crossings the tool loop can make. -/
def generates (log : List Effect) : Nat := (log.filter (fun e => e matches .Generate)).length
def lookups (log : List Effect) : Nat := (log.filter (fun e => e matches .Lookup)).length

/-- **GenerateResponse, for every model and every knowledge base.** `Host` is the
model and the knowledge base: the statement quantifies over every implementation
and every state, so it covers any model, however it adapts to what it has seen.
Whenever a run completes (a host call may fail, and then so does the run):
- at most 3 model calls and at most 3 lookups, so at most 6 crossings (S4's bound);
- no lookup without a model call before it;
- a refused tool is never the granted one. -/
def respond_spec : Prop :=
  ∀ {H : Type} (inst : Host H) (host : H) (granted : alloc.vec.Vec Std.U32)
    (outcome : Outcome) (log : alloc.vec.Vec Effect) (host' : H),
    respond inst host granted = ok ((outcome, log), host') →
      generates log.val ≤ 3 ∧ lookups log.val ≤ 3 ∧ log.val.length ≤ 6 ∧
      lookups log.val ≤ generates log.val ∧
      (∀ tool, outcome = .ToolRefused tool → tool.val ≠ granted.val)

end Statements
