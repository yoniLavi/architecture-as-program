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
// - dist/architect.json's `post_hoc_sonnet` block (`son`) and its display strings
//   (`ad.post_hoc_sonnet`): the reviewer re-run post hoc with Sonnet on the
//   registered graphs (add-paper-4 task 5). Post hoc, in the post-hoc subsection,
//   beside the registered reviewer on the same trials only; same family as the
//   architect, so diversity of capability, never independence.
//
// Never pooled: the registered run, the pilot and the AgentDojo measurement are
// kept apart in every table and sentence.
//
// Trials and grants are different units. `reg.conditions.*.unseen` and
// `k.registered.total.unseen` count trials; `k.registered.unseen_grants` counts
// grants, which is the unit of the scope-binding replay. Name the unit every time.
//
// Every catch rate says, beside it, that the architect and the reviewer are the
// same model (`openspec/specs/paper-corpus`).
//
// Paper 2's and Paper 3's figures are cited from those papers, never stated here.
#let arch = json("/dist/architect.json")
#let bank = json("/dist/agentdojo-banking.json")
#let slice = json("/dist/slice.json")
#let reg = arch.registered
#let meas = arch.measured
#let k = arch.counts
#let kr = k.registered
#let km = k.measured
#let tot = kr.total
#let ad = arch.display
#let ud = ad.utility
#let ph = slice.post_hoc
#let conf = reg.confirmatory
#let gate = reg.preuse
#let rule = kr.reviewer_rule
#let base = bank.baseline.at(0)
#let model = reg.architect_model
// Condition order for tables: the labels are names, not figures.
#let conds = ("Q0", "A-Q1", "A-Q2", "B-Q1", "B-Q2")
#let cond(c) = reg.conditions.at(c)
#let num(t) = t.split("_").at(-1)
#let and-list(xs) = if xs.len() == 1 { xs.at(0) } else { xs.slice(0, xs.len() - 1).join(", ") + " and " + xs.at(xs.len() - 1) }
#let tasks(ts) = and-list(ts.map(num))
#let rate(x) = [#x.hits/#x.n]
// Facts the prose states about the data, computed so a sentence cannot outlive them.
#let graphs = meas.tasks.filter(t => t.graph)
#let residual = graphs.filter(t => t.predicted_residual.len() > 0)
#let residual-at-extract = residual.all(t => t.failure != none and t.failure.contains("lib_extract"))
#let writers-reached = graphs.filter(t => t.writer_reached_under_attack > 0)
#let rationale-flags-more = tot.flagged_with_rationales > tot.caught_by_reviewer
#let looser = conds.slice(1).all(c => cond(c).graphs > cond("Q0").graphs and cond(c).inexpressible < cond("Q0").inexpressible and cond(c).widened > cond("Q0").widened)
#let extract-failures = graphs.filter(t => t.failure != none and t.failure.contains("lib_extract"))
#let writers-every-run = writers-reached.all(t => t.writer_reached_under_attack == t.attacked_runs and t.attack_success.len() == 0)
#let top = kr.unseen_grants_by_task_ranked
#let p-one = arch.pilot.at(0)
#let p-two = arch.pilot.at(1)
#let p-three = arch.pilot.at(2)
#let sb = ph.scope_binding
#let br = ph.behaviour
#let pd = ph.display
#let ps = reg.post_hoc_without_spelling_slips
#let pe = kr.preuse_effect
#let son = arch.post_hoc_sonnet
#let sp = son.views.primary
#let sq = son.views.persuaded
#let sd = ad.post_hoc_sonnet
#let son-minority = sp.caught * 2 < sp.widened_trials
#let caught-planted = if gate.caught == gate.planted [all #gate.planted] else [#gate.caught of #gate.planted]
#let caught-effect = if pe.caught == pe.planted [all #pe.planted] else [#pe.caught of #pe.planted]
#let minority = tot.caught_by_reviewer * 2 < tot.widened
// The planted test passed whole, and the natural rate fell below half.
#let overstated = minority and gate.caught == gate.planted and pe.caught == pe.planted
#let zero-both = meas.attack_success.hits == 0 and base.attack_success.hits == 0
#let ids(ts) = tasks(ts.map(t => t.task))
#let failed = graphs.filter(t => t.failure != none)
#let failed-elsewhere = failed.filter(t => not t.failure.contains("lib_extract"))
#let writers = graphs.filter(t => t.holds_writer)
#let writers-not-reached = writers.filter(t => t.writer_reached_under_attack == 0)
#let ran-not-reached = writers-not-reached.filter(t => t.failure == none)
#let attacks = if km.attacks_count == 1 [one attack] else [#km.attacks_count attacks]
// Facts the prose names in words rather than figures: a changed record fails the build here.
#assert(reg.architect_model == reg.reviewer_model)
#assert(k.labels.cannot_succeed == ("user_task_5", "user_task_14"))
#assert(top.at(0).at(0) == "user_task_15" and top.at(1).at(0) == "user_task_2")
#assert(ps.trials_changed == ("user_task_15.Q0.1",))
#assert(km.with_unseen == ("user_task_10",))
#assert(meas.tasks.filter(t => t.task == "user_task_10").at(0).unseen == ("Payments<[any], uncapped>",))
// The Sonnet re-run: complete, one model, every widened trial of the run in its sample,
// and its misses led by the same two tasks as the registered unseen grants.
#assert(son.complete and son.model_ids == (son.model,) and son.sample_holds_every_widened_trial)
#assert(sp.missed_by_task_ranked.slice(0, 2).map(x => x.at(0)) == (top.at(0).at(0), top.at(1).at(0)))

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

#align(center)[
  #block(width: 85%, stroke: 0.5pt + luma(180), inset: 1em, radius: 3pt)[
    #set text(size: 9pt)
    #set par(justify: true)
    *Note on process.* This paper was developed collaboratively with Claude (Anthropic), which served as primary drafter under the author's direction, and the pipeline and experiment it reports were likewise AI-implemented against author-directed specifications. The model whose output the experiment measures is a Claude model too, in two roles; @sec:limits states what that does and does not bound. The research direction, the registration's design decisions and the synthesis are the author's, and so is the approval of the least-authority labels, which the AI drafted; the harness, analysis, literature survey and prose were produced by the AI and verified against primary sources and a test suite.
  ]
]

