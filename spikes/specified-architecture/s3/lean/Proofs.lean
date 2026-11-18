/-
Proofs of `Statements`, checked by `../check.sh`.
-/
import Statements

open Aeneas Aeneas.Std Result
open cores

namespace Proofs

/-! ## drop_seen -/

theorem contains_loop_spec (xs : alloc.vec.Vec Std.U64) (x : Std.U64) (found : Bool) (i : Std.Usize)
    (hi : i.val ≤ xs.val.length) :
    contains_loop xs x found i ⦃ b => (b = true ↔ (found = true ∨ x ∈ xs.val.drop i.val)) ⦄ := by
  unfold contains_loop
  apply loop.spec_decr_nat (measure := fun (s : Bool × Std.Usize) => xs.val.length - s.2.val)
    (inv := fun s => s.2.val ≤ xs.val.length ∧ ((found = true ∨ x ∈ xs.val.drop i.val) ↔ (s.1 = true ∨ x ∈ xs.val.drop s.2.val)))
  · rintro ⟨f, j⟩ ⟨hj, hiff⟩
    simp only at hj hiff
    dsimp only
    unfold contains_loop.body
    dsimp only
    split
    · have hlt : j.val < xs.val.length := by scalar_tac
      have hd := List.drop_eq_getElem_cons hlt
      step*
      · split
        · rename_i heq
          step*
          refine ⟨by scalar_tac, ?_, by scalar_tac⟩
          simp only [true_or, iff_true]
          rw [hiff, hd, ← heq, i2_post]
          exact Or.inr List.mem_cons_self
        · rename_i hne
          step*
          refine ⟨by scalar_tac, ?_, by scalar_tac⟩
          have : x ≠ (↑xs : List Std.U64)[j.val] := fun h => hne (by rw [i2_post, h])
          rw [hiff, hd, i3_post, List.mem_cons]
          simp only [this, false_or]
    · have : j.val = xs.val.length := by scalar_tac
      simp [hiff, this]
  · simp [hi]

