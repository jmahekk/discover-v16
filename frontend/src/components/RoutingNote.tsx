import { useState } from "react";
import type { Routing, CategoryCount } from "../lib/types";

interface Props {
  routing: Routing;
  papersInScope: number;
  allCategories: CategoryCount[];
  onOverride: (categories: string[]) => void;
  onAutomatic: () => void;
}

export default function RoutingNote({
  routing,
  papersInScope,
  allCategories,
  onOverride,
  onAutomatic,
}: Props) {
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState<string[]>(routing.categories);

  const scope = `${papersInScope.toLocaleString()} papers`;

  let sentence;
  if (routing.mode === "all" && routing.confidence === "low") {
    sentence = (
      <>
        This question is broad, so the whole library is being searched
        <span className="text-graphite"> · {scope}</span>
      </>
    );
  } else if (routing.mode === "all") {
    sentence = (
      <>
        Searching the whole library
        <span className="text-graphite"> · {scope}</span>
      </>
    );
  } else if (routing.confidence === "manual") {
    sentence = (
      <>
        Searching your selection:{" "}
        <span className="font-semibold">{routing.categories.join(", ")}</span>
        <span className="text-graphite"> · {scope}</span>
      </>
    );
  } else {
    sentence = (
      <>
        Searching <span className="font-semibold">{routing.categories.join(", ")}</span>
        <span className="text-graphite"> · {scope} · </span>
        <span className="font-data text-xs text-graphite">{routing.confidence} confidence</span>
      </>
    );
  }

  const toggle = (name: string) =>
    setPicked((prev) =>
      prev.includes(name) ? prev.filter((c) => c !== name) : [...prev, name]
    );

  return (
    <div className="relative border-b border-rule py-3 text-sm">
      {sentence}{" "}
      <button
        onClick={() => {
          setPicked(routing.categories);
          setOpen((v) => !v);
        }}
        className="text-ultra underline decoration-rule underline-offset-2 hover:decoration-ultra"
      >
        change
      </button>

      {open && (
        <div className="absolute left-0 top-12 z-30 w-96 max-w-full rounded-xl border border-rule bg-surface p-4 shadow-xl">
          <div className="mb-2 text-xs font-bold uppercase tracking-widest text-graphite">
            Search these shelves instead
          </div>
          <div className="max-h-52 overflow-y-auto">
            {allCategories.map((c) => (
              <label
                key={c.name}
                className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-bond"
              >
                <input
                  type="checkbox"
                  checked={picked.includes(c.name)}
                  onChange={() => toggle(c.name)}
                  className="accent-[var(--ultra)]"
                />
                <span className="flex-1">{c.name}</span>
                <span className="font-data text-xs text-graphite tnum">{c.count}</span>
              </label>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={() => {
                setOpen(false);
                onOverride(picked);
              }}
              disabled={picked.length === 0}
              className="rounded-lg bg-ultra px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              Search again
            </button>
            <button
              onClick={() => {
                setOpen(false);
                onAutomatic();
              }}
              className="text-sm text-graphite underline underline-offset-2 hover:text-ink"
            >
              Back to automatic
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
