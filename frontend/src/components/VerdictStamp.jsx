const STYLES = {
  verified: {
    color: "text-verified",
    border: "border-verified/70",
    bg: "bg-verified/10",
    label: "Verified",
    glyph: "✓",
  },
  plausible: {
    color: "text-plausible",
    border: "border-plausible/70",
    bg: "bg-plausible/10",
    label: "Plausible",
    glyph: "~",
  },
  unverified: {
    color: "text-unverified",
    border: "border-unverified/70",
    bg: "bg-unverified/10",
    label: "Unverified",
    glyph: "?",
  },
  contradicted: {
    color: "text-contradicted",
    border: "border-contradicted/70",
    bg: "bg-contradicted/10",
    label: "Contradicted",
    glyph: "×",
  },
};

export default function VerdictStamp({ verdict, confidence, notes, index }) {
  const style = STYLES[verdict] || STYLES.unverified;
  return (
    <span className="relative inline-block group align-middle mx-0.5">
      <span
        className={`stamp ${style.color} ${style.border} ${style.bg} animate-stampIn`}
        style={{ animationDelay: `${Math.min(index || 0, 8) * 40}ms` }}
      >
        <span>{style.glyph}</span>
        <span>{style.label}</span>
        {confidence && <span className="opacity-60">· {confidence}</span>}
      </span>
      {notes && (
        <span className="pointer-events-none absolute left-1/2 bottom-full z-20 mb-2 w-56 -translate-x-1/2 rounded-md border border-rule bg-panel2 p-2 text-[11px] leading-snug text-bone/90 font-sans opacity-0 shadow-paper transition-opacity duration-150 group-hover:opacity-100">
          {notes}
        </span>
      )}
    </span>
  );
}
