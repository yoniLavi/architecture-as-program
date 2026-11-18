/-
The gate's audit, run as a separate process over the *compiled* environment:

    lake env lean --run ../audit/Audit.lean <Module> <theorem>=<statement> ...

It never elaborates the proof file, so nothing the proof declares (a `macro_rules`
rewriting `#print axioms`, notation, options) can reach it. The adversarial review
of 18 November 2026 got `sorry` proofs past the first gate exactly that way.

For each pair it checks:
- the theorem exists, is a `theorem`, and its type is *literally* the statement
  constant (no re-definition can satisfy this, since the statement is a different
  module's constant, pinned by the olean hashes `check.sh` takes);
- the axioms its value reaches, by walking the terms: only propext,
  Classical.choice and Quot.sound.
Then it replays every constant outside Aeneas's library (Cores, Statements, the
proof) through the kernel, as lean4checker does, so a declaration added by a
metaprogram that skipped the kernel is caught.
Prints `AUDIT OK` and exits 0, or names the failure and exits 1.
-/
import Lean
open Lean

def allowed : List Name := [``propext, ``Classical.choice, ``Quot.sound]

partial def reach (env : Environment) (n : Name) : StateM (NameSet × NameSet) Unit := do
  let (seen, axs) ← get
  if seen.contains n then return
  set (seen.insert n, axs)
  match env.find? n with
  | some (.axiomInfo _) => modify fun (s, a) => (s, a.insert n)
  | some ci =>
    -- `allowOpaque := true`: without it `value?` returns nothing for a theorem, and
    -- the walk never looks inside a proof (the first draft's bug: it reported only
    -- `Classical.choice` where `#print axioms` reports three). Mirrors Lean's own
    -- `CollectAxioms.collect`, including an inductive's constructors.
    let deps := ci.type.getUsedConstants ++
      ((ci.value? (allowOpaque := true)).map (·.getUsedConstants)).getD #[]
    let ctors := match ci with | .inductInfo v => v.ctors.toArray | _ => #[]
    for d in deps ++ ctors do reach env d
  | none => modify fun (s, a) => (s, a.insert (`missing ++ n))

def main (args : List String) : IO UInt32 := do
  let some modStr := args.head? | IO.eprintln "usage: Audit <Module> thm=stmt ..."; return 2
  initSearchPath (← findSysroot)
  -- No extensions: loading them would run the imported modules' initializers,
  -- including any the proof file declares. Constants are all the audit needs.
  let env ← importModules #[{ module := modStr.toName }] {} (trustLevel := 0)
  let mut ok := true
  for pair in args.tail do
    let [thmS, stmtS] := pair.splitOn "=" | IO.eprintln s!"bad pair {pair}"; return 2
    let thm := thmS.toName
    let stmt := stmtS.toName
    match env.find? thm with
    | some (.thmInfo info) =>
      if info.type != .const stmt [] then
        IO.println s!"FAIL {thm}: its type is not the constant {stmt}"
        ok := false
      let ((), (_, axs)) := (reach env thm).run ({}, {})
      let bad := axs.toList.filter (fun a => !allowed.contains a)
      IO.println s!"{thm}: axioms {axs.toList}"
      if !bad.isEmpty then
        IO.println s!"FAIL {thm}: disallowed axioms {bad}"
        ok := false
    | some _ => IO.println s!"FAIL {thm}: not a theorem"; ok := false
    | none => IO.println s!"FAIL {thm}: not found"; ok := false
  -- Kernel replay of everything not in Aeneas's library (which the gate trusts).
  let base ← importModules #[{ module := `Aeneas }] {} (trustLevel := 0)
  let mut fresh : Std.HashMap Name ConstantInfo := {}
  for (n, ci) in env.constants.toList do
    if (base.find? n).isNone then fresh := fresh.insert n ci
  try
    discard <| base.toKernelEnv.replay fresh
    IO.println s!"kernel replay: {fresh.size} constants re-checked"
  catch e =>
    IO.println s!"FAIL kernel replay: {e}"
    ok := false
  IO.println (if ok then "AUDIT OK" else "AUDIT FAILED")
  return if ok then 0 else 1
