#!/usr/bin/env python3
"""Guard the hedging of the corpus's unproven claims against silent drift.

The corpus mechanises two drift guards already. Numeric drift is closed by
interpolation: a figure in a paper *is* the figure in `dist/evaluation.json`,
and typst enforces it by construction. Capability drift is closed by the
evaluation harness: a paper cannot say the artifact lacks something the artifact
has, because the harness runs the artifact. Both work because their property is
decidable against something.

Hedge drift has no such artifact. "Is this claim appropriately hedged?" is a
question about the relationship between a sentence's mood and a property's
evidential status, and the second half of that is not machine-readable. So this
check does not attempt it. What it does instead is narrower and decidable:

    Each pin below quotes, verbatim, a fragment of a paper in which an unproven
    claim and the qualification that bounds it appear *together*. The check
    asserts each fragment is still present, in the section it was pinned to.

That makes the two fail together. Delete the hedge and the fragment stops
matching. Rewrite the claim and the fragment also stops matching, which forces
whoever rewrote it to re-read the passage and re-seed the pin deliberately —
the same arrangement as the overhead band, where widening the band is an edit to
a claim rather than a tuning knob. A naive alternative — grepping a section for
`would` / `in a sound realisation` and requiring a minimum count — is satisfied
by a rewrite that keeps the vocabulary and moves it off the claim it was
qualifying, which is worse than no check because it converts a review obligation
into a green tick.

WHAT THIS IS NOT. This is a regression guard over the passages it pins, and
nothing more. It cannot tell that the *set* of pins is complete, it cannot tell
that a hedge qualifies the right claim in a fragment it has not seen, and the
pins are hand-maintained, so a wrong pin is as invisible here as a wrong row in
the derivation's mapping table (Paper 2 §7.1 admits the same weakness about
itself). No paper should describe it as more than this. AGENTS.md records the
review obligation that covers everything the pins do not.

Seeded from Paper 2 §2.5 (Security properties), which is the densest hedging in
the corpus and the passage most at risk: §2 describes intent inside a paper
otherwise written in the present tense, so a claim there reads as substantiated
unless its mood is deliberately kept conditional. Paper 1 is frozen and guarded
byte-for-byte by check-freeze.py instead.

Section numbers in the comments below are as seeded, before the 30 September
2026 merge renumbered Paper 2: §2.5 (security) is now §2.4, §3.4 (identity) is
§3.3.1, and §4.3 (the injection residual) is §4.4. The pins themselves are keyed
by label (`sec:...`), which the merge kept, so none needed re-seeding.

Usage:  uv run python3 scripts/check-hedges.py
"""

import re
import sys
from pathlib import Path

# A pin: (paper, section label, id, hedge marker, verbatim fragment).
#
#   paper     — path relative to the repository root
#   section   — the `<sec:...>` label whose body must contain the fragment, so a
#               fragment that survives by migrating elsewhere still fails here
#   id        — short name for the claim, so a failure report says which claim
#               lost its qualification rather than only which string vanished
#   hedge     — the marker doing the qualifying. Asserted at load time to be a
#               substring of the fragment, so a pin cannot be seeded without one
#   fragment  — claim and hedge together, quoted from the paper. Whitespace is
#               normalised on both sides before comparison; nothing else is
#
# Seeded 5 August 2026 against papers/02-demonstrator/proposal.typ §2.5.
PAPER2 = "papers/02-demonstrator/proposal.typ"

