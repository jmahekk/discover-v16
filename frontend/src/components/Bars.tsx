import type { CategoryCount } from "../lib/types";

export default function Bars({ items }: { items: CategoryCount[] }) {
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <div className="flex flex-col gap-2.5">
      {items.map((item) => (
        <div key={item.name} className="grid grid-cols-[minmax(0,1fr)_56px] items-center gap-3">
          <div>
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <span className="truncate text-sm">{item.name}</span>
            </div>
            <div className="h-2 rounded-sm bg-rule">
              <div
                className="h-2 rounded-sm bg-ultra"
                style={{ width: `${(100 * item.count) / max}%` }}
              />
            </div>
          </div>
          <div className="text-right font-data text-xs text-graphite tnum">
            {item.count.toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}
