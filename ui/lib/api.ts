import type {
  CorpusCase,
  GraphDoc,
  GraphIndexEntry,
  InjectionScenario,
  Meta,
  RunResponse,
} from "./types";

// All calls go through the Next.js rewrite to the Python inspector API — the
// UI's only source of graphs and traces.

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`${url}: ${resp.status}`);
  return resp.json();
}

export const fetchMeta = () => getJson<Meta>("/api/meta");

export const fetchGraphIndex = async (): Promise<GraphIndexEntry[]> =>
  (await getJson<{ graphs: GraphIndexEntry[] }>("/api/graphs")).graphs;

// The canonical file, served byte-for-byte by the API; parsing happens here,
// for display only.
export const fetchGraph = (file: string) => getJson<GraphDoc>(`/api/graphs/${file}`);

export const fetchCorpus = async (): Promise<CorpusCase[]> =>
  (await getJson<{ cases: CorpusCase[] }>("/api/corpus")).cases;

// The graph a corpus case validates — for mutation cases, the canonical base
// with the harness's own mutation applied, derived server-side on demand.
export const fetchCaseGraph = async (name: string): Promise<GraphDoc> =>
  (await getJson<{ case: string; graph: GraphDoc }>(`/api/corpus/${name}/graph`)).graph;

export async function runCase(body: {
  case: string;
  message?: string;
  tier?: "host" | "confined";
}): Promise<RunResponse> {
  const resp = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await resp.json();
  if (!resp.ok && !payload.rejected) {
    throw new Error(payload.error ?? `run failed: ${resp.status}`);
  }
  return payload;
}

export async function runInjectionScenario(): Promise<InjectionScenario> {
  const resp = await fetch("/api/scenario/injection", { method: "POST", body: "{}" });
  if (!resp.ok) {
    const payload = await resp.json().catch(() => ({}));
    throw new Error(payload.error ?? `scenario failed: ${resp.status}`);
  }
  return resp.json();
}
