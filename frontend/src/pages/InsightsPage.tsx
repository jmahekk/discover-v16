import { useEffect, useState } from "react";
import { fetchInsights } from "../lib/api";
import type { Insights } from "../lib/types";
import Bars from "../components/Bars";

export default function InsightsPage() {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchInsights()
      .then(setData)
      .catch(() => setError("Could not load insights. Check that the backend is running."));
  }, []);

  const tiles = data
    ? [
        { label: "Papers", value: data.total_papers.toLocaleString() },
        { label: "Shelves", value: String(data.categories.length) },
        { label: "Venues", value: String(data.venues.length) },
        { label: "With abstract", value: `${data.coverage.abstract}%` },
      ]
    : [];

  return (
    <main className="mx-auto max-w-6xl px-5 pb-16">
      <h1 className="pt-8 font-reading text-3xl font-medium">Insights</h1>
      <p className="mt-1 text-sm text-graphite">The corpus at a glance.</p>

      {error && (
        <div className="mt-6 rounded-lg border border-rule bg-surface p-4 text-sm text-graphite">
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {tiles.map((t) => (
              <div key={t.label} className="rounded-xl border border-rule bg-surface p-4">
                <div className="font-data text-2xl text-ink tnum">{t.value}</div>
                <div className="mt-1 text-xs uppercase tracking-widest text-graphite">
                  {t.label}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-2">
            <section>
              <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.16em] text-graphite">
                Papers per shelf
              </h2>
              <Bars items={data.categories} />
            </section>

            <section>
              <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.16em] text-graphite">
                Top venues
              </h2>
              <Bars items={data.venues} />

              <h2 className="mb-4 mt-10 text-xs font-bold uppercase tracking-[0.16em] text-graphite">
                Field coverage
              </h2>
              <div className="rounded-xl border border-rule bg-surface">
                {Object.entries(data.coverage).map(([field, pct]) => (
                  <div
                    key={field}
                    className="flex items-center justify-between border-b border-rule px-4 py-2.5 text-sm last:border-0"
                  >
                    <span className="capitalize">{field}</span>
                    <span className="font-data text-xs text-graphite tnum">{pct}%</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </main>
  );
}