theorem contains_spec' (xs : alloc.vec.Vec Std.U64) (x : Std.U64) :
    contains xs x ⦃ b => (b = true ↔ x ∈ xs.val) ⦄ := by
  apply WP.spec_mono (contains_loop_spec xs x false 0#usize (by simp))
  intro b h
  simpa using h

/-- The invariant of `drop_seen`'s loop over `(fresh, j)`. -/
def DSInv (items recorded : List Std.U64) (fresh : List Std.U64) (j : Nat) : Prop :=
  j ≤ items.length ∧ fresh.length ≤ j ∧
  (∀ y ∈ fresh, y ∈ items ∧ y ∉ recorded) ∧ fresh.Nodup ∧
  (∀ y ∈ items.take j, y ∉ recorded → y ∈ fresh)

theorem drop_seen_holds : Statements.drop_seen_spec := by
  intro items recorded
  unfold drop_seen drop_seen_loop
  apply loop.spec_decr_nat
    (measure := fun (s : alloc.vec.Vec Std.U64 × Std.Usize) => items.val.length - s.2.val)
    (inv := fun s => DSInv items.val recorded.val s.1.val s.2.val)
  · rintro ⟨fresh, j⟩ ⟨hj, hlen, hsub, hnd, hall⟩
    simp only at hj hlen hsub hnd hall
    dsimp only
    unfold drop_seen_loop.body
    dsimp only
    split
    · have hlt : j.val < items.val.length := by scalar_tac
      step*
      have htake : items.val.take (j.val + 1) = items.val.take j.val ++ [id] := by
        rw [id_post]; exact List.take_succ_eq_append_getElem hlt
      have hid : id ∈ items.val := by rw [id_post]; exact List.getElem_mem hlt
      step with contains_spec' as ⟨b, hb⟩
      split
      · rename_i hbt
        have hin : id ∈ fresh.val := hb.mp hbt
        step*
        refine ⟨⟨by scalar_tac, by scalar_tac, hsub, hnd, ?_⟩, by scalar_tac⟩
        rw [i2_post, htake]
        intro y hy hyr
        rcases List.mem_append.mp hy with hy | hy
        · exact hall y hy hyr
        · rw [List.mem_singleton.mp hy]; exact hin
      · rename_i hbf
        have hnin : id ∉ fresh.val := fun h => hbf (hb.mpr h)
        step with contains_spec' as ⟨b1, hb1⟩
        split
        · rename_i hbt
          have hrec : id ∈ recorded.val := hb1.mp hbt
          step*
          refine ⟨⟨by scalar_tac, by scalar_tac, hsub, hnd, ?_⟩, by scalar_tac⟩
          rw [i2_post, htake]
          intro y hy hyr
          rcases List.mem_append.mp hy with hy | hy
          · exact hall y hy hyr
          · rw [List.mem_singleton.mp hy] at hyr; exact absurd hrec hyr
        · rename_i hbf1
          have hnrec : id ∉ recorded.val := fun h => hbf1 (hb1.mpr h)
          step*
          refine ⟨⟨by scalar_tac, ?_, ?_, ?_, ?_⟩, by scalar_tac⟩
          · rw [fresh1_post, i2_post, List.length_append]; simp only [List.length_singleton]
            scalar_tac
          · rw [fresh1_post]
            intro y hy
            rcases List.mem_append.mp hy with hy | hy
            · exact hsub y hy
            · rw [List.mem_singleton.mp hy]; exact ⟨hid, hnrec⟩
          · rw [fresh1_post, List.nodup_append]
            refine ⟨hnd, List.nodup_singleton _, ?_⟩
            intro a ha b hb' hab
            rw [List.mem_singleton.mp hb'] at hab
            exact hnin (hab ▸ ha)
          · rw [fresh1_post, i2_post, htake]
            intro y hy hyr
            rcases List.mem_append.mp hy with hy | hy
            · exact List.mem_append_left _ (hall y hy hyr)
            · exact List.mem_append_right _ hy
    · have hjl : j.val = items.val.length := by scalar_tac
      rw [hjl, List.take_length] at hall
      simp only [WP.spec_ok]
      exact ⟨hsub, hnd, hall⟩
  · simp [DSInv]

/-! ## one_line -/

/-- The line breaks the statement forbids. -/
abbrev LB : List Nat := [0x0A, 0x0B, 0x0C, 0x0D, 0x85, 0x2028, 0x2029]

theorem is_space_spec (c : Std.U32) :
    is_space c ⦃ b => b = false → c.val ∉ LB ⦄ := by
  unfold is_space
  step*
  all_goals
    intro _
    simp only [LB, List.mem_cons, List.not_mem_nil, or_false, not_or]
    refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> scalar_tac

theorem truncate_spec (xs : alloc.vec.Vec Std.U32) (limit : Std.Usize) :
    truncate xs limit ⦃ out => out.val.length ≤ limit.val ∧ ∀ c ∈ out.val, c ∈ xs.val ⦄ := by
  unfold truncate truncate_loop
  apply loop.spec_decr_nat
    (measure := fun (s : alloc.vec.Vec Std.U32 × Std.Usize) => xs.val.length - s.2.val)
    (inv := fun s => s.2.val ≤ xs.val.length ∧ s.1.val.length = s.2.val ∧ s.2.val ≤ limit.val ∧
      ∀ c ∈ s.1.val, c ∈ xs.val)
  · rintro ⟨out, k⟩ ⟨hk, hlen, hlim, hsub⟩
    simp only at hk hlen hlim hsub
    dsimp only
    unfold truncate_loop.body
    dsimp only
    split
    · split
      · have hlt : k.val < xs.val.length := by scalar_tac
        step*
        refine ⟨by scalar_tac, ?_, by scalar_tac, ?_, by scalar_tac⟩
        · rw [out1_post, i3_post, List.length_append, hlen]; simp
        · rw [out1_post]
          intro c hc
          rcases List.mem_append.mp hc with hc | hc
          · exact hsub c hc
          · rw [List.mem_singleton.mp hc, i2_post]; exact List.getElem_mem hlt
      · simp only [WP.spec_ok]
        exact ⟨by scalar_tac, hsub⟩
    · simp only [WP.spec_ok]
      exact ⟨by scalar_tac, hsub⟩
  · simp

/-- The invariant of `one_line`'s loop over `(out, pending_space, j)`: a pending space
is counted against the input read so far, so the two pushes never overflow. -/
def OLInv (n : Nat) (out : List Std.U32) (pending : Bool) (j : Nat) : Prop :=
  j ≤ n ∧ out.length + (if pending then 1 else 0) ≤ j ∧ ∀ c ∈ out, c.val ∉ LB

theorem one_line_loop_spec (text : alloc.vec.Vec Std.U32) :
    one_line_loop text (alloc.vec.Vec.new Std.U32) false 0#usize ⦃ out =>
      ∀ c ∈ out.val, c.val ∉ LB ⦄ := by
  unfold one_line_loop
  apply loop.spec_decr_nat
    (measure := fun (s : alloc.vec.Vec Std.U32 × Bool × Std.Usize) => text.val.length - s.2.2.val)
    (inv := fun s => OLInv text.val.length s.1.val s.2.1 s.2.2.val)
  · rintro ⟨out, pending, j⟩ ⟨hj, hlen, hnl⟩
    simp only at hj hlen hnl
    dsimp only
    unfold one_line_loop.body
    dsimp only
    split
    · have hlt : j.val < text.val.length := by scalar_tac
      step*
      step with is_space_spec as ⟨b, hb⟩
      split
      · split
        · step*
          have h1 : out.val.length ≤ j.val := by
            split at hlen
            · scalar_tac
            · scalar_tac
          refine ⟨⟨by scalar_tac, ?_, hnl⟩, by scalar_tac⟩
          simp only [ite_true]
          scalar_tac
        · step*
          refine ⟨⟨by scalar_tac, ?_, hnl⟩, by scalar_tac⟩
          rw [i2_post]
          exact Nat.le_succ_of_le hlen
      · rename_i hbf
        have hc : c.val ∉ LB := hb (by simpa using hbf)
        split
        · rename_i hp
          have h1 : out.val.length + 1 ≤ j.val := by simpa [hp] using hlen
          step as ⟨y, hy⟩
          step as ⟨z, hz⟩
          · simp only [hy, List.length_append, List.length_singleton]
            scalar_tac
          step as ⟨i2, i2_post⟩
          · refine ⟨⟨by scalar_tac, ?_, ?_⟩, by scalar_tac⟩
            · simp only [hz, hy, List.length_append, List.length_singleton]
              simp only [Bool.false_eq_true, ite_false]
              scalar_tac
            · intro d hd
              simp only [hz, hy, List.mem_append, List.mem_singleton] at hd
              rcases hd with (hd | hd) | hd
              · exact hnl d hd
              · rw [hd]; decide
              · rw [hd]; exact hc
        · rename_i hp
          have h1 : out.val.length ≤ j.val := by simpa [hp] using hlen
          step*
          refine ⟨⟨by scalar_tac, ?_, ?_⟩, by scalar_tac⟩
          · simp only [x_post, List.length_append, List.length_singleton, hp]
            simp only [Bool.false_eq_true, ite_false]
            scalar_tac
          · intro d hd
            simp only [x_post, List.mem_append, List.mem_singleton] at hd
            rcases hd with hd | hd
            · exact hnl d hd
            · rw [hd]; exact hc
    · simp only [WP.spec_ok]
      exact hnl
  · simp [OLInv]

theorem one_line_holds : Statements.one_line_spec := by
  intro reply limit
  unfold one_line
  step with one_line_loop_spec as ⟨out, hout⟩
  apply WP.spec_mono (truncate_spec out limit)
  rintro r ⟨hlen, hsub⟩
  exact ⟨hlen, fun c hc => hout c (hsub c hc)⟩

/-! ## respond: partial correctness, since the host's methods may fail -/

theorem bind_ok_inv {α β : Type} {m : Result α} {k : α → Result β} {y : β}
    (h : Std.bind m k = ok y) : ∃ a, m = ok a ∧ k a = ok y := by
  cases m with
  | ret a => exact ⟨a, rfl, by simpa using h⟩
  | vis e k' => simp at h
  | div => simp at h

theorem spec_ok_eq {α : Type} {m : Result α} {P : α → Prop} {y : α}
    (hs : m ⦃ r => P r ⦄) (h : m = ok y) : P y := by
  rw [h] at hs
  simpa using hs

/-- A loop rule for partial correctness: if every successful step of the body keeps the
invariant and decreases the measure, every successful run ends in the postcondition. -/
theorem loop_pc {α β : Type} (measure : α → Nat) (inv : α → Prop) (post : β → Prop)
    (body : α → Result (ControlFlow α β))
    (hBody : ∀ x, inv x → ∀ r, body x = ok r →
      match r with
      | .done y => post y
      | .cont x' => inv x' ∧ measure x' < measure x) :
    ∀ x, inv x → ∀ y, loop body x = ok y → post y := by
  intro x
  induction h : measure x using Nat.strong_induction_on generalizing x with
  | _ n ih =>
    intro hx y hy
    unfold loop at hy
    obtain ⟨r, hr, hk⟩ := bind_ok_inv hy
    have hb := hBody x hx r hr
    cases r with
    | cont x' =>
      dsimp only at hk
      exact ih (measure x') (h ▸ hb.2) x' rfl hb.1 y hk
    | done z =>
      dsimp only at hk
      have : z = y := by simpa using hk
      exact this ▸ hb

theorem same_spec (a b : alloc.vec.Vec Std.U32) :
    same a b ⦃ r => a.val = b.val → r = true ⦄ := by
  unfold same
  dsimp only
  split
  · simp only [WP.spec_ok]
    intro h
    rename_i hne
    simp only [bne_iff_ne, ne_eq] at hne
    exact absurd (by scalar_tac) hne
  · unfold same_loop
    apply loop.spec_decr_nat
      (measure := fun (s : Bool × Std.Usize) => a.val.length - s.2.val)
      (inv := fun s => s.2.val ≤ a.val.length ∧ a.val.length = b.val.length ∧
        (a.val = b.val → s.1 = true))
    · rintro ⟨eq, i⟩ ⟨hi, hab, heq⟩
      simp only at hi hab heq
      dsimp only
      unfold same_loop.body
      dsimp only
      split
      · step*
        split
        · rename_i hneq
          step*
          refine ⟨by scalar_tac, hab, ?_, by scalar_tac⟩
          intro h
          exfalso
          simp only [bne_iff_ne, ne_eq] at hneq
          apply hneq
          rw [i2_post, i3_post]
          exact List.getElem_of_eq h _
        · step*
          exact ⟨by scalar_tac, hab, heq, by scalar_tac⟩
      · simp only [WP.spec_ok]
        exact heq
    · rename_i hne
      refine ⟨by simp, ?_, fun _ => rfl⟩
      simp at hne
      scalar_tac

theorem generates_append (l : List Effect) (e : Effect) :
    Statements.generates (l ++ [e]) =
      Statements.generates l + (match e with | .Generate => 1 | .Lookup => 0) := by
  cases e <;> simp [Statements.generates, List.filter_append]

theorem lookups_append (l : List Effect) (e : Effect) :
    Statements.lookups (l ++ [e]) =
      Statements.lookups l + (match e with | .Generate => 0 | .Lookup => 1) := by
  cases e <;> simp [Statements.lookups, List.filter_append]

theorem length_eq_gen_add_look (l : List Effect) :
    l.length = Statements.generates l + Statements.lookups l := by
  induction l with
  | nil => simp [Statements.generates, Statements.lookups]
  | cons e l ih =>
    cases e <;> simp [Statements.generates, Statements.lookups] at ih ⊢ <;> omega

/-- The invariant of `respond`'s loop over `(host, log, round, outcome, done)`. -/
def RInv {H : Type} (granted : alloc.vec.Vec Std.U32)
    (s : H × alloc.vec.Vec Effect × Std.Usize × Outcome × Bool) : Prop :=
  s.2.2.1.val ≤ 3 ∧ Statements.generates s.2.1.val = s.2.2.1.val ∧
  Statements.lookups s.2.1.val ≤ s.2.2.1.val ∧
  ∀ t, s.2.2.2.1 = .ToolRefused t → t.val ≠ granted.val

def RPost {H : Type} (granted : alloc.vec.Vec Std.U32)
    (r : H × alloc.vec.Vec Effect × Outcome) : Prop :=
  Statements.generates r.2.1.val ≤ 3 ∧
  Statements.lookups r.2.1.val ≤ Statements.generates r.2.1.val ∧
  ∀ t, r.2.2 = .ToolRefused t → t.val ≠ granted.val

theorem respond_body_pc {H : Type} (inst : Host H) (granted : alloc.vec.Vec Std.U32)
    (s : H × alloc.vec.Vec Effect × Std.Usize × Outcome × Bool) (hs : RInv granted s) :
    ∀ r, (match s with
      | (h1, l1, r1, o1, d1) => respond_loop.body inst granted h1 l1 r1 o1 d1) = ok r →
    match r with
    | .done y => RPost granted y
    | .cont x' => RInv granted x' ∧ 3 - x'.2.2.1.val < 3 - s.2.2.1.val := by
  intro r hr
  obtain ⟨host, log, round, outcome, d⟩ := s
  obtain ⟨hround, hgen, hlook, hout⟩ := hs
  simp only at hround hgen hlook hout hr
  have hM : MAX_ROUNDS.val = 3 := by unfold MAX_ROUNDS; rfl
  have hloglen : log.val.length ≤ 6 := by
    rw [length_eq_gen_add_look]; omega
  unfold respond_loop.body at hr
  by_cases hR : round < MAX_ROUNDS
  · simp only [hR, ite_true] at hr
    have hR' : round.val < 3 := by rw [← hM]; exact hR
    by_cases hd : d = true
    · simp only [hd, ite_true] at hr
      have := (Result.ok.injEq ▸ hr : _ = r)
      subst this
      exact ⟨by simp only; omega, by simp only; omega, hout⟩
    · simp only [hd, Bool.false_eq_true, ite_false] at hr
      obtain ⟨log1, hpush, hr⟩ := bind_ok_inv hr
      have hlog1 : log1.val = log.val ++ [Effect.Generate] :=
        by have hs := alloc.vec.Vec.push_spec log Effect.Generate (by scalar_tac)
           have h' := spec_ok_eq hs hpush
           exact h'
      obtain ⟨⟨rep, host1⟩, _, hr⟩ := bind_ok_inv hr
      obtain ⟨⟨host2, log2, outcome1, done2⟩, hm, hr⟩ := bind_ok_inv hr
      obtain ⟨round1, hadd, hr⟩ := bind_ok_inv hr
      have hround1 : round1.val = round.val + 1 :=
        by have hs := Usize.add_spec (x := round) (y := 1#usize) (by scalar_tac)
           have h' := spec_ok_eq hs hadd
           exact h'
      have := (Result.ok.injEq ▸ hr : _ = r)
      subst this
      simp only
      have hg1 : Statements.generates log1.val = round.val + 1 := by
        rw [hlog1, generates_append, hgen]
      have hl1 : Statements.lookups log1.val = Statements.lookups log.val := by
        rw [hlog1, lookups_append]; rfl
      -- What each reply leaves behind.
      have key : Statements.generates log2.val = round.val + 1 ∧
          Statements.lookups log2.val ≤ round.val + 1 ∧
          ∀ t, outcome1 = .ToolRefused t → t.val ≠ granted.val := by
        cases rep with
        | Text text =>
          have h := (Result.ok.injEq ▸ hm : _ = _)
          simp only [Prod.mk.injEq] at h
          obtain ⟨_, rfl, rfl, _⟩ := h
          refine ⟨hg1, by omega, ?_⟩
          intro t ht
          cases ht
        | Call tool query =>
          dsimp only at hm
          obtain ⟨b, hsame, hm⟩ := bind_ok_inv hm
          cases b with
          | false =>
            have h := (Result.ok.injEq ▸ hm : _ = _)
            simp only [Prod.mk.injEq] at h
            obtain ⟨_, rfl, rfl, _⟩ := h
            refine ⟨hg1, by omega, ?_⟩
            intro t ht
            injection ht with ht
            subst ht
            intro heq
            have hs2 := spec_ok_eq (same_spec _ _) hsame
            exact absurd (hs2 heq) (by simp)
          | true =>
            obtain ⟨log3, hpush3, hm⟩ := bind_ok_inv hm
            have hlog3 : log3.val = log1.val ++ [Effect.Lookup] :=
              by have hs := alloc.vec.Vec.push_spec log1 Effect.Lookup
                   (by rw [hlog1]; simp only [List.length_append, List.length_singleton]; scalar_tac)
                 have h' := spec_ok_eq hs hpush3
                 exact h'
            obtain ⟨⟨_, host3⟩, _, hm⟩ := bind_ok_inv hm
            have h := (Result.ok.injEq ▸ hm : _ = _)
            simp only [Prod.mk.injEq] at h
            obtain ⟨_, rfl, rfl, _⟩ := h
            refine ⟨?_, ?_, hout⟩
            · rw [hlog3, generates_append, hg1]; rfl
            · rw [hlog3, lookups_append, hl1]; simp only; omega
      obtain ⟨k1, k2, k3⟩ := key
      exact ⟨⟨by simp only; omega, by simp only; omega, by simp only; omega, k3⟩, by omega⟩
  · simp only [hR, ite_false] at hr
    have := (Result.ok.injEq ▸ hr : _ = r)
    subst this
    exact ⟨by simp only; omega, by simp only; omega, hout⟩

theorem respond_holds : Statements.respond_spec := by
  intro H inst host granted outcome log host' h
  unfold respond at h
  obtain ⟨⟨h1, l1, o1⟩, hloop, hr⟩ := bind_ok_inv h
  have hr' := (Result.ok.injEq ▸ hr : _ = _)
  simp only [Prod.mk.injEq] at hr'
  obtain ⟨⟨rfl, rfl⟩, rfl⟩ := hr'
  unfold respond_loop at hloop
  have hpost := loop_pc (fun s => 3 - s.2.2.1.val) (RInv granted) (RPost granted)
    _ (fun s hs r hr => by
        obtain ⟨a, b, c, d, e⟩ := s
        have key := respond_body_pc inst granted (a, b, c, d, e) hs r hr
        cases r
        · exact key
        · exact key) _
    ⟨by simp, by simp [Statements.generates], by simp [Statements.lookups], by simp⟩ _ hloop
  obtain ⟨hg, hl, ho⟩ := hpost
  simp only at hg hl ho
  refine ⟨hg, by omega, ?_, hl, ho⟩
  rw [length_eq_gen_add_look]; omega

end Proofs
