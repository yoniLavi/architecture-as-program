import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

// Each test here backs a behaviour the paper asserts about the inspector — the
// testing bar of the `graph-inspector` spec: what is not covered here (or in the
// Python contract tests) is not claimed. The screenshots written to
// `screenshots/` are the committed figures the paper build copies into dist/,
// so the paper's images regenerate from the artifact rather than being pasted.

const SHOTS = path.join(__dirname, "..", "screenshots");
fs.mkdirSync(SHOTS, { recursive: true });

async function shoot(page: Page, name: string) {
  await page.screenshot({ path: path.join(SHOTS, name), animations: "disabled" });
}

async function loaded(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("node-ReceiveMessage")).toBeVisible();
}

// ── Canonical rendering ──────────────────────────────────────────────

test("the graph view renders exactly the nodes of the served canonical JSON", async ({
  page,
  request,
}) => {
  // The canonical source, fetched from the same endpoint the UI consumes
  // (which the Python suite pins byte-identical to graphs/customer-support.json).
  const doc = await (await request.get("http://127.0.0.1:8123/api/graphs/customer-support")).json();
  await loaded(page);
  for (const node of doc.nodes) {
    await expect(page.getByTestId(`node-${node.name}`)).toBeVisible();
  }
  await expect(page.locator(".signal-node")).toHaveCount(doc.nodes.length);
});

test("node detail shows the signature and with clause parsed from the source", async ({ page }) => {
  await loaded(page);
  await page.getByTestId("node-ParseMessage").click();
  const detail = page.getByTestId("detail-panel");
  await expect(detail).toContainText("discharges trust");
  await expect(detail).toContainText("Untrusted<RawMessage>");
  await expect(detail).toContainText("LLMClient<inference>");
});

// ── Run → trace ──────────────────────────────────────────────────────

test("a run overlays the runtime's trace: tiers, trust, crossings, terminal", async ({ page }) => {
  await loaded(page);
  await page.getByTestId("run-btn").click();
  // Tier badges appear on executed nodes; the benign message takes the ok path.
  await expect(page.getByTestId("node-GenerateResponse")).toContainText("host");
  await expect(page.getByTestId("node-ParseMessage")).toContainText("in: untrusted");
  await expect(page.getByTestId("node-ParseMessage")).toContainText("out: trusted");
  await expect(page.getByTestId("detail-panel").getByTestId("terminal")).toContainText(
    "DeliveryConfirmation",
  );
  // Crossings with instance names, from the trace.
  await page.getByTestId("node-GenerateResponse").click();
  const crossings = page.getByTestId("crossing");
  await expect(crossings.first()).toBeVisible();
  await expect(page.getByTestId("detail-panel")).toContainText("aap:caps/tool-llm");
  await shoot(page, "inspector-run-host.png");
});

// ── Rejection ────────────────────────────────────────────────────────

test("an unsafe mutation is refused with its pinned reason class shown", async ({ page }) => {
  await loaded(page);
  await page.getByTestId("case-launder_trust").click();
  await expect(page.getByTestId("node-GenerateResponse")).toContainText("Untrusted<RawMessage>");
  await page.getByTestId("run-btn").click();
  const banner = page.getByTestId("rejection-banner");
  await expect(banner).toBeVisible();
  await expect(page.getByTestId("reason-class")).toContainText("trust lattice");
  await expect(banner).toContainText("laundering");
  await shoot(page, "inspector-rejection.png");
});

// ── Sub-graph nesting ────────────────────────────────────────────────

test("a composed run nests: drill into the sub-graph trace, identity visible", async ({
  page,
}) => {
  await loaded(page);
  await page.getByTestId("case-support-platform").click();
  await page.getByTestId("run-btn").click();
  const subNode = page.getByTestId("node-CustomerSupport");
  await expect(subNode).toContainText("graph"); // the non-tier, reported as such
  await page.getByTestId("open-CustomerSupport").click();
  await expect(page.getByTestId("breadcrumbs")).toContainText("SupportPlatform");
  await expect(page.getByTestId("breadcrumbs")).toContainText("CustomerSupport");
  // The nested trace, one level down, with the parent-declared instance label
  // on the reply node's crossing — identity routing, visible.
  await page.getByTestId("node-SendReply").click();
  await expect(page.getByTestId("detail-panel")).toContainText("customer_session");
  await shoot(page, "inspector-subgraph.png");
});

// ── The injection walkthrough ────────────────────────────────────────

test("the walkthrough shows taint to the discharge node and nowhere after", async ({ page }) => {
  await loaded(page);
  await page.getByTestId("walkthrough-btn").click();
  await expect(page.getByTestId("walkthrough")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("adversarial-message")).toContainText("Ignore all previous");

  await page.getByTestId("walk-next").click();
  // The taint step: exactly one edge carries the Untrusted label — the one into
  // the discharge node — and the trace-derived fact confirms the sole raiser.
  await expect(page.getByTestId("fact-raisers")).toContainText("ParseMessage");
  await expect(page.getByTestId("fact-raisers")).toContainText("✓");
  const untrustedEdges = page.locator(".react-flow__edge", { hasText: "Untrusted" });
  await expect(untrustedEdges).toHaveCount(1);
  await shoot(page, "inspector-walkthrough-taint.png");

  await page.getByTestId("walk-next").click();
  await expect(page.getByTestId("fact-refused")).toContainText("refused");

  await page.getByTestId("walk-next").click();
  // The residual, honestly shown: true, on the confined run where available.
  await expect(page.getByTestId("fact-residual")).toContainText("true");
});

test("the tier contrast surfaces the recorded difference between the runs", async ({
  page,
  request,
}) => {
  const meta = await (await request.get("http://127.0.0.1:8123/api/meta")).json();
  await loaded(page);
  await page.getByTestId("walkthrough-btn").click();
  await expect(page.getByTestId("walkthrough")).toBeVisible({ timeout: 30_000 });
  for (let i = 0; i < 4; i++) await page.getByTestId("walk-next").click();

  const table = page.getByTestId("tier-table");
  await expect(table).toBeVisible();
  const parseRow = table.locator("tr", { hasText: "ParseMessage" });
  await expect(parseRow).toContainText("host");
  if (meta.confined_tier_available) {
    // The recorded difference: the same node, host on one run, sandbox on the other.
    await expect(parseRow).toContainText("sandbox");
    await shoot(page, "inspector-tier-contrast.png");
  }
});
