#!/usr/bin/env bash
# S3/S4 toolchain: Aeneas (Rust → Lean 4) with its pinned Charon, and the Lean library
# its output imports. Pre-approved by the author on 18 November 2026 (task 0.1).
#
# Where things go:
#   - source checkouts: spikes/specified-architecture/s3/vendor/ (gitignored)
#   - opam's root: ~/.opam (its standard location), one switch named `aeneas`
#   - Lean toolchains: ~/.elan (elan's standard location)
#   - Rust toolchains Charon pins: ~/.rustup (rustup's standard location)
# Nothing here runs in any build step.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENDOR="$HERE/vendor"
mkdir -p "$VENDOR"
cd "$VENDOR"

[ -d aeneas ] || git clone --depth 50 https://github.com/AeneasVerif/aeneas.git
cd aeneas
echo "aeneas at $(git rev-parse --short HEAD)"

if [ ! -d "$HOME/.opam" ]; then
  opam init --bare -n -y
fi
if ! opam switch list --short | grep -qx aeneas; then
  opam switch create aeneas 5.3.0 -y
fi
eval "$(opam env --switch=aeneas --set-switch)"
opam install ./src --deps-only -y

# Aeneas's Makefile needs GNU make (`brew install make` provides `gmake` on macOS).
MAKE_BIN="$(command -v gmake || command -v make)"
"$MAKE_BIN" setup-charon || true   # its OCaml half may need the deps below first
# Charon's OCaml library has dependencies of its own (e.g. ppx_deriving_hash).
for opamfile in charon/charon-ml/*.opam charon/*.opam; do
  [ -f "$opamfile" ] && opam install "$opamfile" --deps-only -y || true
done
opam install ppx_deriving_hash -y || true
"$MAKE_BIN" setup-charon
"$MAKE_BIN"

echo "--- Lean library"
elan self update || true
cd backends/lean
cat lean-toolchain
lake exe cache get || true   # Mathlib's prebuilt oleans, if the library depends on it
lake build
echo "setup done"
