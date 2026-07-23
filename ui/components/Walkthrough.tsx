"use client";

import type { InjectionScenario } from "@/lib/types";
import type { WalkthroughHighlights } from "./GraphCanvas";
import { trustRaisers } from "@/lib/graph";

// The guided prompt-injection walkthrough. Every fact shown is read from the
// scenario response (the same `run_injection` the evaluation harness pins);
// the copy deliberately mirrors the paper's §4.3 language — attenuation, not
// elimination — and never claims more than the trace shows. In particular the
// host tier is described as demonstrating the *shape* of confinement, never as
// blocking anything.

export const WALK_STEPS = 5;

// What the canvas should show at each step. The taint steps use the confined
// run where available (falling back to host, stated in the copy); the last
// step contrasts the two tiers on one view.
export function walkthroughCanvasConfig(
  step: number,
  scenario: InjectionScenario,
): { trace: InjectionScenario["host"]["trace"]; highlights: WalkthroughHighlights } {
  const side = scenario.confined ?? scenario.host;
  switch (step) {
    case 0:
      return { trace: side.trace, highlights: { emphasize: ["ReceiveMessage"] } };
    case 1:
      return { trace: side.trace, highlights: { taintOnly: true } };
    case 2:
      return { trace: side.trace, highlights: { emphasize: ["GenerateResponse"] } };
    case 3:
      return { trace: side.trace, highlights: { emphasize: ["GenerateResponse"] } };
    default: {
      const contrast: Record<string, { host: string; confined: string }> = {};
      for (const [node, hostTier] of Object.entries(scenario.host.tiers)) {
        contrast[node] = {
          host: hostTier,
          confined: scenario.confined?.tiers[node] ?? "—",
        };
      }
      return { trace: side.trace, highlights: { contrastTiers: contrast } };
    }
  }
}

interface Props {
  scenario: InjectionScenario;
  step: number;
  onStep: (s: number) => void;
  onExit: () => void;
}

