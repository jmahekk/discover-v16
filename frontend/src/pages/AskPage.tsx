import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { fetchMeta } from "../lib/api";
import type { Meta } from "../lib/types";

const EXAMPLES = [
  "What defenses exist against jailbreak attacks on LLMs?",
  "Which methods improve low-resource machine translation?",
  "How is chain-of-thought reasoning evaluated?",
];

export default function AskPage() {
  const navigate = useNavigate();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMeta()
      .then(setMeta)
      .catch(() =>
        setError(
          "The backend is not responding. Start it with: python -m uvicorn api:app --port 8000"
        )
      );
  }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`);
  };

  const total = meta ? meta.total_papers.toLocaleString() : "...";

  return (
    <main className="mx-auto max-w-6xl px-5">
      <div className="mx-auto max-w-3xl pt-20 pb-10">
        <h1 className="font-reading text-4xl font-medium leading-tight sm:text-5xl">
          Ask {total} papers.
        </h1>
        <p className="mt-3 text-graphite">
          Grounded answers from ACL, EMNLP, NAACL, EACL, CoNLL and Findings, 2025 to 2026.
          Every claim traceable to a paper.
        </p>

        {error && (
          <div className="mt-6 rounded-lg border border-rule bg-surface p-4 text-sm text-graphite">
            {error}
          </div>
        )}

        <form onSubmit={submit} className="mt-8">
          <div className="flex items-center gap-2 rounded-xl border-2 border-ink bg-surface px-4 py-3 focus-within:border-ultra">
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="What do you want to know?"
              className="w-full bg-transparent font-reading text-lg text-ink placeholder:text-graphite focus:outline-none"
            />
            <button
              type="submit"
              className="shrink-0 rounded-lg bg-ultra px-4 py-1.5 text-sm font-semibold text-white"
            >
              Search
            </button>
          </div>
        </form>

        <div className="mt-3 text-sm text-graphite">
          try:{" "}
          {EXAMPLES.map((ex, i) => (
            <span key={ex}>
              <button
                onClick={() => navigate(`/search?q=${encodeURIComponent(ex)}`)}
                className="text-ultra hover:underline"
              >
                {ex}
              </button>
              {i < EXAMPLES.length - 1 && " · "}
            </span>
          ))}
        </div>

        <div className="mt-14">
          <div className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-graphite">
            The shelves
          </div>
          <div className="grid grid-cols-1 gap-x-10 gap-y-1.5 sm:grid-cols-2">
            {(meta?.categories || []).map((c) => (
              <Link
                key={c.name}
                to={`/library?category=${encodeURIComponent(c.name)}`}
                className="group flex items-baseline justify-between border-l-[3px] border-ultra py-2 pl-3 pr-1 hover:bg-surface"
              >
                <span className="text-sm group-hover:text-ultra">{c.name}</span>
                <span className="font-data text-xs text-graphite tnum">
                  {c.count.toLocaleString()}
                </span>
              </Link>
            ))}
          </div>
        </div>

        <div className="mt-14 border-t border-rule pt-5 text-sm text-graphite">
          How it works: your question is matched to the right shelf, the strongest
          papers are retrieved and re-ranked, and the answer is written from them,
          with citations. Open Settings to take manual control.
        </div>
      </div>
    </main>
  );
}
