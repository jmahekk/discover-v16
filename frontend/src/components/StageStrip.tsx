interface Props {
  routeMs: number | null;
  bm25Ms: number | null;
  colbertMs: number | null;
  answerMs: number | null;
  answerLive: boolean;
  searching: boolean;
}

export default function StageStrip({
  routeMs,
  bm25Ms,
  colbertMs,
  answerMs,
  answerLive,
  searching,
}: Props) {
  const fmt = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`);

  const stage = (label: string, ms: number | null, live: boolean, pending: boolean) => (
    <span
      className={`font-data text-xs tnum ${
        ms !== null || live ? "text-ink" : "text-graphite/60"
      }`}
    >
      {label}{" "}
      {ms !== null && !live && <span className="text-ultra font-medium">{fmt(ms)}</span>}
      {live && ms !== null && (
        <span className="text-ultra font-medium">
          {fmt(ms)}
          <span className="ml-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-ultra align-middle" />
        </span>
      )}
      {ms === null && pending && <span className="text-graphite">. . .</span>}
    </span>
  );

  return (
    <div className="flex flex-wrap items-center gap-x-7 gap-y-1 border-b border-rule py-2.5">
      {stage("ROUTE", routeMs, false, searching)}
      {stage("RETRIEVE", bm25Ms, false, searching)}
      {stage("RE-RANK", colbertMs, false, searching)}
      {stage("ANSWER", answerMs, answerLive, !searching && answerMs === null)}
    </div>
  );
}