export default function Walkthrough({ scenario, step, onStep, onExit }: Props) {
  const side = scenario.confined ?? scenario.host;
  const tierNote = scenario.confined
    ? null
    : "wasmtime is not installed, so this walkthrough shows the host-tier run only.";
  const raisers = trustRaisers(side.trace);

  const steps = [
    {
      title: "An adversarial message arrives",
      body: (
        <>
          <p>
            The customer message below instructs the model to exfiltrate data. It enters the graph
            as the boundary input, and <code>ReceiveMessage</code> narrows it to{" "}
            <code>Untrusted&lt;RawMessage&gt;</code> — the trust marker is part of the type.
          </p>
          <div className="quote" data-testid="adversarial-message">
            {scenario.adversarial_message}
          </div>
          <p className="note">
            Assume the model <em>is</em> fooled. The question the graph answers is what a fooled
            model can <em>reach</em>.
          </p>
        </>
      ),
    },
    {
      title: "Taint is visible — and is raised at exactly one node",
      body: (
        <>
          <p>
            Red edges labelled ⚠ carry the <code>Untrusted</code> value. It reaches only{" "}
            <code>{scenario.discharge_node}</code>, the one node the graph declares{" "}
            <code>discharges_trust</code> (marked ⊼). Everything downstream receives structured,
            trust-discharged data.
          </p>
          <div className="fact" data-testid="fact-raisers">
            <span className={raisers.length === 1 && raisers[0] === scenario.discharge_node ? "ok" : "bad"}>
              {raisers.length === 1 && raisers[0] === scenario.discharge_node ? "✓" : "✗"}
            </span>
            <span>
              This trace records untrusted→trusted at <code>{raisers.join(", ") || "nowhere"}</code>{" "}
              and nowhere else — the same property the evaluation harness pins on every build.
            </span>
          </div>
        </>
      ),
    },
    {
      title: "What the tool-capable node actually receives",
      body: (
        <>
          <p>
            <code>GenerateResponse</code> is the only node holding a tool-capable LLM handle —{" "}
            <code>LLMClient&lt;[lookup]&gt;</code>, scoped to exactly one tool. Its recorded input is
            a <code>{side.received_type}</code>, not the raw message.
          </p>
          <div className="fact" data-testid="fact-untrusted">
            <span className={side.is_untrusted ? "bad" : "ok"}>{side.is_untrusted ? "✗" : "✓"}</span>
            <span>
              It received an <code>Untrusted&lt;_&gt;</code> value: <b>{String(side.is_untrusted)}</b>{" "}
              — the raw adversarial wrapper never reaches it.
            </span>
          </div>
          <div className="fact" data-testid="fact-refused">
            <span className={side.out_of_scope_call_refused ? "ok" : "bad"}>
              {side.out_of_scope_call_refused ? "✓" : "✗"}
            </span>
            <span>
              An attempted <code>exfiltrate</code> tool call outside the <code>{"{lookup}"}</code>{" "}
              scope was refused by the handle itself.
            </span>
          </div>
        </>
      ),
    },
    {
      title: "The residual, stated honestly",
      body: (
        <>
          <p>
            The question text is a free-text field, and that field stays adversarial data even
            after discharge — the node&apos;s input is labelled <em>trusted</em>, yet the
            instruction text is still inside it:
          </p>
          <div className="fact" data-testid="fact-residual">
            <span className="bad">•</span>
            <span>
              Adversarial text present in a permitted field:{" "}
              <b>{String(side.adversarial_text_present)}</b>
            </span>
          </div>
          <p>
            So the guarantee is <b>attenuation, not elimination</b>: the model can still be{" "}
            <em>influenced</em> by that text; it cannot call anything outside{" "}
            <code>{"{lookup}"}</code>, because the handle refuses. Blast radius drops from
            arbitrary tool execution to a bad lookup query.
          </p>
          <p className="note">
            The confined tier does <em>not</em> close this residual — what bounds the damage is
            the capability scope, not the sandbox.
          </p>
        </>
      ),
    },
    {
      title: "Host tier vs confined tier",
      body: (
        <>
          <p>
            The same run on both tiers records <em>structurally identical</em> traces — the
            recorded difference is which tier ran each node. On the host tier a node receives only
            its declared handles, but nothing stops a hostile node from <code>import os</code>:
            that is the <em>shape</em> of confinement, not enforcement. On the confined tier the
            ported nodes run as WASM components whose imports <em>are</em> their declared
            capability interfaces.
          </p>
          {tierNote && <p className="note">{tierNote}</p>}
          <table className="tier-table" data-testid="tier-table">
            <thead>
              <tr>
                <th>node</th>
                <th>host run</th>
                <th>confined run</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(scenario.host.tiers).map(([node, hostTier]) => {
                const confinedTier = scenario.confined?.tiers[node] ?? "—";
                return (
                  <tr key={node} className={confinedTier !== hostTier ? "diff" : ""}>
                    <td className="n">{node}</td>
                    <td>
                      <span className={`badge tier-${hostTier}`}>{hostTier}</span>
                    </td>
                    <td>
                      {confinedTier === "—" ? (
                        "—"
                      ) : (
                        <span className={`badge tier-${confinedTier}`}>{confinedTier}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      ),
    },
  ];

  const current = steps[step];

  return (
    <div className="detail walkthrough" data-testid="walkthrough">
      <div className="step-head">
        <span className="step-count">
          {step + 1} / {steps.length}
        </span>
        <h2>{current.title}</h2>
      </div>
      {tierNote && step < 4 && <p className="note">{tierNote}</p>}
      <div className="body">{current.body}</div>
      <div className="nav">
        <button onClick={() => onStep(step - 1)} disabled={step === 0} data-testid="walk-prev">
          ← Back
        </button>
        <button
          className="primary"
          onClick={() => onStep(step + 1)}
          disabled={step === steps.length - 1}
          data-testid="walk-next"
        >
          Next →
        </button>
      </div>
      <button className="exit" onClick={onExit} data-testid="walk-exit">
        Exit walkthrough
      </button>
    </div>
  );
}
