import { useState, useRef, useEffect } from "react";
import { Link, NavLink, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { getRecent } from "../lib/recent";
import SettingsPopover from "./SettingsPopover";

export default function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const onWorkspace = location.pathname === "/search";
  const [q, setQ] = useState(params.get("q") || "");
  const [recentOpen, setRecentOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const recentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setQ(params.get("q") || "");
  }, [params]);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (recentRef.current && !recentRef.current.contains(e.target as Node)) {
        setRecentOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`);
  };

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm ${isActive ? "text-ultra font-semibold" : "text-graphite hover:text-ink"}`;

  const recent = getRecent();

  return (
    <header className="border-b border-rule bg-surface">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-3">
        <Link
          to="/"
          className="font-reading text-sm font-medium tracking-[0.24em] text-ink"
        >
          DISCOVER
        </Link>

        <nav className="hidden items-center gap-5 sm:flex">
          <NavLink to="/" end className={navClass}>
            Ask
          </NavLink>
          <NavLink to="/library" className={navClass}>
            Library
          </NavLink>
          <NavLink to="/insights" className={navClass}>
            Insights
          </NavLink>
        </nav>

        {onWorkspace && (
          <form onSubmit={submit} className="min-w-0 flex-1">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ask another question"
              className="w-full rounded-lg border border-rule bg-bond px-3 py-1.5 font-reading text-sm text-ink placeholder:text-graphite focus:border-ultra focus:outline-none"
            />
          </form>
        )}

        <div className="ml-auto flex items-center gap-4">
          <div className="relative" ref={recentRef}>
            <button
              onClick={() => setRecentOpen((v) => !v)}
              className="text-sm text-graphite hover:text-ink"
            >
              Recent
            </button>
            {recentOpen && (
              <div className="absolute right-0 top-8 z-40 w-80 rounded-lg border border-rule bg-surface p-2 shadow-lg">
                {recent.length === 0 && (
                  <div className="px-3 py-2 text-sm text-graphite">
                    Questions you ask will appear here.
                  </div>
                )}
                {recent.map((r) => (
                  <button
                    key={r.when}
                    onClick={() => {
                      setRecentOpen(false);
                      navigate(`/search?q=${encodeURIComponent(r.query)}`);
                    }}
                    className="block w-full truncate rounded px-3 py-2 text-left text-sm text-ink hover:bg-bond"
                  >
                    {r.query}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={() => setSettingsOpen(true)}
            aria-label="Settings"
            className="text-graphite hover:text-ink"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.01a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55h.01a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.01a1.7 1.7 0 0 0 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.55 1z" />
            </svg>
          </button>
        </div>
      </div>
      {settingsOpen && <SettingsPopover onClose={() => setSettingsOpen(false)} />}
    </header>
  );
}
