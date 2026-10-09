"use client";

import type {
  FeedCorpusCase,
  FeedDigest,
  FeedFacts,
  FeedFactValue,
  FeedRunOk,
  HostileCase,
} from "@/lib/types";

// What the inspector shows of the feed-triage service beyond the graph view:
// the selected case's note, a tick's published digest, and the hostile-feed
// walkthrough. Every sentence about a case (`note`, `attack`, `outcome`) and
// every fact about a run is the API's, shown as returned; the only copy written
// here is the labelling of fields the payload carries.

// The API's sentences carry light inline Markdown (`**strong**`, `*emphasis*`,
// backticked names). It is set as the emphasis it marks — as React elements,
// never as HTML — with every word left as returned.
export function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("**") && p.endsWith("**") && p.length > 4 ? (
          <strong key={i}>{p.slice(2, -2)}</strong>
        ) : p.startsWith("*") && p.endsWith("*") && p.length > 2 ? (
          <em key={i}>{p.slice(1, -1)}</em>
        ) : p.startsWith("`") && p.endsWith("`") && p.length > 2 ? (
          <code key={i}>{p.slice(1, -1)}</code>
        ) : (
          p
        ),
      )}
    </>
  );
}

// ── The digest ───────────────────────────────────────────────────────

// The digest is derived from feed text an attacker may have written. The
// Markdown is shown as text; the rendered page only ever inside an iframe with
// an empty `sandbox` (no scripts, no same-origin, no navigation).
export function DigestView({ digest, testid }: { digest: FeedDigest; testid: string }) {
  if (!digest.markdown) {
    return <p className="empty">This run published no digest.</p>;
  }
  return (
    <>
      <pre className="digest-text" data-testid={testid}>
        {digest.markdown}
      </pre>
      {digest.html && (
        <details className="digest-rendered">
          <summary>Rendered page (sandboxed frame)</summary>
          <iframe
            title="digest, rendered"
            sandbox=""
            srcDoc={digest.html}
            className="digest-frame"
            data-testid={`${testid}-frame`}
          />
        </details>
      )}
    </>
  );
}

// ── The selected corpus case ─────────────────────────────────────────

interface CaseProps {
  feedCase: FeedCorpusCase;
  run: FeedRunOk | null;
  acceptedOnly: boolean;
}

export function FeedCaseInfo({ feedCase, run, acceptedOnly }: CaseProps) {
  return (
    <div data-testid="feed-case-info">
      <p className="note" data-testid="feed-case-note">
        <code>{feedCase.name}</code> ({feedCase.kind}, expected {feedCase.expected}
        {feedCase.reason ? `: ${feedCase.reason}` : ""}): <Inline text={feedCase.note} />
      </p>
      {acceptedOnly && (
        <div className="fact" data-testid="feed-accepted-only">
          <span>
            The API reports this rewiring <b>accepted</b> and <b>not run</b>{" "}
            (<code>accepted: true, ran: false</code>).
          </span>
        </div>
      )}
      {run && !run.hostile && (
        <>
          <h3>Published digest ({run.tier} tier)</h3>
          <DigestView digest={run.digest} testid="feed-digest" />
        </>
      )}
    </div>
  );
}

// ── Facts of a hostile run ───────────────────────────────────────────

function show(v: FeedFactValue | undefined): string {
  if (v === undefined) return "not reported";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "none";
  return String(v);
}

// The five facts named first, each labelled with the field it reads; every
// other key the payload carries follows, under its own name.
const LEAD: [key: string, label: string][] = [
  ["offlist_requests", "Requests that reached the attacker's host"],
  ["http_callers", "Nodes that crossed the HTTP client"],
  ["state_writers", "Nodes that crossed the state writer"],
  ["hostile_in_must_read", "Hostile item ranked a must-read"],
  ["attacker_text_in_digest", "Attacker's words in the digest"],
];

