#!/usr/bin/env bash
# S3's gate: does Proofs.lean prove the pinned statements about the pinned code,
# with nothing assumed? Exit 0 only if:
#   1. Statements.lean and Cores.lean match ../statements.sha256 (the specification
#      and the translated code are the gate's, not the prover's);
#   2. Proofs.lean declares no axiom, opaque constant, or kernel escape;
#   3. it builds;
#   4. every theorem depends on no axiom beyond propext, Classical.choice and
#      Quot.sound (so no sorryAx, no Lean.ofReduceBool, no Lean.trustCompiler).
# Usage: check.sh [proof-file]   (default lean/Proofs.lean)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PROOF="${1:-$HERE/lean/Proofs.lean}"
cd "$HERE/lean"

shasum -a 256 -c "$HERE/statements.sha256" >/dev/null || {
  echo "REFUSED: the statements or the translated code changed"; exit 1; }

if grep -nE '^\s*(axiom|opaque|unsafe|@\[extern|@\[implemented_by)|debug\.skipKernelTC|native_decide|ofReduceBool' "$PROOF"; then
  echo "REFUSED: the proof file declares an axiom or escapes the kernel"; exit 1
fi

if [ "$PROOF" != "$HERE/lean/Proofs.lean" ]; then cp "$PROOF" "$HERE/lean/Proofs.lean"; fi
lake build Proofs >/tmp/s3-check-build.log 2>&1 || {
  echo "REFUSED: the proofs do not build"; tail -30 /tmp/s3-check-build.log; exit 1; }

cat > /tmp/s3-axioms.lean <<'EOF'
import Proofs
#print axioms Proofs.drop_seen_holds
#print axioms Proofs.one_line_holds
#print axioms Proofs.respond_holds
EOF
out="$(lake env lean /tmp/s3-axioms.lean 2>&1)"
echo "$out"
if echo "$out" | grep -qE "sorryAx|ofReduceBool|trustCompiler|error"; then
  echo "REFUSED: a theorem depends on a forbidden axiom"; exit 1
fi
bad="$(echo "$out" | grep -oE "\[[^]]*\]" | tr -d '[]' | tr ',' '\n' | sed 's/^ *//' \
  | grep -vE '^(propext|Classical\.choice|Quot\.sound)?$' || true)"
if [ -n "$bad" ]; then echo "REFUSED: unexpected axioms: $bad"; exit 1; fi
echo "ACCEPTED"
