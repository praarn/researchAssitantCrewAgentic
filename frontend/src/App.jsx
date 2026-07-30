import { useCallback, useEffect, useRef, useState } from "react";
import QueryForm from "./components/QueryForm";
import PipelineRail from "./components/PipelineRail";
import ReportView from "./components/ReportView";
import { startResearch, getJob } from "./api";

const POLL_MS = 1400;

export default function App() {
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  async function handleSubmit(payload) {
    setError("");
    setJob(null);
    try {
      const created = await startResearch(payload);
      setJob(created);
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const updated = await getJob(created.id);
          setJob(updated);
          if (updated.status === "complete" || updated.status === "failed") {
            stopPolling();
          }
        } catch (e) {
          stopPolling();
          setError(e.message);
        }
      }, POLL_MS);
    } catch (e) {
      setError(e.message || "Could not reach the research backend.");
    }
  }

  function handleReset() {
    stopPolling();
    setJob(null);
    setError("");
  }

  const isRunning = job && job.status !== "complete" && job.status !== "failed";
  const isDone = job && job.status === "complete" && job.report;
  const isFailed = job && job.status === "failed";

  return (
    <div className="min-h-full flex flex-col">
      <div className="aurora" aria-hidden />
      <div className="grain" aria-hidden />
      <div className="vignette" aria-hidden />

      <header className="relative">
        <div className="mx-auto max-w-5xl px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md border border-plausible/50 bg-gradient-to-br from-mystic/40 via-plausible/25 to-bloom/30 font-display text-bone text-sm animate-glowRing">
              R
            </span>
            <span className="font-display text-lg text-bone tracking-tight">Research Assistant Crew</span>
          </div>
          <span className="font-mono text-[11px] text-ash uppercase tracking-wider hidden sm:block">
            Planner · Search · Summarizer · Fact-Checker · Writer
          </span>
        </div>
        <div className="h-px w-full bg-gradient-to-r from-transparent via-rule to-transparent" />
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-12">
        {!job && <QueryForm onSubmit={handleSubmit} errorMessage={error} />}

        {job && !isDone && (
          <div className="grid gap-10 lg:grid-cols-[280px_1fr]">
            <aside className="lg:sticky lg:top-12 lg:self-start">
              <div className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-ash">
                Case #{job.id}
              </div>
              <PipelineRail stages={job.stages} />
            </aside>
            <div className="min-w-0">
              <p className="font-display text-2xl text-bone leading-snug mb-4">
                “{job.request.query}”
              </p>
              {isRunning && (
                <p className="text-sm text-ash">
                  Working through the case. This usually takes half a minute to a couple of minutes,
                  depending on depth.
                </p>
              )}
              {isFailed && (
                <div className="mt-4 rounded-md border border-contradicted/40 bg-contradicted/10 px-4 py-3 text-sm text-contradicted">
                  {job.error || "Something went wrong while researching this."}
                  <button
                    onClick={handleReset}
                    className="ml-3 underline underline-offset-2 hover:opacity-80"
                  >
                    Try again
                  </button>
                </div>
              )}
              {job.plan && (
                <div className="mt-8 space-y-3">
                  {job.plan.sub_questions.map((sq, i) => (
                    <div key={sq.id} className="flex gap-3 text-sm">
                      <span className="font-mono text-ash pt-0.5">{String(i + 1).padStart(2, "0")}</span>
                      <div>
                        <div className="text-bone">{sq.text}</div>
                        {sq.rationale && <div className="text-ash text-xs mt-0.5">{sq.rationale}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {isDone && <ReportView report={job.report} onNewQuery={handleReset} />}
      </main>

      <footer className="border-t border-rule/60 py-5">
        <div className="mx-auto max-w-5xl px-6 font-mono text-[11px] text-ash">
          Powered by Groq · Search via DuckDuckGo · Every claim is labeled, never assumed.
        </div>
      </footer>
    </div>
  );
}