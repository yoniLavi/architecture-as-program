// Hand-written illustrative diagram: type error in direct wiring.
// Referenced from proposal.typ §3.1.
// Source of truth; compiled to dist/diagrams/typed-wiring.svg by the Makefile.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge

#set page(width: auto, height: auto, margin: 1em)
#set text(font: "New Computer Modern", size: 9pt)

#diagram(
  spacing: (34mm, 8mm),
  node-stroke: 0.6pt,
  node-inset: 8pt,
  edge-stroke: 0.6pt,

  node((0, 0), align(center)[
    *UserInputHandler* \
    #text(size: 7pt)[(HTTPRequest\<'POST', 'user:message'\>)] \
    #text(size: 7pt)[→ #text(fill: rgb("#b33"))[Untrusted\<UserMessage\>]]
  ]),

  node((1, 0), align(center)[
    *LLMOrchestrator* \
    #text(size: 7pt)[(#text(fill: rgb("#272"))[SanitisedPrompt]) → AgentResponse] \
    #text(size: 7pt, weight: "bold", fill: rgb("#46c"))[LLMClient\<\[respond, lookup\]\>]
  ]),

  edge(
    (0, 0), (1, 0), "->",
    stroke: 1pt + rgb("#b33"),
    label: text(size: 7pt, fill: rgb("#b33"))[
      ill-typed: Untrusted\<UserMessage\> ≠ SanitisedPrompt
    ],
    label-side: left, label-sep: 4pt,
  ),
)
