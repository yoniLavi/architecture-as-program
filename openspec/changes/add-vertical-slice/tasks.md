# Tasks

Every session working on this change first checks the feed recorder (standing task 0.3 of
`strengthen-generation-evidence`) and `git status`. Long runs go at low priority. Edit
nothing a run imports while it runs.

## 0. Approval

- [x] 0.1 **The author approves this proposal** and answers the five questions in `design.md`
      (1 November 2026: every recommendation taken; recorded in `design.md`)

## 1. Steps 2 and 3: the custom node and the shadow link check

- [x] 1.1 The `Custom` library entry: role, signature and clause, no body; the library check;
      the catalogue's wording, which says when to use it. In `SLICE_CATALOGUE` only, so the
      registered run's hashed text is unchanged (a test now holds it reproducible); `author`
      takes a `custom` flag, not a catalogue, so no content can arrive by it. Holds a reader's
      `DBHandle`, `LLMClient<inference>`, or a banking writer kind; may not discharge trust;
      its output is `Untrusted` if it reads the bank or any untrusted input
- [x] 1.2 The scope-binding link check, in shadow mode, replayed over the registered
      records. Reported, never enforced. `formal.scope_binding`, `poc/slice/replay.py`.
      Found (pinned by test): bound to the quote, it flags 1 of the 61 unseen widenings at
      59 false alarms in 60 flags (the quotes are a few words; the IBAN stands elsewhere);
      bound to the prompt, it flags none. The 61 are 17 by kind (open scope), 2 open
      `UserProfile`, and 42 whose literal elements all stand in the prompt: field and mode
      widenings, which no text-binding check can see

## 2. Step 4: the chosen reviewer candidate(s)

- [x] 2.1 The behaviour-shown reviewer (amended after 1.2; see `design.md`): the writers'
      possible values come from the predictions' taint analysis. The scope-binding check
      gets no further work: it stays in shadow mode and is reported only.
      `poc/slice/behaviour.py` (taint generalised to provenance; held to taint on all 305
      registered graphs), `poc/slice/review.py`; records in `poc/slice/runs/behaviour/`.
      Replayed in shadow mode, Haiku on the subscription, 6 November 2026, over a sample
      fixed in advance: the 76 registered trials with a counted widening, and 76 clean
      ones by hash. Found (pinned by test):
      - **Barely better, within noise.** 21 of 76 widened trials caught, against the
        registered reviewer's 17 on the same graphs. 5 gained, 1 lost. Clean trials
        flagged rose from 3 to 7. Most new flags ask to cap an amount the architect
        could not know ("the usual Spotify amount").
      - **The misses are not for lack of information.** The 42 field and mode widenings
        are untouched: 0 of 21 on tasks 2 and 9 (`date`), 0 of 20 on task 15
        (a new recurring 2200 to the new landlord instead of updating the rent order).
        The view states exactly what the graph does ("date: a model's answer, from the
        file 'landlord-notices.txt'"), and the reviewer judges it needed, quoting
        "adjust my rent payment accordingly". It disagrees with the label, not with the
        graph. Those are judgement calls, and they go to the author at step 8.
      - **There is nothing to minimise in them.** No counted widening, and no grant in the
        sample, admits a field its graph never sets. Every wide grant is exercised. So
        step 6, as designed, will remove nothing from them, as the roadmap expected.
      - By condition, caught (registered → behaviour): channel A 12 → 17 of 41,
        channel B 4 → 3 of 28, Q0 1 → 1 of 7.

## 3. Step 5: the developer and escalation

- [x] 3.1 The developer step, using Paper 3's pipeline for custom nodes, held to the gate.
      `poc/slice/developer.py`. It is shown Paper 3's way: signature, the architect's role
      text, input and output shapes, granted interfaces, and the `aap:caps` package with
      the banking interfaces, without any world. It sees no bank value and no task
      prompt. Format → build → gate → run, reusing Paper 3's reply parser, ambient scan and
      crate, with `serde_json` added. The gate is `interfaces.py`, unchanged. The run is
      the graph on the task's clean environment with the component confined. Two
      **stubs/departures, recorded**: no contract step (the architect writes none for a
      `Custom` node), and an unused grant is recorded, not failed (a minimisation finding,
      not a faulty body). A refusal at a crossing reaches the developer as a class from
      the measured run's table, never its message. Control: a hand-written `ParseBill`
      (`poc/slice/control/`) passes clean end to end, utility true. Negative control: the
      same body plus one `payments` import is caught at the gate (`gate:payments`) and not
      run. Integration, additive and no registered figure moved: `bodies()` takes supplied
      bodies; the pipeline and `run_pair` take `custom=`; `confinable()` reads the slice
      catalogue; `predict.py` reads a `Custom` node as `Extract`, and as the library
      writer of its kind if it holds one
- [x] 3.2 Escalation as a graph edit request, reviewed again by steps 3 and 4. Never text
      that grants anything. `poc/slice/escalate.py`. The architect gets the request as a
      structured reason (`developer-request`: node, capability, the developer's sentence
      bounded to 300 characters), with the measured run's edit view, and is told a request
      grants nothing. The edit is repaired against the validator and the slice's library
      check. It is accepted only if the link check finds nothing and the behaviour-shown
      reviewer flags no grant the edit added. The least-authority check against the
      label is recorded and never gates (a real pipeline has no label). Otherwise the
      graph before the request stands. One request per node (crude)
- [ ] 3.3 The pretext condition, if chosen

## 4. Steps 6–8

- [ ] 4.1 The crude minimiser and its report
- [ ] 4.2 The human-review page, and a committed verdict file per graph
- [ ] 4.3 **The author's verdicts**, steps 7 and 8

## 5. The run and its findings

- [ ] 5.1 The slice on the chosen tasks, recorded whole
- [ ] 5.2 `dist/slice.md` from the records; a findings entry in `docs/ROADMAP.md`
- [ ] 5.3 Then, by the author's sequence: update Paper 3 and the Paper 4 proposal, then a
      final pass to publish Paper 3