export function FactsView({ facts }: { facts: FeedFacts }) {
  const lead = new Set(LEAD.map(([k]) => k));
  const rest = Object.keys(facts).filter((k) => !lead.has(k));
  return (
    <div data-testid="hostile-facts">
      {LEAD.map(([key, label]) => (
        <div key={key} className="fact" data-testid={`fact-${key}`}>
          <span>
            {label}: <b>{show(facts[key])}</b>
            <span className="fact-key">{key}</span>
          </span>
        </div>
      ))}
      <details className="facts-rest">
        <summary>Every fact returned ({Object.keys(facts).length})</summary>
        <dl className="kv">
          {rest.map((k) => (
            <span key={k} style={{ display: "contents" }}>
              <dt className="mono">{k}</dt>
              <dd>{show(facts[k])}</dd>
            </span>
          ))}
        </dl>
      </details>
    </div>
  );
}

// ── The hostile-feed walkthrough ─────────────────────────────────────

// The three groups, in the write-up's order and under its headings.
const GROUPS: { verdict: HostileCase["verdict"]; heading: string }[] = [
  { verdict: "impossible", heading: "Structurally impossible here" },
  { verdict: "bounded", heading: "Bounded by a limit" },
  { verdict: "residual", heading: "The residual: the attack succeeds" },
];

interface HostileProps {
  cases: HostileCase[];
  run: FeedRunOk | null; // the last hostile run, if any
  running: string | null; // the case being run right now
  onRun: (name: string) => void;
  onExit: () => void;
}

export function HostilePanel({ cases, run, running, onRun, onExit }: HostileProps) {
  return (
    <div className="detail hostile" data-testid="hostile-panel">
      <div className="step-head">
        <h2>Hostile feeds</h2>
        <span className="spacer" />
        <button className="exit" onClick={onExit} data-testid="hostile-exit">
          close
        </button>
      </div>
      <p className="note" data-testid="fooled-model-note">
        The model in these runs is a stand-in, the fooled model: it obeys every instruction it is
        shown. Each case serves one hostile feed through one tick of the service; what is shown
        after a run is what the API returned for it.
      </p>

      {GROUPS.map((g) => {
        const members = cases.filter((c) => c.verdict === g.verdict);
        const residual = g.verdict === "residual";
        return (
          <section
            key={g.verdict}
            className={`hostile-group ${residual ? "residual" : ""}`}
            data-testid={`hostile-group-${g.verdict}`}
          >
            <h3>{g.heading}</h3>
            {members.map((c) => {
              const ran = run?.hostile === c.name ? run : null;
              return (
                <div
                  key={c.name}
                  className={`hostile-case ${residual ? "residual" : ""}`}
                  data-testid={`hostile-${c.name}`}
                >
                  <div className="hc-head">
                    <code>{c.name}</code>
                    {residual ? (
                      <span className="badge rejected" data-testid={`verdict-${c.name}`}>
                        ✗ {c.verdict}: the attack succeeds
                      </span>
                    ) : (
                      <span className="badge neutral" data-testid={`verdict-${c.name}`}>
                        {c.verdict}
                      </span>
                    )}
                  </div>
                  <p className="hc-text">
                    <span className="hc-label">attack</span> <Inline text={c.attack} />
                  </p>
                  <p className="hc-text">
                    <span className="hc-label">outcome</span> <Inline text={c.outcome} />
                  </p>
                  <button
                    className="chip-btn"
                    onClick={() => onRun(c.name)}
                    disabled={running !== null}
                    data-testid={`run-hostile-${c.name}`}
                  >
                    {running === c.name ? "Running…" : "Run this feed"}
                  </button>
                  {ran && (
                    <div className="hostile-result" data-testid="hostile-result">
                      <h3>
                        This run ({ran.tier} tier) — verdict: {ran.verdict}
                      </h3>
                      {residual && (
                        <div className="fact attack-succeeded" data-testid="attack-succeeded">
                          <span className="bad">✗</span>
                          <span>
                            <b>The attack succeeds.</b> This case is the residual; the digest
                            this run published is below.
                          </span>
                        </div>
                      )}
                      {ran.facts ? (
                        <FactsView facts={ran.facts} />
                      ) : (
                        <p className="empty">The API returned no facts for this run.</p>
                      )}
                      <h3>Published digest</h3>
                      <DigestView digest={ran.digest} testid="hostile-digest" />
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        );
      })}
    </div>
  );
}
