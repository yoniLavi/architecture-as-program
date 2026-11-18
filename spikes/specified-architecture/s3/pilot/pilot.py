"""S3's generation pilot (task 5.2): a model writes a proof (or a body and a proof),
and the gate decides. Approved by the author on 18 November 2026, within the Claude
Max subscription; no paid API.

    cd spikes/specified-architecture
    PYTHONPATH=../../scripts:../.. ../../.venv/bin/python -m s3.pilot.pilot [--dry-run]

Design, fixed before any trial runs (and committed before the first call):
- **Arms.** `proof`: the body is the shipped core (`s3/cores`, translated); the model
  writes the proof. `body+proof`: the model writes the Rust function and the proof;
  the harness splices the function into a copy of the crate, translates it with the
  pinned Charon and Aeneas, and checks the proof against the *pinned statement*.
- **Targets.** `drop_seen`, `one_line` (both arms), `respond` (proof arm only: its
  body is a loop over a trait, and the arm would mostly measure Rust, not proof).
- **Models.** `sonnet` and `opus` through `ClaudeCLIBackend` (no tools, safe mode,
  the usage ceiling). Three repetitions each.
- **Attempts.** One, then up to four repairs. A repair is shown the gate's refusal
  (the build's error lines, truncated), never anything else.
- **The gate** is the same as `s3/check.sh`: the statement is the pinned
  `Statements.lean` (hash-checked); no `axiom`, `opaque`, `sorry`, `native_decide`,
  kernel escape; it builds; `#print axioms` shows only propext, Classical.choice,
  Quot.sound.
- **Outcome per trial:** accepted on attempt k (1 to 5), or not accepted. Counts only.
- **Not measured:** whether a body+proof body equals the shipped one. The
  differential test (`s3/cores/tests`) is run on each accepted body and reported
  beside it, as information: the gate accepts any body its statement admits.

Records: one JSON line per trial in `runs/pilot.jsonl`, including every response.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from poc.llm import ClaudeCLIBackend, LLMRequest, ModelCallError, UsageLimitReached

S3 = Path(__file__).resolve().parents[1]
LEAN = S3 / "lean"
WORK = S3 / "pilot" / "work"
RUNS = S3 / "pilot" / "runs"
VENDOR = S3 / "vendor" / "aeneas"
SKILLS = VENDOR / "documentation" / "skills"

TARGETS = {
    "drop_seen": ("Statements.drop_seen_spec", ["contains", "drop_seen"]),
    "one_line": ("Statements.one_line_spec", ["is_space", "one_line", "truncate"]),
    "respond": ("Statements.respond_spec", None),
}
ARMS = {"proof": ["drop_seen", "one_line", "respond"], "body+proof": ["drop_seen", "one_line"]}
MODELS = ["sonnet", "opus"]
REPS = 3
MAX_ATTEMPTS = 5
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = re.compile(
    r"^\s*(axiom|opaque|unsafe|@\[extern|@\[implemented_by)|\bsorry\b|\badmit\b|"
    r"native_decide|debug\.skipKernelTC|ofReduceBool",
    re.M,
)

SYSTEM = (
    "You write Lean 4 proofs about Rust code translated to Lean by Aeneas. You have no "
    "tools: reply with the complete file(s) requested, in fenced code blocks, and nothing "
    "else. A checker builds your file with `lake build` against Aeneas's Lean library and "
    "rejects any `sorry`, `axiom`, `opaque`, `native_decide`, or dependence on axioms other "
    "than propext, Classical.choice and Quot.sound. You may not change the statement."
)


def pinned_ok() -> bool:
    lines = (S3 / "statements.sha256").read_text().split("\n")
    want = dict(reversed(line.split()) for line in lines if line.strip())
    got = hashlib.sha256((LEAN / "Statements.lean").read_bytes()).hexdigest()
    return want.get("Statements.lean") == got


def setup_work() -> None:
    """A Lean workspace sharing the prebuilt packages of `s3/lean`."""
    WORK.mkdir(parents=True, exist_ok=True)
    # Share s3/lean's prebuilt packages (Mathlib alone is gigabytes) by a symlink:
    # lakefile.toml's `packagesDir` was ignored, and Lake began compiling Mathlib.
    (WORK / ".lake").mkdir(exist_ok=True)
    if not (WORK / ".lake" / "packages").exists():
        (WORK / ".lake" / "packages").symlink_to(LEAN / ".lake" / "packages")
    (WORK / "lakefile.toml").write_text(
        'name = "pilot"\ndefaultTargets = ["Trial"]\n\n'
        f'[[require]]\nname = "aeneas"\npath = "{VENDOR / "backends" / "lean"}"\n\n'
        '[[lean_lib]]\nname = "Cores"\n\n[[lean_lib]]\nname = "Statements"\n\n'
        '[[lean_lib]]\nname = "Trial"\n'
    )
    shutil.copy(LEAN / "lean-toolchain", WORK / "lean-toolchain")
    # The manifest names Aeneas by a path relative to `s3/lean`; make it absolute.
    manifest = (LEAN / "lake-manifest.json").read_text()
    manifest = manifest.replace('"../vendor/aeneas/backends/lean"',
                                json.dumps(str(VENDOR / "backends" / "lean")))  # fmt: skip
    (WORK / "lake-manifest.json").write_text(manifest)
    shutil.copy(LEAN / "Statements.lean", WORK / "Statements.lean")


def run(cmd: list[str], cwd: Path, timeout: int = 1200) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def translate_body(rust: str, target: str) -> tuple[bool, str]:
    """Splice the model's functions into a copy of the crate and translate it."""
    crate = WORK / "crate"
    if crate.exists():
        shutil.rmtree(crate)
    shutil.copytree(S3 / "cores", crate, ignore=shutil.ignore_patterns("target", "*.llbc"))
    src = (crate / "src" / "lib.rs").read_text()
    for name in TARGETS[target][1]:
        # Remove the shipped definition of each function the model must write.
        src = re.sub(rf"\npub fn {name}\b.*?\n}}\n", "\n", src, flags=re.S)
    (crate / "src" / "lib.rs").write_text(src + "\n// ── written by the model ──\n" + rust + "\n")
    code, out = run([str(VENDOR / "charon" / "bin" / "charon"), "cargo", "--preset=aeneas"], crate)
    if code != 0:
        return False, "Charon refused the Rust:\n" + out[-3000:]
    code, out = run([str(VENDOR / "bin" / "aeneas"), "-backend", "lean", "-dest", str(WORK),
                     str(crate / "cores.llbc")], WORK)  # fmt: skip
    if code != 0:
        return False, "Aeneas refused the Rust:\n" + out[-3000:]
    return True, ""