PINS = (
    # §2.3, the running example. Pinned alongside §2.5 because it carries the
    # third instance of the same claim, and all three had drifted the same way:
    # they described the principal binding as undesigned after §3.4 built it.
    # A claim understating the artifact is drift too, and nothing else catches
    # it — the evaluation harness only guards the overstating direction.
    (
        PAPER2,
        "sec:concrete-graph",
        "concrete-graph/user-scoped-untyped",
        "not yet typed",
        "bounding that further depends on user-scoped capabilities, which are "
        "bound at the instance but not yet typed",
    ),
    # §2.3's schema caveat: the residual's statement at the running example's
    # altitude. Its primary home with evidence is §4.4; what must survive here
    # is the qualification, without which the example promises what §4.4 then
    # measures as unclosed.
    (
        PAPER2,
        "sec:concrete-graph",
        "concrete-graph/schema-proviso",
        "holds only _provided",
        "the schema guarantee holds only _provided the schema excludes unbounded "
        "free text in positions flowing to privileged nodes_",
    ),
    (
        PAPER2,
        "sec:concrete-graph",
        "concrete-graph/no-untrusted-path",
        "in a sound realisation",
        "no direct path from untrusted input to a tool-capable LLM exists in the "
        "graph; in a sound realisation it would be ill-typed",
    ),
    # The section's framing sentence. Without "intended to" the whole of §2.5
    # reads as a report of what the artifact does rather than of a design's aim.
    (
        PAPER2,
        "sec:security",
        "security/framing",
        "intended to",
        "The capability-injection model is intended to provide guarantees "
        "qualitatively different from those achievable by code review or "
        "runtime monitoring.",
    ),
    # Injection attacks. The typed-query capability does not exist; the claim is
    # about what a capability of that shape would accept.
    (
        PAPER2,
        "sec:security",
        "injection/typed-queries",
        "would accept",
        "A SQL-executing capability would accept typed queries, not raw strings",
    ),
    (
        PAPER2,
        "sec:security",
        "injection/untrusted-cannot-reach",
        "could not",
        "so `Untrusted<string>` could not reach it without transiting a "
        "sanitisation node that produces a typed query",
    ),
    (
        PAPER2,
        "sec:security",
        "injection/ill-typed",
        "In a sound realisation",
        "In a sound realisation the pattern would be ill-typed.",
    ),
    # Privilege escalation. Three separate qualifications, each on a different
    # claim; design.md records that their order is deliberate.
    (
        PAPER2,
        "sec:security",
        "privilege/no-acquisition",
        "would not acquire",
        "A node would not acquire capabilities it was not given",
    ),
    (
        PAPER2,
        "sec:security",
        "privilege/cheri-unrun",
        "on which nothing here has run",
        "would extend to the memory level on CHERI hardware — on which nothing here has run",
    ),
    (
        PAPER2,
        "sec:security",
        "privilege/out-of-band-authority",
        "in principle",
        "a node holding a network capability can in principle acquire authority "
        "out-of-band from services the graph does not model",
    ),
    # Re-seeded 5 August 2026. The pin previously read "only as strong as an
    # undesigned principal binding", which had gone stale in the understating
    # direction: §3.4 binds a principal, propagates the RFC 8693 delegation
    # chain, and tests both. What is open is the *typed* form. Seeding this pin
    # is what surfaced it, so the hedge now bounds the claim the artifact
    # actually supports rather than a weaker one.
    (
        PAPER2,
        "sec:security",
        "privilege/principal-binding",
        "only as strong as",
        "for user-scoped operations the guarantee is only as strong as a "
        "principal binding that lives on the instance rather than in the "
        "capability's type",
    ),
    # The tier split. A property that holds only on the confined tier must say
    # so, or it reads as universal when the host tier demonstrably escapes.
    (
        PAPER2,
        "sec:security",
        "privilege/tier-split",
        "only as an object discipline",
        "the property holds on the confined tier and only as an object discipline on the host tier",
    ),
    (
        PAPER2,
        "sec:security",
        "supply-chain/tier-split",
        "only as an object discipline",
        "This holds as a property of the artifact on the confined tier and only "
        "as an object discipline a hostile library can reach around on the host "
        "tier",
    ),
    # Prompt injection. The residual is the boundary of the claim; §4.3 measures
    # it, and this is where §2 must not promise more than §4.3 delivers.
    (
        PAPER2,
        "sec:security",
        "prompt-injection/attenuated-not-eliminated",
        "not eliminated",
        "Structurally attenuated, not eliminated.",
    ),
    (
        PAPER2,
        "sec:security",
        "prompt-injection/well-typed-wiring",
        "would connect",
        "No well-typed wiring would connect an untrusted source to a "
        "tool-capable LLM without transiting a type that constrains the "
        "downstream payload",
    ),
    (
        PAPER2,
        "sec:security",
        "prompt-injection/free-text-residual",
        "stays adversarial",
        "a free-text field reaching an LLM-capable node stays adversarial even "
        "when its wrapper is non-`Untrusted`",
    ),
    # The confused deputy. Corrected at the same time and for the same reason as
    # privilege/principal-binding: the mechanism is built, and it is the typing
    # of it that is open. Pinned because that boundary is easy to slide in
    # either direction — into claiming a static property, or back into claiming
    # the mechanism is undesigned.
    (
        PAPER2,
        "sec:security",
        "prompt-injection/confused-deputy-untyped",
        "but does not type",
        "which @sec:identity binds and propagates but does not type",
    ),
    (
        PAPER2,
        "sec:security",
        "prompt-injection/schema-discipline",
        "depends on",
        "strength depends on schema discipline",
    ),
    # Covert channels. The known-hard problem is named and disclaimed, not
    # quietly folded into what the model closes.
    (
        PAPER2,
        "sec:security",
        "covert-channels/not-claimed",
        "is not claimed to close",
        "which general covert-channel elimination, a known-hard problem, is not claimed to close",
    ),
)

