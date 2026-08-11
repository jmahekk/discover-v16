import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchMeta, fetchPapers } from "../lib/api";
import type { Meta, PaperSummary } from "../lib/types";
import PaperDrawer from "../components/PaperDrawer";

const PAGE_SIZE = 25;

export default function LibraryPage() {
  const [params, setParams] = useSearchParams();
  const [meta, setMeta] = useState<Meta | null>(null);

  const category = params.get("category") || "";
  const venue = params.get("venue") || "";
  const qParam = params.get("q") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);

  const [qInput, setQInput] = useState(qParam);
  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [drawerId, setDrawerId] = useState<number | null>(null);

  useEffect(() => {
    fetchMeta().then(setMeta).catch(() => {});
  }, []);

  // Debounce the free-text filter so we do not query on every keystroke
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (qInput !== qParam) updateParams({ q: qInput, page: "" });
    }, 350);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qInput]);

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchPapers({ category, venue, q: qParam, page, page_size: PAGE_SIZE })
      .then((res) => {
        setPapers(res.papers);
        setTotal(res.total);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
        setError("Could not load papers. Check that the backend is running.");
      });
  }, [category, venue, qParam, page]);

  function updateParams(patch: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    setParams(next);
  }

  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="mx-auto max-w-6xl px-5 pb-16">
      <div className="flex flex-wrap items-end justify-between gap-4 pt-8">
        <div>
          <h1 className="font-reading text-3xl font-medium">Library</h1>
          <p className="mt-1 text-sm text-graphite">
            {loading ? "Counting..." : `${total.toLocaleString()} papers`}
            {category && ` on the ${category} shelf`}
            {venue && ` from ${venue}`}
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <input
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          placeholder="Filter by title, author or keyword"
          className="w-72 max-w-full rounded-lg border border-rule bg-surface px-3 py-2 text-sm placeholder:text-graphite focus:border-ultra focus:outline-none"
        />
        <select
          value={category}
          onChange={(e) => updateParams({ category: e.target.value, page: "" })}
          className="rounded-lg border border-rule bg-surface px-3 py-2 text-sm"
        >
          <option value="">All shelves</option>
          {(meta?.categories || []).map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={venue}
          onChange={(e) => updateParams({ venue: e.target.value, page: "" })}
          className="rounded-lg border border-rule bg-surface px-3 py-2 text-sm"
        >
          <option value="">All venues</option>
          {(meta?.venues || []).map((v) => (
            <option key={v.name} value={v.name}>
              {v.name}
            </option>
          ))}
        </select>
        {(category || venue || qParam) && (
          <button
            onClick={() => {
              setQInput("");
              updateParams({ category: "", venue: "", q: "", page: "" });
            }}
            className="text-sm text-ultra underline underline-offset-2"
          >
            Clear filters
          </button>
        )}
      </div>

      {error && (
        <div className="mt-6 rounded-lg border border-rule bg-surface p-4 text-sm text-graphite">
          {error}
        </div>
      )}

      <div className="mt-6 overflow-hidden rounded-xl border border-rule bg-surface">
        {loading && <div className="p-6 text-sm text-graphite">Loading papers...</div>}
        {!loading && papers.length === 0 && !error && (
          <div className="p-6 text-sm text-graphite">
            Nothing matches these filters. Clear them to see the whole library.
          </div>
        )}
        {!loading &&
          papers.map((p) => (
            <button
              key={p.id}
              onClick={() => setDrawerId(p.id)}
              className="block w-full border-b border-rule px-5 py-3.5 text-left last:border-0 hover:bg-bond"
            >
              <div className="text-sm font-semibold leading-snug">{p.title}</div>
              <div className="mt-1 flex flex-wrap items-baseline gap-x-3 text-xs text-graphite">
                <span className="truncate">{p.authors}</span>
                {p.publication && <span className="font-data">{p.publication}</span>}
                {p.broad_category && <span className="text-ultra">{p.broad_category}</span>}
              </div>
            </button>
          ))}
      </div>

      {total > PAGE_SIZE && (
        <div className="mt-5 flex items-center gap-4 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => updateParams({ page: String(page - 1) })}
            className="rounded-lg border border-rule bg-surface px-4 py-1.5 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="font-data text-xs text-graphite tnum">
            page {page} of {lastPage}
          </span>
          <button
            disabled={page >= lastPage}
            onClick={() => updateParams({ page: String(page + 1) })}
            className="rounded-lg border border-rule bg-surface px-4 py-1.5 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {drawerId !== null && (
        <PaperDrawer paperId={drawerId} onClose={() => setDrawerId(null)} />
      )}
    </main>
  );
}