def gate(lean: str, target: str) -> tuple[bool, str]:
    # SUPERSEDED (18 Nov 2026): this is the gate the pilot ran, kept as run. The
    # adversarial review fooled it (`macro_rules` over `#print axioms`; `sorryAx`
    # passes `\bsorry\b`; build-time `#eval`). Every accepted trial is re-checked
    # under `reaudit.hardened_gate`; use that for any new run.
    if not pinned_ok():
        raise RuntimeError("the pinned statements changed: harness fault, stopping")
    if FORBIDDEN.search(lean):
        return False, "REFUSED: the file uses sorry/admit/axiom/opaque or a kernel escape."
    (WORK / "Trial.lean").write_text(lean)
    code, out = run(["lake", "build", "Trial"], WORK)
    if code != 0:
        errs = [ln for ln in out.splitlines() if "error" in ln.lower() or ln.startswith("  ")]
        return False, "REFUSED: the file does not build.\n" + "\n".join(errs)[:4000]
    # The theorem must prove the pinned statement itself: `holds : True` builds too
    # (the smoke test found this hole in the first draft of the gate).
    stmt = TARGETS[target][0]
    (WORK / "Axioms.lean").write_text(
        f"import Trial\nexample : {stmt} := Trial.holds\n#print axioms Trial.holds\n"
    )
    code, out = run(["lake", "env", "lean", "Axioms.lean"], WORK)
    if code != 0 or "error" in out:
        return False, "REFUSED: `Trial.holds` does not prove the statement.\n" + out[-1500:]
    found = set(re.findall(r"[\w.]+", (re.search(r"\[(.*)\]", out) or [None, ""])[1]))
    if code != 0 or ("Trial.holds" not in out and "does not depend" not in out):
        return False, "REFUSED: no theorem `Trial.holds` was found.\n" + out[-1000:]
    if found - ALLOWED_AXIOMS:
        return False, f"REFUSED: depends on axioms {sorted(found - ALLOWED_AXIOMS)}"
    return True, "ACCEPTED"