_HEADING = re.compile(r"^=+\s.*<(?P<label>sec:[A-Za-z0-9_-]+)>\s*$")


def normalise(text: str) -> str:
    """Collapse whitespace so a fragment matches across typst line breaks."""
    return re.sub(r"\s+", " ", text).strip()


def section_bodies(source: str) -> dict[str, str]:
    """Map each `<sec:...>` label to its body, up to the next heading of any level.

    Deliberately not recursive: a pin names the innermost labelled section its
    fragment sits in, so a fragment that migrates into a subsection of the same
    parent still fails. That is the intended strictness — a hedged claim moving
    to a different altitude is a change worth re-reading.
    """
    bodies: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in source.splitlines():
        match = _HEADING.match(line)
        if match:
            if current is not None:
                bodies[current] = normalise(" ".join(lines))
            current = match.group("label")
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        bodies[current] = normalise(" ".join(lines))
    return bodies


def malformed_pins(pins=PINS) -> list[str]:
    """Pins whose declared hedge is not inside the fragment it is meant to qualify.

    This is the guard on the guard: without it a pin can be seeded — or edited
    down — until it quotes a claim with no qualification left in it and still
    passes, which is exactly the green tick this check exists to avoid.
    """
    problems = []
    for _paper, _section, name, hedge, fragment in pins:
        if normalise(hedge) not in normalise(fragment):
            problems.append(f"{name}: hedge {hedge!r} is not present in its own pinned fragment")
    return problems


def find_violations(sources: dict[str, str], pins=PINS) -> list[str]:
    """Return a human-readable violation per pin whose fragment no longer holds.

    `sources` maps a paper path to its typst source, so the check is a pure
    function of text and its failure path is testable without touching the tree.
    """
    violations = []
    bodies_by_paper = {path: section_bodies(text) for path, text in sources.items()}
    for paper, section, name, hedge, fragment in pins:
        bodies = bodies_by_paper.get(paper)
        if bodies is None:
            violations.append(f"{name}: {paper} not found")
            continue
        body = bodies.get(section)
        if body is None:
            violations.append(f"{name}: {paper} has no section <{section}>")
            continue
        if normalise(fragment) not in body:
            where = (
                "elsewhere in the paper"
                if normalise(fragment) in normalise(sources[paper])
                else "nowhere in the paper"
            )
            violations.append(
                f"{name}: the pinned fragment is no longer in <{section}> ({where}).\n"
                f"      hedge:    {hedge}\n"
                f"      fragment: {normalise(fragment)}"
            )
    return violations


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    problems = malformed_pins()
    if problems:
        print("ERROR: a hedge pin is malformed:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    sources = {}
    for paper in {pin[0] for pin in PINS}:
        path = root / paper
        if path.exists():
            sources[paper] = path.read_text(encoding="utf-8")

    violations = find_violations(sources)
    if violations:
        print("ERROR: a pinned claim has lost its hedging:", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(
            "\nEach pin quotes a claim and the qualification that bounds it, together.\n"
            "If you shortened the passage: length is a target, hedging is a claim —\n"
            "miss the target and keep the hedge. If you rewrote the claim deliberately\n"
            "and it is still qualified, re-seed the pin in scripts/check-hedges.py and\n"
            "say so in the commit message.",
            file=sys.stderr,
        )
        return 1

    print(f"check-hedges: {len(PINS)} pinned claims still carry their hedging.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
