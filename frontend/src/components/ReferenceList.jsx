const TYPE_LABEL = {
  academic: "Academic",
  official: "Official",
  news: "News",
  reference: "Reference",
  blog_or_forum: "Blog/Forum",
  other: "Web",
};

export default function ReferenceList({ references }) {
  if (!references.length) return null;
  return (
    <div className="mt-10 border-t border-black/10 pt-6">
      <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-[#6B6852]">
        Sources · {references.length}
      </div>
      <ol className="space-y-2">
        {references.map((ref, i) => (
          <li key={ref.source_id} className="flex items-start gap-3 text-sm">
            <span className="font-mono text-xs text-[#8A876E] pt-0.5 w-5 shrink-0">{i + 1}.</span>
            <div className="min-w-0">
              <a
                href={ref.url}
                target="_blank"
                rel="noreferrer"
                className="text-[#1B1A16] hover:text-[#8A5A2E] underline decoration-black/20 underline-offset-2 break-words"
              >
                {ref.title || ref.domain}
              </a>
              <div className="text-xs text-[#6B6852] mt-0.5">
                {ref.domain} · {TYPE_LABEL[ref.source_type] || "Web"}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
