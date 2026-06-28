import { useState } from "react";
import { sb } from "@/lib/supabase";
import { cn } from "@/lib/utils";

interface EvalRun {
  id: string;
  run_at: string;
  model_tag: string;
  n_questions: number | null;
  score_mean: number | null;
  score_min: number | null;
  passed: boolean | null;
  notes: string | null;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function MetricBar({ label, value, threshold }: { label: string; value: number | null; threshold?: number }) {
  const pct = value ?? 0;
  const isWarn = threshold !== undefined && pct < threshold;
  return (
    <div className="flex items-center gap-3">
      <span className="w-14 shrink-0 text-[11px] text-slate-600">{label}</span>
      <div className="flex-1 rounded-full bg-slate-100" style={{ height: "6px" }}>
        <div
          className={cn("h-full rounded-full transition-all", isWarn ? "bg-rose-500/70" : "bg-emerald-500/70")}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className={cn("w-12 shrink-0 text-right text-[11px] font-semibold", isWarn ? "text-rose-700" : "text-slate-700")}>
        {value !== null ? `${value}%` : "—"}
      </span>
    </div>
  );
}

export function EvalPanel() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [lastResult, setLastResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function loadRuns() {
    if (!sb) return;
    setLoading(true);
    setError("");
    try {
      const { data, error: err } = await sb
        .from("eval_runs")
        .select("id,run_at,model_tag,n_questions,score_mean,score_min,passed,notes")
        .order("run_at", { ascending: false })
        .limit(20);
      if (err) throw err;
      setRuns((data ?? []) as EvalRun[]);
      setLoaded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải lịch sử eval.");
    } finally {
      setLoading(false);
    }
  }

  async function runEval() {
    if (!sb) return;
    setRunning(true);
    setError("");
    setLastResult(null);
    try {
      const { data, error: err } = await sb.rpc("run_fts_eval_v1", {
        p_top_k: 5,
        p_model_tag: "fts-v1",
        p_notes: `Manual eval — ${new Date().toISOString()}`,
      });
      if (err) throw err;
      setLastResult(data as Record<string, unknown>);
      await loadRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi chạy eval.");
    } finally {
      setRunning(false);
    }
  }

  if (!loaded && !loading) {
    return (
      <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Eval Harness — FTS Retrieval
          </h3>
          <button
            type="button"
            onClick={() => void loadRuns()}
            className="rounded-xl border border-border px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-50"
          >
            Tải lịch sử
          </button>
        </div>
        <div className="p-5">
          <p className="text-sm text-muted-foreground">
            Chạy eval để kiểm tra chất lượng truy xuất tài liệu GMP (FTS Hit@5, MRR) trên 50 golden questions.
          </p>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => void runEval()}
              disabled={running}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {running ? "Đang chạy..." : "▶ Chạy Eval FTS"}
            </button>
            <button
              type="button"
              onClick={() => void loadRuns()}
              className="rounded-xl border border-border px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
            >
              Xem lịch sử
            </button>
          </div>
          {error ? (
            <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
      <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          Eval Harness — FTS Retrieval (50 golden questions)
        </h3>
        <button
          type="button"
          onClick={() => void runEval()}
          disabled={running}
          className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
        >
          {running ? "Đang chạy..." : "▶ Chạy Eval"}
        </button>
      </div>

      <div className="p-5 space-y-4">
        {error ? (
          <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
        ) : null}

        {/* Latest result inline */}
        {lastResult ? (
          <div className="rounded-2xl border border-border bg-slate-50/70 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-bold",
                lastResult.passed
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-rose-100 text-rose-800"
              )}>
                {lastResult.passed ? "✅ PASS" : "❌ FAIL"}
              </span>
              <span className="text-xs text-muted-foreground">
                {lastResult.n_with_sources as number}/{lastResult.n_total as number} câu có nguồn
              </span>
            </div>
            <MetricBar label="Hit@1" value={lastResult.hit_at_1_pct as number} threshold={60} />
            <MetricBar label="Hit@3" value={lastResult.hit_at_3_pct as number} threshold={70} />
            <MetricBar label="Hit@5" value={lastResult.hit_at_5_pct as number} threshold={80} />
            <div className="flex items-center gap-3">
              <span className="w-14 shrink-0 text-[11px] text-slate-600">MRR</span>
              <span className="text-[11px] font-semibold text-slate-700">{String(lastResult.mrr ?? "—")}</span>
              <span className="text-[10px] text-muted-foreground">(Mean Reciprocal Rank — cao hơn = tốt hơn)</span>
            </div>
          </div>
        ) : null}

        {/* History table */}
        {loading ? (
          <p className="text-center text-sm text-muted-foreground">Đang tải...</p>
        ) : runs.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground">
            Chưa có lần chạy eval nào. Nhấn "Chạy Eval" hoặc kích hoạt GitHub Actions workflow "GMP Eval Harness".
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
                <tr>
                  <th className="border-b border-border/60 px-4 py-2.5">Thời gian</th>
                  <th className="border-b border-border/60 px-4 py-2.5">Model Tag</th>
                  <th className="border-b border-border/60 px-4 py-2.5">Câu hỏi</th>
                  <th className="border-b border-border/60 px-4 py-2.5">Hit@5%</th>
                  <th className="border-b border-border/60 px-4 py-2.5">Hit@1%</th>
                  <th className="border-b border-border/60 px-4 py-2.5">Kết quả</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-t border-border/60 hover:bg-slate-50/60">
                    <td className="px-4 py-2.5 text-[12px] text-slate-700 whitespace-nowrap">
                      {formatDate(run.run_at)}
                    </td>
                    <td className="px-4 py-2.5">
                      <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-700">
                        {run.model_tag}
                      </code>
                    </td>
                    <td className="px-4 py-2.5 text-[12px] text-slate-700">
                      {run.n_questions ?? "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={cn(
                        "text-[12px] font-semibold",
                        (run.score_mean ?? 0) >= 80 ? "text-emerald-700" : "text-rose-700"
                      )}>
                        {run.score_mean !== null ? `${run.score_mean}%` : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-[12px] text-slate-700">
                      {run.score_min !== null ? `${run.score_min}%` : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={cn(
                        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold",
                        run.passed === true
                          ? "bg-emerald-100 text-emerald-800"
                          : run.passed === false
                          ? "bg-rose-100 text-rose-800"
                          : "bg-slate-100 text-slate-600"
                      )}>
                        {run.passed === true ? "✅ PASS" : run.passed === false ? "❌ FAIL" : "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="text-[11px] text-muted-foreground">
          Ngưỡng PASS: Hit@5 ≥ 80%. Tự động hóa qua GitHub Actions workflow "GMP Eval Harness" (Settings → Actions → Run workflow).
          Cần thêm Secret <code className="rounded bg-slate-100 px-1 py-0.5">SUPABASE_SERVICE_ROLE_KEY</code> vào repo.
        </p>
      </div>
    </section>
  );
}
