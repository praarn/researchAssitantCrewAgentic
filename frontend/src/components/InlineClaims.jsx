import VerdictStamp from "./VerdictStamp";

const MARKER = /\[\[([\w-]+)\]\]/g;

export default function InlineClaims({ text, verdictsByClaim }) {
  const parts = [];
  let lastIndex = 0;
  let match;
  let stampIndex = 0;
  MARKER.lastIndex = 0;

  while ((match = MARKER.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const v = verdictsByClaim[match[1]];
    if (v) {
      parts.push(
        <VerdictStamp
          key={`${match[1]}-${match.index}`}
          verdict={v.verdict}
          confidence={v.confidence}
          notes={v.notes}
          index={stampIndex++}
        />
      );
    }
    lastIndex = MARKER.lastIndex;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));

  return <>{parts}</>;
}
