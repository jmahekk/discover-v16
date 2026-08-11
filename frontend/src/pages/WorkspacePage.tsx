import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { search, streamAnswer, fetchMeta } from "../lib/api";
import { useSettings } from "../lib/settings";
import { addRecent } from "../lib/recent";
import type { SearchResponse, AnswerMeta, CategoryCount } from "../lib/types";
import StageStrip from "../components/StageStrip";
import RoutingNote from "../components/RoutingNote";
import AnswerView from "../components/AnswerView";
import EvidenceCard from "../components/EvidenceCard";
import PaperDrawer from "../components/PaperDrawer";

export default function WorkspacePage() {
  const [params] = useSearchParams();
  const query = params.get("q") || "";
  const { settings } = useSettings();

  const [data, setData] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const [answerText, setAnswerText] = useState("");
  const [answerStreaming, setAnswerStreaming] = useState(false);
  const [answerMs, setAnswerMs] = useState<number | null>(null);
  const [answerMeta, setAnswerMeta] = useState<AnswerMeta | null>(null);
  const [debugContext, setDebugContext] = useState("");

  const [litRef, setLitRef] = useState<number | null>(null);
  const [drawerId, setDrawerId] = useState<number | null>(null);
  const [candidatesOpen, setCandidatesOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [allCategories, setAllCategories] = useState<CategoryCount[]>([]);

  // Guards against stale updates when a new question starts mid-stream
  const runIdRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    fetchMeta().then((m) => setAllCategories(m.categories)).catch(() => {});
  }, []);

  const run = useCallback(
    async (mode: string, categories: string[]) => {
      const runId = ++runIdRef.current;
      setData(null);
      setSearching(true);
      setSearchError("");
      setAnswerText("");
      setAnswerMeta(null);
      setAnswerMs(null);
      setAnswerStreaming(false);
      setDebugContext("");
      setCandidatesOpen(false);
      setSourcesOpen(false);

      let result: SearchResponse;
      try {
        result = await search({
          query,
          mode,
          categories,
          bm25_k: settings.bm25K,
          final_k: settings.finalK,
        });
      } catch {
        if (runIdRef.current !== runId) return;
        setSearching(false);
        setSearchError(
          "Search failed. Check that the backend is running on port 8000, then try again."
        );
        return;
      }
      if (runIdRef.current !== runId) return;

      setData(result);
      setSearching(false);
      addRecent(query);

      if (result.results.length === 0) {
        setAnswerText(
          "No papers matched this question in the selected shelves. Try rephrasing, or use change above to widen the search."
        );
        return;
      }

      // Stream the answer, timing it live
      setAnswerStreaming(true);
      const start = performance.now();
      timerRef.current = window.setInterval(() => {
        if (runIdRef.current === runId) setAnswerMs(performance.now() - start);
      }, 120);

      const stop = () => {
        if (timerRef.current) window.clearInterval(timerRef.current);
        timerRef.current = null;
      };

      await streamAnswer(
        {
          query,
          paper_ids: result.results.map((r) => r.id),
          debug: settings.debugContext,
        },
        {
          onMeta: (m) => runIdRef.current === runId && setAnswerMeta(m),
          onDelta: (t) =>
            runIdRef.current === runId && setAnswerText((prev) => prev + t),
          onDone: (elapsed, context) => {
            stop();
            if (runIdRef.current !== runId) return;
            setAnswerMs(elapsed);
            setAnswerStreaming(false);
            if (context) setDebugContext(context);
          },
          onError: (msg) => {
            stop();
            if (runIdRef.current !== runId) return;
            setAnswerStreaming(false);
            setAnswerText(msg);
          },
        }
      );
      stop();
      if (runIdRef.current === runId) setAnswerStreaming(false);
    },
    [query, settings.bm25K, settings.finalK, settings.debugContext]
  );

  // New question or changed global settings: run with the configured mode
  useEffect(() => {
    if (!query.trim()) return;
    run(settings.mode, settings.mode === "manual" ? settings.manualCategories : []);
    return () => {
      runIdRef.current++;
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [query, settings.mode, settings.manualCategories, run]);

  if (!query.trim()) {
    return (
      <main className="mx-auto max-w-6xl px-5 py-16 text-graphite">
        Type a question in the bar above to begin.
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-5 pb-16">
      <StageStrip
        routeMs={data ? data.routing.elapsed_ms : null}
        bm25Ms={data ? data.timings.bm25_ms : null}
        colbertMs={data ? data.timings.colbert_ms : null}
        answerMs={answerMs}
        answerLive={answerStreaming}
        searching={searching}
      />

      {searching && (
        <div className="py-10 text-sm text-graphite">
          Finding the right shelf and reading the strongest papers...
        </div>
      )}

      {searchError && (
        <div className="mt-6 rounded-lg border border-rule bg-surface p-4 text-sm">
          {searchError}{" "}
          <button
            onClick={() =>
              run(settings.mode, settings.mode === "manual" ? settings.manualCategories : [])
            }
            className="text-ultra underline underline-offset-2"
          >
            Retry
          </button>
        </div>
      )}

      {data && (
        <>
          <RoutingNote
            routing={data.routing}
            papersInScope={data.papers_in_scope}
            allCategories={allCategories}
            onOverride={(cats) => run("manual", cats)}
            onAutomatic={() => run("auto", [])}
          />

          <div className="grid grid-cols-1 gap-10 pt-7 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
            {/* Reading side */}
            <div>
              {!answerText && answerStreaming && (
                <div className="text-sm text-graphite">Writing the answer...</div>
              )}
              <AnswerView
                text={answerText}
                streaming={answerStreaming}
                litRef={litRef}
                onHoverCite={setLitRef}
              />

              {answerMeta && !answerStreaming && (
                <div className="mt-6 border-t border-rule pt-4 text-sm text-graphite">
                  <span className="font-data text-xs">intent: {answerMeta.intent}</span>
                  <span className="mx-2">·</span>
                  <button
                    onClick={() => setSourcesOpen((v) => !v)}
                    className="text-ultra underline decoration-rule underline-offset-2 hover:decoration-ultra"
                  >
                    Sources ({answerMeta.sources.length})
                  </button>
                  {sourcesOpen && (
                    <ol className="mt-3 list-decimal space-y-1 pl-5 text-ink">
                      {answerMeta.sources.map((s, i) => (
                        <li key={i} className="text-sm">
                          {s}
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              )}

              {debugContext && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-xs text-graphite">
                    Text sent to the model
                  </summary>
                  <pre className="mt-2 max-h-80 overflow-auto rounded-lg border border-rule bg-surface p-3 font-data text-[11px] leading-relaxed">
                    {debugContext}
                  </pre>
                </details>
              )}
            </div>

            {/* Instrument side */}
            <div>
              <div className="mb-3 flex items-baseline justify-between">
                <span className="text-xs font-bold uppercase tracking-[0.16em] text-graphite">
                  Evidence
                </span>
                <button
                  onClick={() => setCandidatesOpen((v) => !v)}
                  className="text-xs text-ultra underline decoration-rule underline-offset-2 hover:decoration-ultra"
                >
                  {candidatesOpen
                    ? "hide candidates"
                    : `view all ${data.candidates.length} candidates`}
                </button>
              </div>

              <div className="flex flex-col gap-2.5">
                {data.results.map((paper, i) => (
                  <EvidenceCard
                    key={paper.id}
                    index={i + 1}
                    paper={paper}
                    lit={litRef === i + 1}
                    onHover={(on) => setLitRef(on ? i + 1 : null)}
                    onOpen={() => setDrawerId(paper.id)}
                  />
                ))}
              </div>

              {candidatesOpen && (
                <div className="mt-4 max-h-96 overflow-y-auto rounded-lg border border-rule bg-surface">
                  <div className="border-b border-rule px-3 py-2 text-xs font-bold uppercase tracking-widest text-graphite">
                    Stage 1 candidates (keyword match)
                  </div>
                  {data.candidates.map((c, i) => (
                    <button
                      key={c.id}
                      onClick={() => setDrawerId(c.id)}
                      className="flex w-full items-baseline gap-3 border-b border-rule px-3 py-2 text-left last:border-0 hover:bg-bond"
                    >
                      <span className="font-data text-[11px] text-graphite tnum">
                        {String(i + 1).padStart(3, " ")}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-xs">{c.title}</span>
                      <span className="font-data text-[11px] text-graphite tnum">
                        {c.bm25.toFixed(1)}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {drawerId !== null && (
        <PaperDrawer paperId={drawerId} onClose={() => setDrawerId(null)} />
      )}
    </main>
  );
}
