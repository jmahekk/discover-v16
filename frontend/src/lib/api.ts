import type {
  Meta,
  SearchResponse,
  PaperDetail,
  PaperSummary,
  Insights,
  AnswerMeta,
} from "./types";

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

export function fetchMeta(): Promise<Meta> {
  return getJson("/api/meta");
}

export function fetchInsights(): Promise<Insights> {
  return getJson("/api/insights");
}

export function fetchPaper(id: number): Promise<PaperDetail> {
  return getJson(`/api/papers/${id}`);
}

export function fetchPapers(params: {
  category?: string;
  venue?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<{ total: number; page: number; page_size: number; papers: PaperSummary[] }> {
  const search = new URLSearchParams();
  if (params.category) search.set("category", params.category);
  if (params.venue) search.set("venue", params.venue);
  if (params.q) search.set("q", params.q);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  return getJson(`/api/papers?${search.toString()}`);
}

export async function search(body: {
  query: string;
  mode: string;
  categories: string[];
  bm25_k: number;
  final_k: number;
}): Promise<SearchResponse> {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

export async function streamAnswer(
  body: { query: string; paper_ids: number[]; debug: boolean },
  handlers: {
    onMeta: (meta: AnswerMeta) => void;
    onDelta: (text: string) => void;
    onDone: (elapsedMs: number, context?: string) => void;
    onError: (message: string) => void;
  }
): Promise<void> {
  let res: Response;
  try {
    res = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    handlers.onError("Could not reach the server. Is the backend running?");
    return;
  }
  if (!res.ok || !res.body) {
    handlers.onError(`Answer request failed: ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let newline;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (!line) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.type === "meta") handlers.onMeta(msg);
        else if (msg.type === "delta") handlers.onDelta(msg.text);
        else if (msg.type === "done") handlers.onDone(msg.elapsed_ms, msg.context);
      } catch {
        // Ignore malformed lines rather than breaking the stream
      }
    }
  }
}