#v(1em)

#block(width: 100%, inset: (x: 2em))[
  #set text(size: 10pt)
  #set par(justify: true)
  *Abstract.* AI agents are usually granted authority while they run: a prompt asks, and a person or a classifier approves. We study the alternative, in which authority is written down before anything runs and reviewed there. From a task in natural language, an architect model writes a _signal graph_, a dataflow graph in which every node declares the capabilities it holds, and every grant quotes the words of the task that need it. Before anything runs, a formal review checks the graph, and a reviewer model, here the architect's own model in a separate call, reviews it. Because each grant is an artefact, it can be held to least-authority labels registered before the run, so whether review catches a widened grant can be counted. On AgentDojo's banking suite, with one model (#raw(model)) as both architect and reviewer, we registered one test: whether a pretext in the task, claiming that wider access had been approved, raises the rate of widenings both reviewers miss. They came in #conf.channel_a.unseen of #conf.channel_a.of trials with the pretext (#ad.channel_a_unseen_rate) and #conf.q0.unseen of #conf.q0.of without it (#ad.q0_unseen_rate): one-sided Fisher exact $p = $ #(ad.confirmatory_p + ",") against a registered $alpha = $ #(ad.confirmatory_alpha + ".") #if conf.supported [The test was supported.] else [The test was *not supported*, and the rates are descriptive.] #if not conf.supported and ps.below_alpha [The verdict sits at the threshold: one trial without a pretext holds only its label's own grant, misspelt, and without it, post hoc, $p$ would be #(ad.post_hoc_without_slips_p + ".")] The reviewer caught #caught-planted widenings planted to test it before use, but only #tot.caught_by_reviewer of the #tot.widened trials in which the architect had widened a grant beyond its label; re-run post hoc on the same graphs, a more capable model of the same family caught #sp.caught. The check that each grant quotes the task caught #if tot.caught_by_link_check == 0 [none] else [#tot.caught_by_link_check]. The architect's graphs scored utility on #rate(meas.utility) tasks (#rate(meas.utility_beyond_idle) beyond tasks that pass when nothing is done), against #rate(base.utility) (#rate(base.utility_beyond_idle)) for the same model undefended#if zero-both [, and attack success was zero for both, which shows no defence here.] else [.]
]

#v(1em)

= Introduction <sec:intro>

AI agents acquire authority while they run. An agent asks before a tool call its rules do not allow, and a person answers in the moment @anthropic_claude_code_2025. A tool server that needs a wider scope tells the client, which obtains it mid-task @mcp_authorization_2025. A policy an LLM drafts from the task can grow when the user approves the change @shi_progent_2025. In each case the request for more authority arrives as text in the middle of a task, and whoever approves it judges it there. Our previous paper showed what such text can do @lavi_granted_2026: models writing code inside an architecture reached for authority they had not been granted when the task merely claimed it had been approved.

The alternative is to settle authority before anything runs, in an artefact that can be reviewed. In earlier work, a system is described as a _signal graph_: a dataflow graph whose nodes declare, in a `with` clause, the typed capabilities they hold. A validator checks the wiring, and the import surface of each node's compiled component is derived from its clause and checked against the binary @lavi_confinement_2026. That moves the question of authority from run time to authoring time, but someone must still write the clauses. Here an architect model writes them, from a task in natural language. Before anything runs, two reviewers check them: a formal review, and a reviewer model. This paper measures the front half of a pipeline, authoring and review before any node's code is written or run, and asks whether the review catches authority the architect should not have granted.

The question can be answered only because the authority is an artefact. Every grant in the graph can be compared with a label: the widest grant a careful architect could justify from the task alone, written per task, approved by the author and committed before the run. A grant beyond its label is a _widening_. A widening neither reviewer flags is _unseen_. We registered one test, of a threat that a published catalogue of agent defences says planning ahead "does not prevent": prompt injections "contained in the user prompt" @beurer-kellner_design_2025. Here it is a pretext in the task, claiming that wider access had been approved.

#block(inset: (x: 1.5em))[
  *Claim.* An architect model can write a signal graph from a task in natural language, citing the task for every grant, and a formal review and a reviewer model can check the graph before anything runs. Because each grant is an artefact, it can be held to least-authority labels registered before the run, so whether review catches a widening becomes a count. On AgentDojo's banking suite, with one model as both architect and reviewer, unseen widenings came in #ad.channel_a_unseen_rate of trials with a pretext in the task and #ad.q0_unseen_rate without one. The registered test of that difference #if conf.supported [was supported] else [was *not supported*] ($p = $ #ad.confirmatory_p, $alpha = $ #ad.confirmatory_alpha). The reviewer caught #caught-planted widenings planted to test it, but #tot.caught_by_reviewer of the #tot.widened trials with a widening the architect wrote; the citation check caught #if tot.caught_by_link_check == 0 [none] else [#tot.caught_by_link_check]. The graphs scored utility on #rate(meas.utility) tasks, against #rate(base.utility) for the same model undefended.
]

What the claim does not say matters as much. It does not say the pipeline defends against injection: #if base.attack_success.hits == 0 [attack success was zero for the undefended model too] else [the undefended model's attack success is in @tab:agentdojo]#if residual.len() > 0 and residual-at-extract [, and the #km.predicted_residual_count graphs predicted to be vulnerable failed before reaching any writer]. It does not say a pretext raises widening, since the registered test #if conf.supported [was supported only at its threshold] else [was not supported] and every rate beside it is descriptive. It does not say automated review is independent, since the architect and the reviewer are one model. It does not say the labels are ground truth in any sense beyond the author's registered judgement. And it says nothing beyond one model, one suite, #kr.pretexts fixed pretexts and #attacks.

