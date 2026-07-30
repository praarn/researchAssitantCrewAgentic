import InlineClaims from "./InlineClaims";
import ReferenceList from "./ReferenceList";

function statBlock(label, value) {
  return (
    <div className="min-w-[6.5rem]">
      <div className="font-display text-2xl text-bone">{value}</div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-ash">{label}</div>
    </div>
  );
}

function reportToMarkdown(report) {
  const lines = [`# ${report.title}`, "", report.executive_summary, ""];
  for (const s of report.sections) {
    lines.push(`## ${s.heading}`, "", s.body.replace(/\[\[([\w-]+)\]\]/g, "").trim(), "");
  }
  lines.push("## Sources", "");
  report.references.forEach((r, i) => lines.push(`${i + 1}. [${r.title || r.domain}](${r.url})`));
  return lines.join("\n");
}

function downloadMarkdown(report) {
  const blob = new Blob([reportToMarkdown(report)], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${report.title.slice(0, 60).replace(/[^\w\- ]/g, "").trim() || "research-report"}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportView({ report, onNewQuery }) {
  const verdictsByClaim = Object.fromEntries(report.verdicts.map((v) => [v.claim_id, v]));

  return (
    <div className="w-full max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-[0.2em] text-ash">Case File · Closed</span>
        <div className="flex gap-2">
          <button
            onClick={() => downloadMarkdown(report)}
            className="rounded-md border border-rule px-3 py-1.5 text-xs font-medium text-bone hover:border-ash/60 transition-colors"
          >
            Download .md
          </button>
          <button
            onClick={onNewQuery}
            className="rounded-md border border-rule px-3 py-1.5 text-xs font-medium text-ash hover:text-bone hover:border-ash/60 transition-colors"
          >
            New research
          </button>
        </div>
      </div>

      <div className="rounded-xl bg-paper text-[#1B1A16] shadow-paper px-6 py-8 sm:px-10 sm:py-10">
        <h1 className="font-display text-3xl sm:text-4xl leading-tight text-[#1B1A16]">
          {report.title}
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed text-[#42402F]">
          {report.executive_summary}
        </p>

        <div className="mt-6 flex flex-wrap gap-x-8 gap-y-3 border-y border-black/10 py-4">
          {statBlock("Threads", report.stats.sub_questions)}
          {statBlock("Sources", report.stats.sources_consulted)}
          {statBlock("Claims", report.stats.claims_extracted)}
          {statBlock("Verified", report.stats.claims_verified)}
          {statBlock("Contested", report.stats.claims_contradicted)}
          {statBlock("Seconds", report.stats.elapsed_seconds)}
        </div>

        <div className="mt-8 space-y-8">
          {report.sections.map((s) => (
            <section key={s.sub_question_id}>
              <h2 className="font-display text-xl text-[#1B1A16] mb-2">{s.heading}</h2>
              <p className="text-[15px] leading-[1.8] text-[#2B2A24]">
                <InlineClaims text={s.body} verdictsByClaim={verdictsByClaim} />
              </p>
            </section>
          ))}
        </div>

        <div className="text-[#1B1A16]">
          <ReferenceList references={report.references} />
        </div>
      </div>
    </div>
  );
}