def prompt(target: str, arm: str) -> str:
    stmt_name = TARGETS[target][0]
    statements = (LEAN / "Statements.lean").read_text()
    cores_rs = (S3 / "cores" / "src" / "lib.rs").read_text()
    cores_lean = (LEAN / "Cores.lean").read_text()
    docs = (
        (SKILLS / "proof-patterns.instructions.md").read_text()
        + "\n\n"
        + (SKILLS / "aeneas-tactics-quickref.instructions.md").read_text()
    )
    if arm == "proof":
        task = (
            f"Prove `{stmt_name}`. Reply with one Lean file in a ```lean block. It must "
            "begin with `import Statements` and contain `namespace Trial`, a theorem "
            f"`theorem holds : {stmt_name} := ...`, and `end Trial`; helper lemmas may "
            "precede it. The Rust and its Aeneas translation (`Cores.lean`, imported by "
            "`Statements`) are below."
        )
        material = f"Rust:\n```rust\n{cores_rs}\n```\n\nCores.lean:\n```lean\n{cores_lean}\n```"
    else:
        names = ", ".join(f"`{n}`" for n in TARGETS[target][1])
        task = (
            f"Write the Rust functions {names} (public, with the signatures used by the "
            f"statement and by each other) so that `{stmt_name}` holds, and prove it. "
            "Reply with a ```rust block holding exactly those functions (safe Rust that "
            "Aeneas can translate: no closures, no iterators, no `return` inside loops, "
            "no std methods beyond `Vec::new`, `push`, `len` and indexing), then a "
            "```lean block as follows. The harness translates your Rust to `Cores.lean` "
            "with Aeneas (names stay `cores.<function>`; a while loop becomes "
            "`<function>_loop` and `<function>_loop.body`). The Lean file must begin with "
            "`import Statements` and contain `namespace Trial`, "
            f"`theorem holds : {stmt_name} := ...`, and `end Trial`."
        )
        material = "The rest of the crate, for context:\n```rust\n" + cores_rs + "\n```"
    return (
        f"{task}\n\nThe statements:\n```lean\n{statements}\n```\n\n{material}\n\n"
        f"Aeneas's own guidance for proofs:\n{docs}"
    )


def blocks(text: str, lang: str) -> str | None:
    m = re.findall(rf"```{lang}\s*\n(.*?)```", text, re.S)
    return m[-1] if m else None


def trial(backend: ClaudeCLIBackend, target: str, arm: str) -> dict:
    record: dict = {"target": target, "arm": arm, "model": backend.model, "attempts": []}
    base = prompt(target, arm)
    feedback = ""
    for k in range(1, MAX_ATTEMPTS + 1):
        text = base if not feedback else (
            base + "\n\nYour previous reply:\n" + record["attempts"][-1]["response"]
            + "\n\nThe checker said:\n" + feedback + "\n\nReply with corrected file(s)."
        )  # fmt: skip
        started = time.time()
        resp = backend.generate(LLMRequest(system=SYSTEM, prompt=text, task="prove")).text
        attempt = {"k": k, "seconds": round(time.time() - started, 1), "response": resp}
        lean = blocks(resp, "lean")
        ok, verdict = False, "REFUSED: no ```lean block in the reply."
        if lean is not None and arm == "body+proof":
            rust = blocks(resp, "rust")
            if rust is None:
                verdict = "REFUSED: no ```rust block in the reply."
                lean = None
            else:
                translated, why = translate_body(rust, target)
                if not translated:
                    verdict, lean = why, None
        else:
            shutil.copy(LEAN / "Cores.lean", WORK / "Cores.lean")
        if lean is not None:
            ok, verdict = gate(lean, target)
        attempt["verdict"] = verdict[:2000]
        record["attempts"].append(attempt)
        if ok:
            record["accepted_on"] = k
            if arm == "body+proof":
                # Information, not a gate: does the accepted body behave as the shipped
                # one? `one_line_spec` admits an empty summary, so a gamed body passes
                # the gate and fails here.
                code, out = run(["cargo", "test", "--release", "--test", "differential",
                                 f"{target}_agrees"], WORK / "crate")  # fmt: skip
                record["differential_agrees"] = code == 0
                record["differential_tail"] = out[-1500:]
            return record
        feedback = verdict
    record["accepted_on"] = None
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the plan; call nothing")
    ap.add_argument("--only", default=None, help="target name, to run one target")
    args = ap.parse_args()
    plan = [(a, t, m, r) for a, ts in ARMS.items() for t in ts for m in MODELS
            for r in range(REPS) if args.only in (None, t)]  # fmt: skip
    print(f"{len(plan)} trials, at most {len(plan) * MAX_ATTEMPTS} model calls")
    if args.dry_run:
        print(len(prompt("drop_seen", "proof")), "characters in a proof-arm prompt")
        return
    setup_work()
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / "pilot.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["arm"], r["target"], r["model"], r["rep"]))
    for arm, target, model, rep in plan:
        if (arm, target, model, rep) in done:
            continue
        # 30 minutes per call: the first run's default 600s timed out an Opus proof
        # mid-generation and stopped the run (amended after 3 trials, 18 Nov 2026).
        backend = ClaudeCLIBackend(model=model, timeout=1800.0)
        try:
            rec = trial(backend, target, arm)
        except UsageLimitReached as e:
            print("usage ceiling reached; stopping:", e)
            return
        except ModelCallError as e:
            # A failed call is the harness's or the service's, never the model's
            # answer: the trial is void, recorded apart, and never counted.
            rec = {"target": target, "arm": arm, "model": model, "accepted_on": None,
                   "void": str(e)[:500], "attempts": []}  # fmt: skip
        rec["rep"] = rep
        with out.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(arm, target, model, rep, "accepted on", rec["accepted_on"])


if __name__ == "__main__":
    main()