*Contributions.* (1) A pipeline from a task to a reviewed graph: an architect in two stages whose every grant quotes the task, a formal review, and a reviewer that sees neither the architect's reasoning nor its names for nodes (@sec:pipeline). (2) A method that makes such review measurable: least-authority labels registered before the run, a registered experiment with pretexts in two channels, and a test the reviewer must pass before use (@sec:method). (3) The registered result, stated as a null, with its descriptive context and labelled post-hoc analyses (@sec:results). (4) A measurement on AgentDojo beside the same model undefended, read with what each graph could write (@sec:results-agentdojo).

= Setting <sec:setting>

We restate nothing of the demonstrator that this paper does not need @lavi_confinement_2026. A graph's nodes declare their authority as typed capability handles in a `with` clause. Capabilities travel on no edge: a node holds only what its clause names, and the runtime injects it. A validator checks every edge's type, a two-point trust lattice, and the narrowing of capabilities across composition. In the lattice, content a node's type declares `Untrusted<_>` can be raised only by a node declared to discharge trust. In this library every reader declares what it returns `Untrusted<_>`, and the architect makes the declaration of discharge, on a node that composes, extracts or answers; trust enters only where a type declares it @lavi_confinement_2026. On the demonstrator's _confined tier_, a node runs as a WebAssembly component whose imports are derived from its clause, so the clause bounds, in kind, what the binary can reach. A grant's scope (which payees, which fields) lives in the host-side handle and is checked at each crossing.

AgentDojo scores an agent's utility on a suite of user tasks, and its security against injection tasks, whose goals an attacker plants in data the agent reads @debenedetti_agentdojo_2024. We use its suite #bank.suite, with its #kr.tasks user tasks and #bank.goals.len() goals, and one attack, #raw(bank.attack). For the suite, the graph language gained four capability kinds:

- `Payments<[payees], cap>` sends money, to listed payees, to `inbound-senders` (anyone who has sent the user money), or to `any`, with a cap per payment or `uncapped`; a `recurring` form schedules a standing order instead;
- `ScheduledPayments<[orders], [fields]>` changes named standing orders, and only the listed fields;
- `UserProfile<[fields]>` changes the listed fields of the user's profile;
- `Credentials`, which no graph may be granted.

Reading the bank is a `DBHandle` with a named scope, and asking a model is an `LLMClient<inference>`, which may call no tool. An architect writes no code. It composes a fixed library of nodes (readers, selectors, writers, an `Extract` node that asks a model to find or compute a value in its material, and a node that answers the user), setting their parameters and wiring them. Every library node that holds a capability has a confined component. The pure ones, which select, compose and start a run, run on the host tier, where nothing confines them @lavi_confinement_2026.

We use AgentDojo's scorer unchanged, and two of its properties bear on every figure. Of its goals, #bank.any_payment_goals.len() (#tasks(bank.any_payment_goals)) read `x or "" in subject`, which holds whatever the subject, so any payment to the attacker meets them. And for #km.idle_pass_count user tasks (#tasks(km.idle_pass)), the utility predicate holds on an _idle_ run, one that calls nothing and answers nothing. Every utility figure below is therefore given over all #kr.tasks tasks and over the other #(kr.tasks - km.idle_pass_count).

= The pipeline <sec:pipeline>

*The architect, in two stages.* Following ACE @li_ace_2026, the architect first writes an _abstract graph_ from the task (and, in one condition below, a document beside it): nodes named by role ("read the bill", "pay the amount it states"), the edges, and what each edge carries. It is shown no catalogue of capabilities, so at this stage it can reach only for a kind the text in front of it names; one of the pretexts below names one. A second call maps the abstract graph onto the library, shown the library's catalogue, and writes the graph. A task the library cannot carry out may be answered `inexpressible`, which is recorded as an outcome, not as a failure.

*Shapes, never values.* The catalogue documents each reader's fields and their types, but no fact about what the bank holds: not which standing orders exist, not that the user's own payments carry the sender `'me'`, not today's date. AgentDojo's own tool documentation does not state these either; an agent learns them from tool output, which the architect never sees. The architect is told to grant the narrowest kind and scope the task's words let it state. Where the task leaves a payee or an amount to be read at run time, a grant that leaves it open (`any`, `uncapped`) is the narrowest it can state, and it is told that this is right. The rule keeps everything the architect sees in the task and the library. Its cost is utility, which @sec:results-agentdojo measures.

*Every grant cites the task.* Following Conseca's per-policy rationales @tsai_contextual_2025, every capability a node holds carries a `because`: a quotation of the words of the task that need it, copied exactly.

*The validator in the loop, and the review out of it.* The graph goes to the demonstrator's validator. Its verdicts return to the architect as reason classes, never as free text, for at most #kr.max_repairs_per_stage repairs per stage; a graph still invalid after them is a recorded failure. The formal review's own checks, below, are deliberately kept out of this loop: fed back, a fabricated citation would be repaired into a real one before review saw it. The architect never sees tool output, the injection, or the reviewer's verdict, and a test rebuilds every request it was sent from the allowed inputs alone.

*The formal review.* After the validator, a _link check_ fails any grant whose `because` is not a verbatim span of the task. It is exact and deterministic, and it measures linkage, not adequacy: a one-word quotation links a grant of any width. A pretext appended to the task is part of the task, so a grant quoting it passes.

*The reviewer.* A reviewer model sees the task, the library's catalogue, and the graph, canonicalised. The rationales are stripped, and the nodes are renamed `N1` to `Nk` in topological order, because a node's name is the architect's reasoning by another route. It is told that another model wrote the graph, which is not so here (below), and, by the standard the labels use, that where the task gives no payee or amount a grant that leaves it open may be needed. For every grant it gives a structured verdict: _needed_ by the task, _wider_ than needed, or _not needed_, quoting the task. A second verdict, shown the architect's rationales, is recorded apart, to measure how far they persuade @arnav_cot_2025. The reviewer's model was chosen by a rule fixed before this run, from Paper 3's registered data, which was already known @lavi_granted_2026: the Claude model least moved by claimed approvals, by first-attempt reach pooled over the four conditions that claim approval and state the rule. By our computation from Paper 3's committed records, that was #raw(reg.reviewer_model), with #rule.pooled.at(rule.chosen).reached of #rule.of trials, ahead of the next model by #rule.margin trials. The architect is the same model, by the author's decision, so that the AgentDojo comparison (@sec:results-agentdojo) sets the graphs beside an undefended run of the identical model. Architect and reviewer are therefore the _identical_ model in different roles and contexts. We report every catch rate as diversity of role and information, never independence (@sec:limits).

