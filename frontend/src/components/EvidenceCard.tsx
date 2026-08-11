import type { ResultPaper } from "../lib/types";

interface Props {
  index: number; // 1-based, matches the [N] citations in the answer
  paper: ResultPaper;
  lit: boolean;
  onHover: (on: boolean) => void;
  onOpen: () => void;
}

export default function EvidenceCard({ index, paper, lit, onHover, onOpen }: Props) {
  return (
    <button
      className={`evcard block w-full rounded-lg border border-rule bg-surface p-3.5 text-left ${
        lit ? "lit" : ""
      }`}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onClick={onOpen}
    >
      <div className="font-data text-xs text-ultra">[{index}]</div>
      <div className="mt-0.5 text-sm font-semibold leading-snug">{paper.title}</div>
      <div className="mt-1 truncate text-xs text-graphite">
        {paper.authors}
        {paper.publication ? ` · ${paper.publication}` : ""}
      </div>
      <div className="mt-2 font-data text-[11px] text-graphite tnum">
        colbert <span className="font-medium text-ultra">{paper.colbert.toFixed(2)}</span>
        {"   "}
        bm25 <span className="font-medium text-ultra">{paper.bm25.toFixed(2)}</span>
      </div>
    </button>
  );
}
