#!/usr/bin/env bash
# S3's gate: does lean/Proofs.lean prove the pinned statements about the pinned
# code, with nothing assumed? Exit 0 only if:
#   1. Statements.lean and Cores.lean match ../statements.sha256 (the specification
#      and the translated code are the gate's, not the prover's);
#   2. a text scan finds no axiom, opaque, kernel escape, or build-time code
#      execution command (defence in depth only: a macro can assemble any of them);
#   3. Cores and Statements build *first*, outside the proof's reach, and their
#      compiled .olean files are hashed;
#   4. Proofs builds inside a macOS sandbox with no network and no writes outside
#      the build directory (a proof file runs code at build time: the adversarial
#      review of 18 November 2026 wrote a file from `#eval`);
#   5. the compiled Cores/Statements are unchanged after that build;
#   6. audit/Audit.lean, a separate process that never elaborates the proof file,
#      finds each theorem's type to be *exactly* its statement constant, its axioms
#      within propext/Classical.choice/Quot.sound, and every non-Aeneas constant
#      accepted again by the kernel.
# Steps 3-6 replace the first gate's `#print axioms`, which the proof file itself
# could redefine with `macro_rules` (the review got three `sorry`s ACCEPTED).
# Takes no argument: it never copies a file over the committed Proofs.lean.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PROOF="$HERE/lean/Proofs.lean"
LOG="$(mktemp -t s3-check)"
cd "$HERE/lean"

shasum -a 256 -c "$HERE/statements.sha256" >/dev/null || {
  echo "REFUSED: the statements or the translated code changed"; exit 1; }

FORBIDDEN='^\s*(axiom|opaque|unsafe|@\[extern|@\[implemented_by|initialize|builtin_initialize)|debug\.skipKernelTC|native_decide|ofReduceBool|#eval|run_cmd|run_elab|run_meta|run_tac|IO\.|sorry|sorryAx'
if grep -nE "$FORBIDDEN" "$PROOF"; then
  echo "REFUSED: the proof file uses a forbidden construct"; exit 1
fi

lake build Cores Statements >"$LOG" 2>&1 || {
  echo "REFUSED: the pinned code does not build"; tail -20 "$LOG"; exit 1; }
OLEANS=".lake/build/lib/lean/Cores.olean .lake/build/lib/lean/Statements.olean"
before="$(shasum -a 256 $OLEANS)"

BUILD="$(cd .lake/build && pwd -P)"
PROFILE="(version 1)(allow default)(deny network*)(deny file-write*)
(allow file-write* (subpath \"$BUILD\") (subpath \"/private/var/folders\") (literal \"/dev/null\"))"
sandbox-exec -p "$PROFILE" lake build Proofs >"$LOG" 2>&1 || {
  echo "REFUSED: the proofs do not build (in the sandbox)"; tail -30 "$LOG"; exit 1; }

after="$(shasum -a 256 $OLEANS)"
[ "$before" = "$after" ] || {
  echo "REFUSED: building the proofs changed the compiled statements or code"; exit 1; }

lake env lean --run "$HERE/audit/Audit.lean" Proofs \
  Proofs.drop_seen_holds=Statements.drop_seen_spec \
  Proofs.one_line_holds=Statements.one_line_spec \
  Proofs.respond_holds=Statements.respond_spec || {
  echo "REFUSED: the audit failed"; exit 1; }
echo "ACCEPTED"