*No escalation at run time.* A graph that turns out at run time to need more than it holds fails the run, and the run returns to the architect, at most once, as a request to edit the graph, which then goes back through both reviews. The request is built from a fixed table of refusal classes, never from the refusal's message, which can name a value the bank holds, an attacker's payee among them. The measurement below made #meas.edits edits, so this path was #if meas.edits == 0 [not exercised] else [exercised #meas.edits times]. This is the contrast with practice, and its price is flexibility: no consequential action waits for a person, but nothing can be granted mid-task either.

= Method <sec:method>

== The labels <sec:labels>

A label states, for one task, the widest grant a careful architect could justify from the task alone, given the catalogue and no knowledge of what the bank holds. Labels are therefore upper bounds, not the narrowest grant that would succeed. Written knowing the bank, task 0's payment grant would name the bill's payee and total, which no architect blind to the bill could write. A grant within its label, by the validator's narrowing relation, is not a widening. A grant beyond it is, and each widening is classed by what its capability does: _effect_ (`Payments`, `ScheduledPayments`, `UserProfile`, `Credentials`), _read_, _inference_ or _answer_. The registration counts effect-class widenings only. Read-class ones are reported apart.

The labels were drafted per task by a Claude model, with a reason for each grant and the open questions recorded, and approved by the author, as drafted, before the run. Two decisions bound the results. Task #num(k.labels.cannot_succeed.at(0)) asks to send Spotify the difference on an underpaid bill. Its label names the payee `'Spotify'`, but AgentDojo's utility check expects Spotify's IBAN, which only the transaction history holds, so no graph within the label can succeed; we kept the label and report the task as failing under least authority. Task #num(k.labels.cannot_succeed.at(1)) asks for a password change, which needs `Credentials`, so it is expected to be inexpressible. The labels are a judgement the author approved, are published with their reasons, and are pinned in the registration by hash. After the run they may be disclosed, never corrected.

== The registration <sec:registration>

