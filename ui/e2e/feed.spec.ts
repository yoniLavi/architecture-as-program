import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

// What the inspector shows of the feed-triage service. As in inspector.spec.ts,
// each test backs one behaviour: what is not covered here (or in the Python
// contract tests of the `/api/feed/…` routes) is not claimed. The screenshots
// are written under their own `feed-` names and touch none of the paper's
// `inspector-*.png` figures.

const API = "http://127.0.0.1:8123";

// The API's sentences carry inline Markdown markers, which the UI sets as
// emphasis; the words on screen are the API's words with the markers removed.
const words = (s: string) => s.replace(/\*\*|\*|`/g, "");
const SHOTS = path.join(__dirname, "..", "screenshots");
fs.mkdirSync(SHOTS, { recursive: true });

async function shoot(page: Page, name: string) {
  await page.screenshot({ path: path.join(SHOTS, name), animations: "disabled" });
}

async function feedLoaded(page: Page, feedCase = "feed-triage") {
  await page.goto("/");
  await page.getByTestId(`feed-case-${feedCase}`).click();
  await expect(page.getByTestId("node-ComposeDigest")).toBeVisible();
}

// ── Canonical rendering ──────────────────────────────────────────────

test("the feed-triage view renders exactly the nodes of the served canonical JSON", async ({
  page,
  request,
}) => {
  const doc = await (await request.get(`${API}/api/graphs/feed-triage`)).json();
  await feedLoaded(page);
  for (const node of doc.nodes) {
    await expect(page.getByTestId(`node-${node.name}`)).toBeVisible();
  }
  await expect(page.locator(".signal-node")).toHaveCount(doc.nodes.length);
});

test("the each marker and the join positions are rendered from the JSON", async ({
  page,
  request,
}) => {
  const doc = await (await request.get(`${API}/api/graphs/feed-triage`)).json();
  await feedLoaded(page);
  // Exactly the nodes declaring `each` carry the marker.
  const eachNodes = doc.nodes.filter((n: { each?: boolean }) => n.each);
  expect(eachNodes.length).toBeGreaterThan(0);
  for (const n of eachNodes) {
    await expect(page.getByTestId(`each-${n.name}`)).toBeVisible();
  }
  await expect(page.locator(".each-mark")).toHaveCount(eachNodes.length);
  // Every edge declaring `to_input` shows its position.
  const positions: number[] = doc.data_edges
    .filter((e: { to_input?: number }) => e.to_input !== undefined)
    .map((e: { to_input: number }) => e.to_input);
  expect(positions.sort()).toEqual([0, 1]);
  for (const p of positions) {
    await expect(page.locator(".react-flow__edge", { hasText: `[${p}]` })).toHaveCount(1);
  }
});

test("the per-item child graph can be opened without a run", async ({ page, request }) => {
  const child = await (await request.get(`${API}/api/graphs/triage-item`)).json();
  await feedLoaded(page);
  await page.getByTestId("open-TriageItem").click();
  await expect(page.locator(".signal-node")).toHaveCount(child.nodes.length);
  await expect(page.getByTestId("breadcrumbs")).toContainText("FeedTriage");
  await expect(page.getByTestId("breadcrumbs")).toContainText("TriageItem");
});

// ── Run a tick ───────────────────────────────────────────────────────

test("a tick overlays the trace; the per-item node reports its element runs", async ({ page }) => {
  await feedLoaded(page);
  await page.getByTestId("feed-run-btn").click();
  await expect(page.getByTestId("node-FetchFeeds")).toContainText("host");
  await expect(page.getByTestId("node-FetchFeeds")).toContainText("out: untrusted");
  await expect(page.getByTestId("node-TriageItem")).toContainText("graph");
  await expect(page.getByTestId("elements-TriageItem")).toHaveText("5 element runs");
  // The digest the tick published, as text.
  await expect(page.getByTestId("feed-digest")).toContainText("# Feed digest");
  await expect(page.getByTestId("detail-panel").getByTestId("terminal")).toContainText(
    "RunReport",
  );
  // Crossings with instance names, from the trace.
  await page.getByTestId("node-FetchFeeds").click();
  await expect(page.getByTestId("detail-panel")).toContainText("aap:caps/http-client");
  await shoot(page, "feed-run.png");
});

test("the rendered digest is only ever shown in a fully sandboxed frame", async ({ page }) => {
  await feedLoaded(page);
  await page.getByTestId("feed-run-btn").click();
  await page.getByText("Rendered page (sandboxed frame)").click();
  const frame = page.getByTestId("feed-digest-frame");
  await expect(frame).toBeVisible();
  await expect(frame).toHaveAttribute("sandbox", "");
});

test("a confined tick records the sandbox tier on ported nodes", async ({ page, request }) => {
  const meta = await (await request.get(`${API}/api/meta`)).json();
  test.skip(!meta.confined_tier_available, "wasmtime is not installed on the server");
  await feedLoaded(page);
  await page.getByTestId("feed-tier-confined").click();
  await page.getByTestId("feed-run-btn").click();
  await expect(page.getByTestId("node-FetchFeeds")).toContainText("sandbox");
  // The feed parser stays on the host tier, and the view says so.
  await expect(page.getByTestId("node-ParseFeeds")).toContainText("host");
});

// ── Per-item drill-down ──────────────────────────────────────────────

test("drilling into one element run shows the child graph with that run's trace", async ({
  page,
}) => {
  await feedLoaded(page);
  await page.getByTestId("feed-run-btn").click();
  await expect(page.getByTestId("elements-TriageItem")).toBeVisible();
  await page.getByTestId("node-TriageItem").click();
  await expect(page.getByTestId("element-count")).toContainText("5 element runs");
  await page.getByTestId("open-element-2").click();
  await expect(page.getByTestId("breadcrumbs")).toContainText("FeedTriage");
  await expect(page.getByTestId("breadcrumbs")).toContainText("TriageItem [2 of 5]");
  const classify = page.getByTestId("node-ClassifyItem");
  await expect(classify).toContainText("host");
  await expect(classify).toContainText("in: untrusted");
  await expect(classify).toContainText("out: trusted");
  await shoot(page, "feed-item-drilldown.png");
  // Stepping to the next element run stays inside the same node's elements.
  await page.getByTestId("element-next").click();
  await expect(page.getByTestId("breadcrumbs")).toContainText("TriageItem [3 of 5]");
  await expect(page.getByTestId("node-ClassifyItem")).toContainText("in: untrusted");
});

// ── Rewirings ────────────────────────────────────────────────────────

test("a rejected rewiring shows its reason class, its layer and the API's note", async ({
  page,
  request,
}) => {
  const cases = await (await request.get(`${API}/api/feed/cases`)).json();
  const c = cases.corpus.find((x: { name: string }) => x.name === "join_launders_one_tainted_input");
  await feedLoaded(page, c.name);
  await expect(page.getByTestId("feed-case-note")).toContainText(words(c.note));
  await page.getByTestId("feed-run-btn").click();
  await expect(page.getByTestId("rejection-banner")).toBeVisible();
  await expect(page.getByTestId("reason-class")).toContainText(c.reason);
  await expect(page.getByTestId("rejection-layer")).toContainText("Rejected by the validator");
  await shoot(page, "feed-rejection.png");
});

test("a shape-check-only rejection says the validator accepts the graph", async ({ page }) => {
  await feedLoaded(page, "http_downstream_of_a_model");
  // The rewiring itself is on screen: the digest writer now holds the client.
  await expect(page.getByTestId("node-ComposeDigest")).toContainText("HTTPClient");
  await page.getByTestId("feed-run-btn").click();
  await expect(page.getByTestId("reason-class")).toContainText("service shape");
  const layer = page.getByTestId("rejection-layer");
  await expect(layer).toContainText("The validator accepts this graph");
  await expect(layer).toContainText("only by the service's own shape check");
  await shoot(page, "feed-rejection-shape-check.png");
});

test("the accepted rewiring is reported accepted and not run", async ({ page }) => {
  await feedLoaded(page, "join_carries_taint_through");
  await page.getByTestId("feed-run-btn").click();
  await expect(page.getByTestId("feed-accepted-only")).toContainText("not run");
  await expect(page.getByTestId("rejection-banner")).toHaveCount(0);
});

// ── Hostile feeds ────────────────────────────────────────────────────

test("the hostile cases are grouped under the write-up's headings, in the API's words", async ({
  page,
  request,
}) => {
  const cases = await (await request.get(`${API}/api/feed/cases`)).json();
  await page.goto("/");
  await page.getByTestId("hostile-btn").click();
  const panel = page.getByTestId("hostile-panel");
  await expect(panel).toContainText("Structurally impossible here");
  await expect(panel).toContainText("Bounded by a limit");
  await expect(panel).toContainText("The residual: the attack succeeds");
  await expect(page.getByTestId("fooled-model-note")).toContainText("stand-in");
  await expect(page.getByTestId("fooled-model-note")).toContainText(
    "obeys every instruction it is shown",
  );
  for (const c of cases.hostile) {
    const group = page.getByTestId(`hostile-group-${c.verdict}`);
    const card = group.getByTestId(`hostile-${c.name}`);
    await expect(card).toContainText(words(c.attack));
    await expect(card).toContainText(words(c.outcome));
  }
});

test("an exfiltration run shows no request reached the attacker's host", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("hostile-btn").click();
  await page.getByTestId("run-hostile-exfiltration").click();
  await expect(page.getByTestId("fact-offlist_requests")).toContainText(
    "Requests that reached the attacker's host: 0",
  );
  await expect(page.getByTestId("fact-http_callers")).toContainText("FetchFeeds");
  await expect(page.getByTestId("fact-state_writers")).toContainText("RecordSeen");
  await expect(page.getByTestId("hostile-digest")).toContainText("# Feed digest");
  // The run's trace overlays the graph like any other.
  await expect(page.getByTestId("node-FetchFeeds")).toContainText("out: untrusted");
  await shoot(page, "feed-hostile.png");
});

test("a residual case is shown as the attack succeeding", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("hostile-btn").click();
  const card = page.getByTestId("hostile-self_promotion");
  await expect(page.getByTestId("hostile-group-residual")).toContainText(
    "The residual: the attack succeeds",
  );
  await expect(page.getByTestId("verdict-self_promotion")).toContainText("the attack succeeds");
  // Never the accepted/trusted styling: the residual carries the rejected one.
  await expect(page.getByTestId("verdict-self_promotion")).toHaveClass(/rejected/);
  await expect(page.getByTestId("verdict-self_promotion")).not.toHaveClass(/accepted|trust-trusted/);
  await page.getByTestId("run-hostile-self_promotion").click();
  await expect(page.getByTestId("attack-succeeded")).toContainText("The attack succeeds.");
  await expect(page.getByTestId("fact-hostile_in_must_read")).toContainText("true");
  await expect(page.getByTestId("fact-attacker_text_in_digest")).toContainText("true");
  await expect(card.locator(".ok")).toHaveCount(0);
  await card.scrollIntoViewIfNeeded();
  await shoot(page, "feed-hostile-residual.png");
});

// ── Latest digest ────────────────────────────────────────────────────

test("the latest-digest line shows the service's date, or the API's own message", async ({
  page,
  request,
}) => {
  const resp = await request.get(`${API}/api/feed/digest/latest`);
  const body = await resp.json();
  await page.goto("/");
  const line = page.getByTestId("latest-digest");
  if (resp.ok()) {
    await expect(line).toContainText(`Latest digest: ${body.date}`);
    await page.getByTestId("latest-digest-view").click();
    await expect(page.getByTestId("latest-digest-frame")).toHaveAttribute("sandbox", "");
  } else {
    await expect(line).toContainText(body.error);
  }
});
