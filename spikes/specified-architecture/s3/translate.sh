#!/usr/bin/env bash
# Regenerate lean/Cores.lean from ../cores with the pinned Charon and Aeneas.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$HERE/vendor/aeneas"
(cd "$HERE/cores" && "$V/charon/bin/charon" cargo --preset=aeneas)
"$V/bin/aeneas" -backend lean -dest "$HERE/lean" "$HERE/cores/cores.llbc"
