const AGENT_NAMES = {
  planner: "Planner",
  search: "Search",
  summarizer: "Summarizer",
  fact_checker: "Fact-Checker",
  writer: "Report Writer",
};

function StageIcon({ status }) {
  if (status === "done") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-verified/60 bg-verified/10 text-verified text-[11px]">
        ✓
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-contradicted/60 bg-contradicted/10 text-contradicted text-[11px]">
        ×
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="relative flex h-6 w-6 items-center justify-center">
        <span className="absolute h-6 w-6 rounded-full border border-plausible/40" />
        <span className="h-2.5 w-2.5 rounded-full bg-plausible animate-pulseDot" />
      </span>
    );
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-rule text-ash text-[11px]">
      ·
    </span>
  );
}

export default function PipelineRail({ stages }) {
  return (
    <ol className="relative">
      {stages.map((stage, i) => (
        <li key={stage.key} className="relative pb-8 last:pb-0">
          {i < stages.length - 1 && (
            <span
              className={`absolute left-3 top-6 h-full w-px ${
                stage.status === "done" ? "bg-verified/40" : "bg-rule"
              }`}
            />
          )}
          <div className="flex items-start gap-3">
            <StageIcon status={stage.status} />
            <div className="min-w-0 pt-0.5">
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-[11px] text-ash">{String(i + 1).padStart(2, "0")}</span>
                <span
                  className={`font-sans text-sm font-medium ${
                    stage.status === "pending" ? "text-ash" : "text-bone"
                  }`}
                >
                  {AGENT_NAMES[stage.key] || stage.label}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-ash truncate">
                {stage.detail || stage.label}
              </p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
