import { cn } from "@/lib/utils";

export interface ObservabilityRow {
  action_type: string;
  timestamp: string;
}

const ACTION_LABELS: Record<string, string> = {
  ai_query: "AI Search / Q&A",
  ai_draft_protocol: "Soạn đề cương",
  ai_check_protocol: "Kiểm tra đề cương",
  ai_calculate_report: "Tính toán báo cáo",
  document_upload: "Upload tài liệu",
  document_review: "Review tài liệu",
  document_approve: "Duyệt tài liệu",
  document_index: "Index tài liệu",
  user_login: "Đăng nhập",
  config_change: "Thay đổi cấu hình",
  security_event: "Sự kiện bảo mật",
};

const ACTION_COLOR: Record<string, string> = {
  ai_query: "bg-primary/70",
  ai_draft_protocol: "bg-emerald-500/70",
  ai_check_protocol: "bg-emerald-500/70",
  ai_calculate_report: "bg-emerald-500/70",
  document_upload: "bg-amber-500/70",
  document_review: "bg-amber-500/70",
  document_approve: "bg-amber-500/70",
  document_index: "bg-amber-500/70",
  user_login: "bg-slate-400/70",
  config_change: "bg-rose-500/70",
  security_event: "bg-rose-600/70",
};

function getDays(n: number): string[] {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (n - 1 - i));
    return d.toISOString().split("T")[0];
  });
}

function formatDay(iso: string): string {
  const parts = iso.split("-");
  return `${parts[1]}/${parts[2]}`;
}

export function ObservabilityPanel({ rows }: { rows: ObservabilityRow[] }) {
  const total = rows.length;

  // Count by action_type
  const byType: Record<string, number> = {};
  for (const row of rows) {
    byType[row.action_type] = (byType[row.action_type] || 0) + 1;
  }

  // Daily count for last 7 days
  const days = getDays(7);
  const byDay: Record<string, number> = {};
  for (const row of rows) {
    const day = row.timestamp.split("T")[0];
    byDay[day] = (byDay[day] || 0) + 1;
  }
  const dayCounts = days.map((d) => byDay[d] ?? 0);
  const maxDay = Math.max(...dayCounts, 1);

  const sortedTypes = Object.entries(byType)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 7);

  if (total === 0) {
    return (
      <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
        <div className="border-b border-border/60 px-5 py-4">
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Observability — 7 ngày gần nhất
          </h3>
        </div>
        <div className="p-5 text-center text-sm text-muted-foreground">
          Chưa có dữ liệu hoạt động trong 7 ngày qua.
        </div>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
      <div className="border-b border-border/60 px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Observability — 7 ngày gần nhất
          </h3>
          <span className="text-xs font-semibold text-slate-700">
            {total.toLocaleString("vi-VN")} sự kiện
          </span>
        </div>
      </div>

      <div className="grid gap-5 p-5 md:grid-cols-2">
        {/* Daily trend bar chart */}
        <div>
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Xu hướng theo ngày
          </p>
          <div className="flex h-20 items-end gap-1">
            {days.map((day, i) => {
              const count = dayCounts[i];
              const heightPct = Math.max(4, Math.round((count / maxDay) * 100));
              return (
                <div key={day} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-sm bg-primary/60 transition-all"
                    style={{ height: `${heightPct}%` }}
                    title={`${formatDay(day)}: ${count} sự kiện`}
                  />
                  <span className="text-[9px] text-muted-foreground">
                    {formatDay(day)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* By action type */}
        <div>
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Theo loại hành động
          </p>
          <div className="space-y-2">
            {sortedTypes.map(([type, count]) => {
              const pct = Math.round((count / total) * 100);
              const colorClass = ACTION_COLOR[type] ?? "bg-slate-400/60";
              return (
                <div key={type} className="flex items-center gap-2">
                  <span className="w-[120px] shrink-0 truncate text-[11px] text-slate-700">
                    {ACTION_LABELS[type] ?? type}
                  </span>
                  <div className="flex-1 rounded-full bg-slate-100" style={{ height: "6px" }}>
                    <div
                      className={cn("h-full rounded-full", colorClass)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-8 shrink-0 text-right text-[11px] font-semibold text-slate-700">
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
