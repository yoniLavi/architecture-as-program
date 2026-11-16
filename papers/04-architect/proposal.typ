// Document setup
#set document(
  title: "Reviewed Before It Runs: Automated Review of an Architect's Authority",
  author: ("Yoni Lavi"),
  date: datetime(year: 2026, month: 11, day: 16),
)
#set page(margin: 2.5cm, numbering: "1")
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true)

// ── Evidence ───────────────────────────────────────────────────────
//
// Every figure in this paper is interpolated from three generated artifacts, and
// nothing is transcribed, counts of things in the data included:
//
// - dist/architect.json (poc/architect/report.py): the registered pretext
//   experiment (`reg`), the AgentDojo measurement (`meas`), and the pilot. Counts
//   the sections only imply are in `counts` (`k`); every non-integer figure is a
//   pre-formatted string in `display` (`ad`), so the PDF and the web copies state
//   one string.
// - dist/agentdojo-banking.json (poc/agentdojo/report.py): the banking corpus and
//   the undefended baseline.
// - dist/slice.json (poc/slice/report.py): only its `post_hoc` block (`ph`), the
//   two replays over the registered records. They are post-hoc analyses, labelled
//   so wherever cited, in their own subsection, never pooled with the registered
//   figures and never tested against them (the author, 16 November 2026).
//
// Never pooled: the registered run, the pilot and the AgentDojo measurement are
// kept apart in every table and sentence.
//
// Trials and grants are different units. `reg.conditions.*.unseen` and
// `k.registered.total.unseen` count trials; `k.registered.unseen_grants` counts
// grants, which is the unit of the scope-binding replay. Name the unit every time.
//
// Paper 2's and Paper 3's figures are cited from those papers, never stated here.
#let arch = json("/dist/architect.json")
#let bank = json("/dist/agentdojo-banking.json")
#let slice = json("/dist/slice.json")
#let reg = arch.registered
#let meas = arch.measured
#let k = arch.counts
#let ad = arch.display
#let ph = slice.post_hoc
#let conf = reg.confirmatory

// Title block
#align(center)[
  #text(size: 16pt, weight: "bold")[
    Reviewed Before It Runs: \
    Automated Review of an Architect's Authority
  ]
]

#align(center)[
  #text(size: 12pt)[Yoni Lavi] \
  #text(size: 10pt, style: "italic")[Codeliance]
]

#align(center)[
  #text(size: 11pt)[November 2026]
]

#align(center)[
  #text(size: 9pt)[Draft · not yet published]
]

// One line on purpose: pandoc's typst reader drops the space at a soft line break here.
#align(center)[
  #block(width: 85%)[
    #set text(size: 9pt, style: "italic")
    Fourth paper in a corpus on architecture-as-program, following the founding vision @lavi_architecture_2026, the demonstrator @lavi_confinement_2026, and the generation experiment @lavi_granted_2026.
  ]
]

#v(1em)

= Introduction <sec:intro>

= Setting <sec:setting>

= The pipeline <sec:pipeline>

= Method <sec:method>

= Results <sec:results>

== The confirmatory test <sec:results-confirm>

== Post-hoc analyses <sec:results-posthoc>

== AgentDojo <sec:results-agentdojo>

= Related work <sec:related>

= Limitations <sec:limits>

= Future work <sec:future>

= Conclusion <sec:conclusion>

#bibliography("/citations.bib", style: "ieee")
