import { useEffect, useState } from "react";
import { useSettings } from "../lib/settings";
import { fetchMeta } from "../lib/api";
import type { CategoryCount } from "../lib/types";

export default function SettingsPopover({ onClose }: { onClose: () => void }) {
  const { settings, update } = useSettings();
  const [categories, setCategories] = useState<CategoryCount[]>([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  useEffect(() => {
    fetchMeta().then((m) => setCategories(m.categories)).catch(() => {});
  }, []);

  const toggleCategory = (name: string) => {
    const list = settings.manualCategories.includes(name)
      ? settings.manualCategories.filter((c) => c !== name)
      : [...settings.manualCategories, name];
    update({ manualCategories: list });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end bg-black/20 p-4"
      onClick={onClose}
    >
      <div
        className="mt-10 w-96 max-w-full rounded-xl border border-rule bg-surface p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-widest text-graphite">
            Settings
          </h2>
          <button onClick={onClose} className="text-graphite hover:text-ink" aria-label="Close settings">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="mb-2 text-sm font-semibold">How categories are chosen</div>
        <div className="flex flex-col gap-2">
          {(
            [
              ["auto", "Automatic", "The system reads your question and picks the right shelves itself. Recommended."],
              ["manual", "Manual", "You choose which shelves to search."],
              ["all", "Everything", "No category filter. Slower on broad questions."],
            ] as const
          ).map(([value, label, help]) => (
            <label key={value} className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-rule p-3 hover:border-ultra">
              <input
                type="radio"
                name="mode"
                checked={settings.mode === value}
                onChange={() => update({ mode: value })}
                className="mt-0.5 accent-[var(--ultra)]"
              />
              <span>
                <span className="block text-sm font-semibold">{label}</span>
                <span className="block text-xs text-graphite">{help}</span>
              </span>
            </label>
          ))}
        </div>

        {settings.mode === "manual" && (
          <div className="mt-3 max-h-44 overflow-y-auto rounded-lg border border-rule p-2">
            {categories.map((c) => (
              <label key={c.name} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-bond">
                <input
                  type="checkbox"
                  checked={settings.manualCategories.includes(c.name)}
                  onChange={() => toggleCategory(c.name)}
                  className="accent-[var(--ultra)]"
                />
                <span className="flex-1">{c.name}</span>
                <span className="font-data text-xs text-graphite tnum">{c.count}</span>
              </label>
            ))}
          </div>
        )}

        <button
          onClick={() => setAdvancedOpen((v) => !v)}
          className="mt-4 text-xs font-semibold uppercase tracking-widest text-ultra"
        >
          {advancedOpen ? "Hide advanced" : "Advanced"}
        </button>

        {advancedOpen && (
          <div className="mt-3 flex flex-col gap-3 border-t border-rule pt-3">
            <label className="flex items-center justify-between text-sm">
              <span>
                Candidates from keyword search
                <span className="block text-xs text-graphite">Stage 1 pool size (BM25)</span>
              </span>
              <input
                type="number"
                min={50}
                max={200}
                step={10}
                value={settings.bm25K}
                onChange={(e) => update({ bm25K: Number(e.target.value) || 100 })}
                className="w-20 rounded border border-rule bg-bond px-2 py-1 text-right font-data text-sm"
              />
            </label>
            <label className="flex items-center justify-between text-sm">
              <span>
                Papers used for the answer
                <span className="block text-xs text-graphite">Stage 2 results (ColBERT)</span>
              </span>
              <input
                type="number"
                min={3}
                max={15}
                value={settings.finalK}
                onChange={(e) => update({ finalK: Number(e.target.value) || 7 })}
                className="w-20 rounded border border-rule bg-bond px-2 py-1 text-right font-data text-sm"
              />
            </label>
            <label className="flex items-center justify-between text-sm">
              <span>
                Show the exact text sent to the model
                <span className="block text-xs text-graphite">For debugging answers</span>
              </span>
              <input
                type="checkbox"
                checked={settings.debugContext}
                onChange={(e) => update({ debugContext: e.target.checked })}
                className="accent-[var(--ultra)]"
              />
            </label>
          </div>
        )}
      </div>
    </div>
  );
}