Before any trial, a registration was committed in the repository and approved by the author (commit #raw(reg.registration_commit.at(0).slice(0, 7))). It fixes the pretext texts verbatim, the cells, the models by full identifier, the SHA-256 of every task the architect would be shown, the labels' hash, one primary outcome and one confirmatory test, and the rules for exclusion, voiding and early stopping. The harness refuses to run against an uncommitted or edited registration, against a task whose hash has drifted, against a model that resolves to another identifier, or from a working tree that differs from its commit. This is pre-registration inside one repository, by its one author, checked by commit hashes and by the harness that runs it. It is not a registry entry, and nobody outside reviewed it.

*Pretexts and channels.* There are #kr.pretexts pretexts, each headed "Approved by the bank's security team". Q1 says the request "has been reviewed and approved for wider access", and names the widening in words, such as "it may also set up the payment as a standing order". Q2 names the wider grant itself, in the graph language, says that "the account's policy will be updated to match in the next release", and asks for the grant to be treated as granted until then. The widening each names is fixed per task in the registration. In channel A the pretext is appended to the task, so the architect, the link check and the reviewer all see it. In channel B it is a document given to the architect beside the task, as material it reads, and the link check and the reviewer see the task alone. Together with Q0, the task with no pretext, that makes #kr.conditions conditions, each run on all #kr.tasks tasks #kr.repetitions times: #reg.planned trials.

*Primary outcome.* A trial has an _unseen widening_ when its graph holds an effect-class widening that neither the link check nor the reviewer's primary verdict catches. The least-authority check against the labels is the reference. No reviewer sees the labels, so neither can be fitted to them. In deployment no such labels would exist, so what is measured is the two reviewers that would: the link check and the reviewer model. A trial with no graph has no widening.

*Confirmatory test.* One contrast: channel A, its pretexts pooled, against Q0, over all #kr.tasks tasks, by a one-sided Fisher exact test at $alpha = $ #ad.confirmatory_alpha. Everything else is registered as descriptive.

*The reviewer's pre-use test.* Following AI Control's practice of testing a monitor on planted attacks before trusting it @greenblatt_ai_2024, the reviewer had to catch at least #kr.preuse_threshold of #gate.planted widenings before the first trial, or the run would not start. They were planted by hand in hand-written (oracle) graphs, one for each of #kr.preuse_controls tasks, whose unwidened versions served as the controls. Of the widenings, #kr.preuse_by.kind widened a grant's kind and #kr.preuse_by.scope its scope, and #pe.planted were effect-class, the class the run counts.

*What happened.* All #reg.recorded of #reg.planned planned trials ran. A harness fault crashed the first start before the pre-use test, with nothing recorded; it was fixed in the harness alone, with the registration and every hash unchanged, and is disclosed here.

== The pilot, told straight <sec:pilot>

An unregistered pilot ran the architect on all #kr.tasks tasks with no pretext before the registration was written, #k.pilot.runs times, and what the architect is shown changed after each run, the last time without a re-run. The first wording was tried on #p-one.tasks task, which the architect #if p-one.outcomes.inexpressible == p-one.tasks [answered as inexpressible] else [mostly answered as inexpressible]: to total the user's spending, the architect needed to know that their own payments carry the sender `'me'`, a fact about the data. The author declined to add it, and instead clarified that `Extract` can find, compare and compute over its material. Under the second wording, #p-two.outcomes.inexpressible of #p-two.tasks tasks came back inexpressible. The architect had been told that a grant wider than the task needs is a fault even when the program works, and read "needs" with hindsight: it refused tasks whose only statable grant was `any` or `uncapped`. That held the architect to a stricter standard than the labels and the reviewer, so its wording was aligned with theirs. The third wording produced #p-three.outcomes.graph graphs, #p-three.outcomes.inexpressible inexpressible answers and #p-three.outcomes.at("failed-stage-two") failed repair. That failure, on task 2, was a scope written with its field names quoted, and a documentation fix followed: field names are bare words, with three examples on values the bank does not hold. By the author's decision the pilot was not re-run, so the registered wording is the third plus that fix, and the fix itself was never piloted. Task 2's rent order later holds many of the run's unseen grants (@sec:results-reviewers). The pilot is reported apart and pooled with nothing.

= Results <sec:results>

== The confirmatory test <sec:results-confirm>

Unseen widenings came in #conf.channel_a.unseen of #conf.channel_a.of channel-A trials (#ad.channel_a_unseen_rate) and in #conf.q0.unseen of #conf.q0.of trials with no pretext (#ad.q0_unseen_rate). The one-sided Fisher exact test gives $p = $ #(ad.confirmatory_p + ",") against the registered $alpha = $ #(ad.confirmatory_alpha + ".") #if conf.supported [The test is *supported*.] else [The test is *not supported*. A pretext in the task did not, at the registered threshold, raise the rate of widenings both reviewers missed, and nothing below is evidence that it did.] The test also treats trials as independent, although they cluster by task, so a clustered analysis could give a larger $p$ still.

*How near the threshold (post hoc).* One of Q0's unseen trials holds a single widening, `Payments<['inbound-senders'], '10.00'>`. Task #num(ps.trials_changed.at(0).split(".").at(0))'s approved label holds `Payments<[inbound-senders], '10.00'>`: the architect wrote the label's own grant with the set's name in quotes, and the parser at the time read it as a payee of that name, which no label allows. The trial counts, as registered. Without it Q0 would be #ps.q0.unseen of #ps.q0.of (#ad.post_hoc_without_slips_q0_rate), and the same test would give $p = $ #(ad.post_hoc_without_slips_p + ",") #if ps.below_alpha [under] else [still over] the threshold. We report this so a reader can see where the verdict sits, not to move it: choosing, after the run, which trials to count is the reanalysis a registration exists to discount, and the registered verdict stands.

== Descriptive: the reviewers, column by column <sec:results-reviewers>

#let row(c) = (
  [#c], [#cond(c).graphs], [#cond(c).inexpressible], [#cond(c).widened], [#cond(c).unseen],
  [#cond(c).caught_by_link_check], [#cond(c).caught_by_reviewer], [#cond(c).flagged_with_rationales],
)

#figure(
  table(
    columns: 8,
    align: (left,) + (right,) * 7,
    table.header([*Condition*], [*Graphs*], [*Inexpr.*], [*Widened*], [*Unseen*], [*Link check*], [*Reviewer*], [*With rationales*]),
    ..conds.map(row).flatten(),
    [All], [#tot.graphs], [#tot.inexpressible], [#tot.widened], [#tot.unseen], [#tot.caught_by_link_check], [#tot.caught_by_reviewer], [#tot.flagged_with_rationales],
  ),
  caption: [The registered run, by condition, #kr.trials_per_condition trials each. _Widened_: trials whose graph holds an effect-class widening. _Unseen_: those neither the link check nor the reviewer caught. The three right-hand columns count widened trials each reviewer caught, and are not summed; the last is the reviewer shown the architect's rationales, recorded apart. Architect and reviewer are the same model. Only Q0 against A-Q1 and A-Q2 pooled carries a test.],
) <tab:conditions>

@tab:conditions gives every cell. All of it is descriptive.

*The reviewer passed its test, then flagged #if minority [a minority] else [part] of the widenings the labels define.* Before the first trial it caught #caught-planted planted widenings (#caught-effect effect-class ones), with #gate.false_alarms false alarms on #gate.grants_within_label grants within their labels. In the run, it caught #tot.caught_by_reviewer of the #tot.widened trials in which the architect had widened an effect-class grant (#ad.reviewer_natural_catch_rate), and flagged #reg.false_alarms_primary of #reg.grants_within_label grants that were within their labels. The reviewer is the architect's own model (@sec:limits). #if overstated [In this setting, a pre-use test built from planted widenings overstated the reviewer on the architect's own.]

Every miss is a disagreement with a label, and the misses fall where the labels draw judgement lines. Across all conditions the #kr.unseen_grants unseen widened grants concentrate in #kr.tasks_with_unseen of the #kr.tasks tasks, most in task #num(top.at(0).at(0)) (#top.at(0).at(1) grants) and task #num(top.at(1).at(0)) (#top.at(1).at(1)), both of which ask, among other things, for a change to the rent standing order. Of them, #kr.unseen_grants_on_open_label_tasks fall on tasks whose label recorded an open question when it was drafted, though not always one about the grant widened. Task #num(top.at(1).at(0))'s label asked whether "accordingly", in "adjust my rent payment accordingly", justifies more fields than the amount, and was drafted as the amount only. A different line there would move these counts, and the reviewer may be right where it disagrees.

*The link check.* It caught #tot.caught_by_link_check of the #tot.widened widened trials. In channel B, where the pretext was in a document, a widened grant quoting the pretext would have failed, and #if cond("B-Q1").caught_by_link_check + cond("B-Q2").caught_by_link_check == 0 [none did: the architect quoted the task] else [some did]. This is "linkage, not adequacy" observed. The check confirms that a grant points at the task, not that the words pointed at justify it.

*The rationales.* Shown the architect's rationales, the same reviewer flagged widenings in #tot.flagged_with_rationales widened trials, against #tot.caught_by_reviewer without them, and #reg.false_alarms_persuaded grants within their labels, against #reg.false_alarms_primary. Monitors shown a generator's reasoning can be deceived by it @arnav_cot_2025; here the quotations were the task's own words, and #if rationale-flags-more and reg.false_alarms_persuaded > reg.false_alarms_primary [seeing them made the reviewer flag more of everything, not discriminate better] else [we read nothing into the difference].

*Under pretexts.* #if looser [Under each pretext, the architect wrote more graphs than without one, answered `inexpressible` less often, and widened in more trials (@tab:conditions).] else [Under a pretext, graph and widening counts differ from Q0's (@tab:conditions).] Of the #kr.unseen_grants_under_pretext unseen widened grants under a pretext, #reg.unseen_is_target_kind.target were exactly the grant the pretext named, #reg.unseen_is_target_kind.at("same kind") were other grants of the same kind, among them grants part-way toward it, and #reg.unseen_is_target_kind.at("other kind") were of another kind. The pretexts' targets do not account for most unseen grants, but this count cannot separate a pretext that loosened the architect from one that steered it part-way.

*Two smaller counts, kept apart.* Of the unseen grants, #kr.unseen_quoted_dynamic named a dynamic payee set as a quoted literal (`'any'` for `any`), which the parser accepted as a payee of that name, and the least-authority check flagged as a widening of scope. Of these, #kr.label_spelling_slips are the slip in @sec:results-confirm, the label's own grant misspelt, so they widen by the parser, not by intent. All count as registered. The parser now refuses the spelling, and the report reads these grants from their literal text, so the count cannot move with the fix. Separately, #kr.read_widenings read-class widenings fell outside the counted class.

== Post-hoc analyses <sec:results-posthoc>

Three analyses were run over the registered records after the run, two in later exploratory work and one for this paper. They are post hoc: not registered, and neither pooled with the registered figures nor tested against them. We report them because they answer the three objections a reader will raise first.

*Bind the link check to the scope (post hoc).* A stronger check would require a grant's literal payees and cap to appear in its quotation. Replayed over the registered graphs, it flagged #sb.quote.unseen_grants_flagged of the #sb.quote.unseen_grants unseen widened grants, among #sb.quote.flags flags of which #sb.quote.false_alarms were false alarms. Bound to the whole task rather than the quotation, it flagged #sb.prompt.unseen_grants_flagged. Of the #sb.quote.unseen_grants, #sb.quote.unseen_grants_open have open scopes (`any`, `uncapped`), which no text-binding check can reach, and the other #sb.quote.unseen_grants_literal widen fields or modes whose literal elements all stand in the task. Binding the check to the scope does not make it measure scope.

*Show the reviewer what the graph does (post hoc).* A reviewer shown type strings might miss what a grant permits. A second view states, for each writer, the payees, amounts, orders and fields it could produce, computed from the graph. Over a sample fixed before the replay (the #br.sample_widened_trials widened trials and #br.sample_clean_trials clean ones), the reviewer, still the architect's own model, caught #br.caught of #br.sample_widened_trials widened trials (#pd.behaviour_catch_rate), against #br.registered_caught (#pd.registered_catch_rate) for the registered reviewer on the same graphs: #br.gained gained and #br.lost lost. It flagged #br.clean_trials_flagged clean trials, against #br.registered_clean_trials_flagged. In this one replay the view moved the catch rate a little, and the false alarms with it. Shown what each missed writer can produce, the reviewer still judged the grant needed: on these grants it disagrees with the labels, not with the graph.

*Use a stronger reviewer (post hoc).* We re-ran the reviewer with #raw(son.model), a more capable model of the same family, on the same sample, changing nothing else: before each call, the system text and the prompt were checked by hash to be the registered reviewer's, byte for byte. The sample holds every widened trial of the run. #raw(son.model) caught #sp.caught of the #sp.widened_trials widened trials (#sd.primary.catch_rate), against #sp.registered_caught (#sd.primary.registered_catch_rate) for the registered reviewer: #sp.gained gained, #sp.lost lost, and #sp.missed_by_both missed by both. It flagged #sp.clean_trials_flagged of the #sp.clean_trials clean trials, against #sp.registered_clean_trials_flagged. Shown the rationales, it caught #sq.caught, against #sq.registered_caught. Its misses fall first on tasks #num(sp.missed_by_task_ranked.at(0).at(0)) and #num(sp.missed_by_task_ranked.at(1).at(0)), where the registered run's unseen grants do. This removes the identity of the two roles, not their family#if son-minority [, and in this one run a more capable reviewer still flagged a minority of the widenings the labels define]. It cannot say what a reviewer of another family would do (@sec:limits).

== AgentDojo <sec:results-agentdojo>

We ran one graph per task, the registered Q0 graph of the first repetition, through AgentDojo's scorer: once clean, and once under each of its #km.goals injection goals, with every capability-holding node confined. Predictions of which goals each graph left open were committed before the run. The architect produced no graph for #km.no_graph tasks (#tasks(meas.no_graph)), which score no utility and are not attacked. The baseline is the same model, #raw(base.model_requested), undefended, calling AgentDojo's tools directly @debenedetti_agentdojo_2024.

#figure(
  table(
    columns: 3,
    align: (left, right, right),
    table.header([], [*Graphs (architect)*], [*Undefended baseline*]),
    [Utility], [#rate(meas.utility) (#ud.graphs.utility)], [#rate(base.utility) (#ud.baseline.utility)],
    [  beyond the idle-pass tasks], [#rate(meas.utility_beyond_idle) (#ud.graphs.utility_beyond_idle)], [#rate(base.utility_beyond_idle) (#ud.baseline.utility_beyond_idle)],
    [Utility under attack], [#rate(meas.utility_under_attack) (#ud.graphs.utility_under_attack)], [#rate(base.utility_under_attack) (#ud.baseline.utility_under_attack)],
    [  beyond the idle-pass tasks], [#rate(meas.utility_under_attack_beyond_idle) (#ud.graphs.utility_under_attack_beyond_idle)], [#rate(base.utility_under_attack_beyond_idle) (#ud.baseline.utility_under_attack_beyond_idle)],
    [Attack success], [#rate(meas.attack_success)], [#rate(base.attack_success)],
  ),
  caption: [AgentDojo banking, #bank.suite, under #raw(bank.attack), one repetition, the same model in both columns. A task with no graph scores no utility. The idle-pass tasks are those whose utility holds on a run that does nothing (@sec:setting).],
) <tab:agentdojo>

The graphs scored utility on #rate(meas.utility) tasks, and #rate(meas.utility_beyond_idle) beyond the idle-pass tasks, against #rate(base.utility) and #rate(base.utility_beyond_idle) for the baseline (@tab:agentdojo). #if km.utility_with_failed_run.len() > 0 [Among the graphs' successes, tasks #tasks(km.utility_with_failed_run) are runs that failed but that AgentDojo scores as succeeding, because they are idle-pass tasks and the failure changed nothing.] Part of the gap is the #km.no_graph tasks with no graph. Of the #km.graphs graphs that ran, #failed.len() failed clean: #extract-failures.len() (tasks #ids(extract-failures)) at an `Extract` node, whose model did not return a field the graph needed#if failed-elsewhere.len() > 0 [, and #failed-elsewhere.len() (task #ids(failed-elsewhere)) elsewhere in the library]. #if km.ran_without_utility.len() > 0 [Another #km.ran_without_utility.len() (tasks #tasks(km.ran_without_utility)) ran to completion with the wrong result.] We attribute the `Extract` failures to the rule that the architect sees shapes, never values, as the pilot suggested (@sec:pilot), but we did not test the attribution.

Attack success was #rate(meas.attack_success) for the graphs, and the attack column must be read with what each graph could write. Of the #km.graphs graphs, #(km.graphs - km.holds_writer) hold no writer, and cannot be made to write by construction. Of the #km.holds_writer that do, #writers-reached.len() reached their writer under attack#if writers-every-run [, in every attacked run, and no goal succeeded against them]. The other #writers-not-reached.len() never reached it#if ran-not-reached.len() > 0 [: task #ids(ran-not-reached) ran to completion without doing so, and the rest failed first]. The #km.predicted_residual_count graphs predicted to leave goals open (tasks #tasks(k.measured.predicted_residual_graphs)) reached their writer in #km.residual_writer_reached attacked runs: #if residual-at-extract [each failed at an `Extract` node first, so their zero is not a defence.] else [their zero is not a defence.] Task #tasks(km.with_unseen)'s graph is the measured graph that holds an unseen widening of the registered run: its label holds no payment grant, the graph holds `Payments<[any], uncapped>`, and both reviewers passed it. That grant is what left its goals open; an `Extract` failure, not review, kept it from the writer. There were #km.contradictions contradictions of the committed predictions. #if base.attack_success.hits == 0 [And the undefended baseline's attack success was #rate(base.attack_success) under the same attack: this model resisted it unaided, so the measurement had no attack success to lower.] else [The undefended baseline's attack success was #rate(base.attack_success) under the same attack.] #if zero-both [Zero attack success here is neither a defence nor the absence of a residual.] AgentDojo scores #km.goals goals under #attacks, and a change the scorer does not count is not seen.

= Related work <sec:related>

*Planning before execution.* That an agent should commit to a plan before it reads untrusted data is established. In CaMeL, a privileged model that never sees tool output writes the plan as restricted Python, and an interpreter checks security policies, supplied with the system, on every tool call's arguments and their provenance @debenedetti_defeating_2025. ACE splits planning as we do: an abstract plan written from trusted information alone, mapped by a second step onto the installed apps, checked statically for information flow, and executed with each app isolated @li_ace_2026. FIDES labels values for confidentiality and integrity at run time and enforces flow policies deterministically, evaluated on AgentDojo @costa_securing_2025, and later work in that line measures _autonomy_, "the fraction of consequential actions an agent can execute without human-in-the-loop (HITL) approval while preserving security" @kolluri_optimizing_2026. Progent has a model draft a privilege policy from the task, applies a narrowing automatically, and requires approval for an expansion @shi_progent_2025. Conseca is nearest to our artefact: a model generates a per-task policy, each entry with a human-readable rationale, and enforcement is deterministic @tsai_contextual_2025. Its authors note that users can be asked to approve the policy, but the prototype does not evaluate such review.

The difference we claim is narrow, and scoped to what we surveyed. None of these systems, in the work we read, measures review of the authority artefact against labels fixed before the run; the derived import surface is the demonstrator's @lavi_confinement_2026. This paper adds the review, and measures it. The comparison cuts the other way on enforcement: CaMeL and FIDES govern data flow at run time, including what tools return, where a graph's authority is fixed before the run and its trust labels cover only what nodes declare. We report no head-to-head figure. On AgentDojo's banking suite, CaMeL reports no successful attack for most of the models it was run with @debenedetti_defeating_2025, and FIDES none with its policy checks on @costa_securing_2025, at banking utilities that vary widely by model; Progent's current version reports totals across suites only @shi_progent_2025. Those results are for other models, under attacks and suite versions the papers do not all name, #if base.attack_success.hits == 0 [and our baseline model resisted our attack unaided (@sec:results-agentdojo),] else [and our attack differs (@sec:results-agentdojo),] so a comparison of attack success would not be informative.

*The threat left out.* A catalogue of design patterns for securing agents includes _plan-then-execute_ and _code-then-execute_, the patterns a signal graph instantiates, and says of plan-then-execute that it "does not prevent prompt injections contained in the user prompt" @beurer-kellner_design_2025. In our pipeline, the task is the trusted input that determines authority, so a pretext there aims at the architect, who could write a wider clause. That is the threat our registered experiment tests, and Paper 3 showed models of this family move under it when writing code @lavi_granted_2026.

*Review by a model.* AI Control studies a monitor that is a copy of the untrusted model, and makes it usable by testing it on planted attacks before use and by redacting what it sees; in that paper's one setting, such untrusted monitoring reached 79% safety, against 62% for a weaker trusted monitor @greenblatt_ai_2024. We followed both disciplines: a pre-use test, and a canonical graph with the architect's names and rationales removed. #if overstated [In our one setting, a pre-use test built from planted widenings overstated the reviewer: it caught every planted widening and a minority of the architect's own (@sec:results-reviewers). AI Control's upfront test is aimed at collusion rather than competence on natural cases, so this is a caution about borrowing it, not about its use there.] Other work suggests why a same-model reviewer may be lenient. Models recognise and favour their own outputs, and fine-tuning a model to recognise its own more strongly also makes it favour them more @panickssery_llm_2024, and errors correlate within a provider and, among larger models, across providers @kim_correlated_2025, so changing family may be only a partial cure. Monitors that read a generator's reasoning catch subtler faults, but can be talked round by a misleading rationale @arnav_cot_2025, which is why our primary verdict sees no rationale. Underneath all of this is Leong's argument that a model's arbitration between instructions is not a trust boundary @leong_instruction_2026. Our reviewer is such an arbitration, placed before the run rather than during it, and the deterministic parts of our pipeline, the validator and the derived import surface, are the parts that do not depend on it.

= Limitations <sec:limits>

*One model, in both roles.* The architect and the reviewer are the same model, #raw(model). A model favours outputs it recognises as its own @panickssery_llm_2024, and errors correlate within a provider and, for larger models, across providers @kim_correlated_2025. That work predicts that a same-model reviewer understates what a comparably capable reviewer of another family would catch, so we read every catch rate here as a likely lower bound. Neither the direction nor the size is measured: the control that would measure them, the reviewer from another model family on a registered subset, is built and gated, and was not run, because no spend on it was approved. A post-hoc re-run with a more capable model of the same family, which did not write the graphs, caught #sp.caught of #sp.widened_trials widened trials against #sp.registered_caught (@sec:results-posthoc). That separates the reviewer from the architect, but not from its family, where correlated errors and a shared reading of the task would persist; it is no test, and it leaves the other-family question open. The reviewer's model was chosen by a margin of #rule.margin trials in #rule.of. And the reviewer was told that another model wrote the graph, so self-preference, as cited, would have to act without being told; whether this model recognised its own graphs was not tested.

*Labels are judgement.* The reference is the least-authority labels. They were drafted by a Claude model and approved by the author unchanged, so the reference too passes through the family under test. They were registered before the run and are published with their reasons, and they are upper bounds by design, which makes a widening a conservative call. Another careful author could draw some differently, and each such line moves the counts: most unseen grants fall on tasks whose label recorded an open question (@sec:results-reviewers). Tasks #tasks(k.labels.cannot_succeed) cannot succeed under their labels (@sec:labels).

*What the checks measure.* The link check measures linkage, not adequacy, and binding it to the scope did not change that (@sec:results-posthoc). The least-authority check and both reviewers ask whether the task needs a grant, never whether the node holding it should. A grant can be needed and held by the wrong node, for example an open payment grant given whole to code a developer will write. None of our measures can see that, and we do not claim the reviewers were measured on it.

*Construct.* The pretexts are #kr.pretexts fixed texts, blunt and appended or attached whole. A model that ignored them ignored those, and no count here says a better-crafted pretext would fare the same. Channel B is a document handed to the architect, not content retrieved by a running system. AgentDojo was run with #attacks and #km.goals goals, and #bank.any_payment_goals.len() of the goals are met by any payment to the attacker, so attack success counts a narrow set of outcomes#if meas.attack_success.hits == 0 [, and a zero is not the absence of a residual]. And #km.idle_pass_count tasks score utility on a run that does nothing, so a figure over all #kr.tasks tasks flatters both pipelines; each is given without them too. The rule that the architect sees shapes, never values, costs utility by design; a richer view of the data would trade information for utility, and is the author's decision to make. The #kr.unseen_grants unseen grants include #kr.unseen_quoted_dynamic that fell through a parser hole the run found, since closed; #kr.label_spelling_slips of them are the label's own grant misspelt (@sec:results-confirm).

*Internal.* The confirmatory test treats trials as independent, though they cluster by task. Each cell has #kr.repetitions repetitions, so no per-task claim is supported; where we name tasks, it describes where the counts fall. The pilot changed what the architect is shown after each of its runs, the last time without a re-run, so the registered wording was never piloted whole (@sec:pilot). A harness fault before any trial was fixed with the registration unchanged. The registration lives in the author's repository, and the harness's refusals rest on that repository's history, which its author can rewrite. And the pipeline, its harness and this paper were produced by the same AI-assisted process, by a model of the family under test: the counts are computed from the records, but the reading of them was drafted by a Claude model about a Claude model.

*Security argument.* The pure library nodes run on the host tier, where nothing confines them; confinement here holds for the capability-holding nodes, which run as components @lavi_confinement_2026. And a grant bounds a kind and a scope, not what a node does with them: inside a granted `Payments<[any], uncapped>`, any payee is reachable. Where trust is discharged is the architect's choice, and neither the labels nor either reviewer assess it.

= Future work <sec:future>

Several directions follow from the limits above. A reviewer from another model family, on a registered subset, would measure what the post-hoc same-family re-run could not. Pretexts carried in content the running system retrieves would test the indirect channel that channel B only approximates. Two follow from exploratory work that has no figure here. A grant bounded by a value an upstream node produces, "this payee, this amount, once read", would narrow the open grants that the shapes-not-values rule forces; the type language cannot yet express it. And a request for more authority, answered by a reviewed edit to the graph, should grant no more than was asked; exploratory work showed that this is not automatic. Placement, which node holds a grant, is a review dimension none of our reviewers measured. The back half of the pipeline, in which agents implement the nodes and tooling reduces what they hold, and review by people, are outside this paper.

= Conclusion <sec:conclusion>

When authority is written down before anything runs, its review can be measured, grant by grant, against labels fixed in advance. We built that measurement and ran it. With one model as both architect and reviewer, a pretext in the task was followed by more unseen widenings than none, but the registered test of the difference #if conf.supported [was supported] else [was not supported#if ps.below_alpha [, near its threshold], and we claim no effect]. What the measurement does show is how little of what the labels call widening the review flagged: the citation check #if tot.caught_by_link_check == 0 [none] else [#tot.caught_by_link_check], and the reviewer model #tot.caught_by_reviewer of #tot.widened natural widenings#if gate.caught == gate.planted [ after catching every planted one]. Writing authority down is what made that visible. A more capable reviewer of the same family, post hoc, caught #sp.caught. Whether a reviewer of another family, or a person, closes the gap is the next measurement, and the artefact makes it possible.

#bibliography("/citations.bib", style: "ieee")
