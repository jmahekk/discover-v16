import { useEffect, useState } from "react";
import { fetchPaper } from "../lib/api";
import type { PaperDetail } from "../lib/types";

interface Props {
  paperId: number;
  onClose: () => void;
}

export default function PaperDrawer({ paperId, onClose }: Props) {
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setPaper(null);
    setError("");
    fetchPaper(paperId)
      .then(setPaper)
      .catch(() => setError("Could not load this paper. Check that the backend is running."));
  }, [paperId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const section = (label: string, body: string) =>
    body ? (
      <div className="mt-5">
        <div className="mb-1.5 text-xs font-bold uppercase tracking-widest text-graphite">
          {label}
        </div>
        <div className="reading text-[0.98rem]">{body}</div>
      </div>
    ) : null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/25" onClick={onClose}>
      <div
        className="h-full w-full max-w-xl overflow-y-auto border-l border-rule bg-surface p-7"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-reading text-xl font-medium leading-snug">
            {paper ? paper.title : error ? "Paper" : "Loading paper..."}
          </h2>
          <button onClick={onClose} aria-label="Close paper" className="mt-1 shrink-0 text-graphite hover:text-ink">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && <p className="mt-4 text-sm text-graphite">{error}</p>}

        {paper && (
          <>
            <p className="mt-1.5 text-sm text-graphite">{paper.authors}</p>

            <div className="mt-3 flex flex-wrap gap-2">
              {paper.publication && (
                <span className="rounded-full border border-rule px-3 py-0.5 text-xs text-graphite">
                  {paper.publication}
                </span>
              )}
              {paper.broad_category && (
                <span className="rounded-full border border-ultra/40 px-3 py-0.5 text-xs text-ultra">
                  {paper.broad_category}
                </span>
              )}
              {paper.category && (
                <span className="rounded-full border border-rule px-3 py-0.5 text-xs text-graphite">
                  {paper.category}
                </span>
              )}
            </div>

            {section("Abstract", paper.abstract)}
            {section("Novelty", paper.novelty)}
            {section("Limitations", paper.limitations)}
            {section("Conclusion", paper.conclusion)}

            {paper.keywords && (
              <div className="mt-5 border-t border-rule pt-4 text-xs text-graphite">
                Keywords: {paper.keywords}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
