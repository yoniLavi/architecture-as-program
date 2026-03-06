#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge

#set page(width: auto, height: auto, margin: 1.5em)
#set text(font: "New Computer Modern", size: 9pt)

#let cap(body) = text(size: 7pt, fill: luma(100), body)
#let llm-cap(body) = text(size: 7pt, weight: "bold", fill: rgb("#46c"))[#body]
#let trust-color = rgb("#b33")
#let ok-color = rgb("#272")
#let err-color = rgb("#b33")
#let esc-color = rgb("#c80")

#let untrusted-bg = rgb("#fef0f0")
#let trusted-bg = rgb("#f0f7f0")

#diagram(
  spacing: (28mm, 15mm),
  node-stroke: 0.6pt,
  node-inset: 8pt,
  edge-stroke: 0.6pt,

  // Trust zone backgrounds (enclose actual node positions; inset controls padding)
  node(enclose: ((-0.55, -0.15), (0, 0), (0, 1)),
    stroke: 1pt + trust-color,
    fill: untrusted-bg,
    corner-radius: 5pt,
    inset: 10pt,
    snap: -1,
    name: <untrusted>),

  node(enclose: ((-1.5, 2.0), (0, 2.2), (-1.2, 3.4), (0, 3.4), (1.2, 3.4), (0, 4.4), (0, 5.4), (1.2, 5.4)),
    stroke: 1pt + ok-color,
    fill: trusted-bg,
    corner-radius: 5pt,
    inset: 10pt,
    snap: -1,
    name: <sanitised>),

  // Zone labels (placed well inside each zone's top-left area)
  node((-0.55, -0.15),
    text(size: 7pt, weight: "bold", fill: trust-color)[UNTRUSTED],
    stroke: none, inset: 0pt),
  node((-1.5, 2.0),
    text(size: 7pt, weight: "bold", fill: ok-color)[SANITISED],
    stroke: none, inset: 0pt),

  // === Untrusted zone ===
  node((0, 0), [*ReceiveMessage*\ #cap[(pure)]]),
  node((0, 1), [*SanitiseInput*\ #cap[(pure)]]),

  // === Sanitised zone ===
  node((0, 2.2), align(center)[*ModerateContent*\ #llm-cap[LLMClient\<no-tools\>]]),

  // Three branches
  node((-1.2, 3.4), align(center)[*NotifyUser*\ #cap[WebSocket\<user-session\>]]),
  node((0, 3.4), align(center)[*FetchContext*\ #cap[DBHandle\<'kb', read\>]]),
  node((1.2, 3.4), align(center)[*EscalateToHuman*\ #cap[EventEmitter\<'support-queue'\>]]),

  // Success path continues
  node((0, 4.4), align(center)[*GenerateResponse*\ #llm-cap[LLMClient\<\[lookup\]\>] \ #cap[DBHandle\<'kb', read\>]]),
  node((0, 5.4), align(center)[*SendReply*\ #cap[WebSocket\<user-session\>]]),
  node((1.2, 5.4), align(center)[*HandleLLMError*\ #cap[WebSocket\<user-session\>]]),

  // === Edges ===
  edge((0, 0), (0, 1), "->",
    label: text(size: 7pt, fill: trust-color)[Untrusted\<UserMessage\>],
    label-side: right),

  edge((0, 1), (0, 2.2), "->",
    label: text(size: 7pt)[UserMessage],
    label-side: right),

  edge((0, 2.2), (-1.2, 3.4), "->",
    label: text(size: 7pt, fill: err-color)[violation],
    label-side: left),
  edge((0, 2.2), (0, 3.4), "->",
    label: text(size: 7pt, fill: ok-color)[safe],
    label-side: right),
  edge((0, 2.2), (1.2, 3.4), "->",
    label: text(size: 7pt, fill: esc-color)[escalate],
    label-side: right),

  edge((0, 3.4), (0, 4.4), "->",
    label: text(size: 7pt)[ConversationContext],
    label-side: right),
  edge((0, 4.4), (0, 5.4), "->",
    label: text(size: 7pt, fill: ok-color)[ok],
    label-side: left),
  edge((0, 4.4), (1.2, 5.4), "->",
    label: text(size: 7pt, fill: err-color)[error],
    label-side: right),
)
