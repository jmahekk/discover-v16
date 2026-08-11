import { Fragment } from "react";

interface Props {
  text: string;
  streaming: boolean;
  litRef: number | null;
  onHoverCite: (ref: number | null) => void;
}

export default function AnswerView({ text, streaming, litRef, onHoverCite }: Props) {
  const paragraphs = text.split(/\n{2,}|\r\n{2,}/).filter((p) => p.trim());

  const renderParagraph = (para: string, pi: number) => {
    const parts = para.split(/(\[\d+\])/g);
    return (
      <p key={pi}>
        {parts.map((part, i) => {
          const match = part.match(/^\[(\d+)\]$/);
          if (match) {
            const n = Number(match[1]);
            return (
              <button
                key={i}
                className={`cite ${litRef === n ? "lit" : ""}`}
                onMouseEnter={() => onHoverCite(n)}
                onMouseLeave={() => onHoverCite(null)}
                onFocus={() => onHoverCite(n)}
                onBlur={() => onHoverCite(null)}
              >
                [{n}]
              </button>
            );
          }
          return <Fragment key={i}>{part}</Fragment>;
        })}
      </p>
    );
  };

  return (
    <div className={`reading ${streaming && text ? "caret" : ""}`}>
      {paragraphs.map(renderParagraph)}
    </div>
  );
}
