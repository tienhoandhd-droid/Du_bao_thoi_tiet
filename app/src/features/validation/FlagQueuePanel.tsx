import { useState } from "react";
import { sb } from "@/lib/supabase";
import { cn } from "@/lib/utils";

// Hàng đợi cờ AL provisional (migration 036 scan_flag_queue / view scan_flags_pending).
// AL duyệt tạm để không nghẽn; người có thẩm quyền (admin/qa_manager) duyệt bỏ cờ
// hoặc từ chối qua RPC clear_scan_flag(). Xem docs/upgrade/crave-scan-gate.md.

interface Mismatch {
  provider?: string;
  field?: string;
  note?: string;
  disputed_numbers?: string[];
}

interface PendingFlag {
  id: string;
  document_code: string;
  source_sha256: string | null;
  page_number: number | null;
  gate: string;
  al_verdict: string;
  al_confidence: number | null;
  al_mismatch: Mismatch[] | null;
  created_at: string;
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

function VerdictBadge({ verdict }: { verdict: string }) {
  const flagged = verdict === "mismatch_flagged";
  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-[11px] font-semibold",
        flagged ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800",
      )}
    >
      {flagged ? "⚠ Lệch dữ liệu" : "Đề xuất đạt"}
    </span>
  );
}

export function FlagQueuePanel() {
  const [flags, setFlags] = useState<PendingFlag[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  async function loadFlags() {
    if (!sb) {
      setError("Chưa cấu hình Supabase (thiếu URL/anon key).");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { data, error: err } = await sb
        .from("scan_flags_pending")
        .select("id,document_code,source_sha256,page_number,gate,al_verdict,al_confidence,al_mismatch,created_at")
        .order("created_at", { ascending: false })
        .limit(100);
      if (err) throw err;
      setFlags((data ?? []) as PendingFlag[]);
      setLoaded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải hàng đợi cờ.");
    } finally {
      setLoading(false);
    }
  }

  async function decide(flagId: string, decision: "HUMAN_APPROVED" | "HUMAN_REJECTED") {
    if (!sb) return;
    setBusyId(flagId);
    setError("");
    try {
      const { error: err } = await sb.rpc("clear_scan_flag", {
        p_flag_id: flagId,
        p_decision: decision,
        p_note: notes[flagId] ?? null,
      });
      if (err) throw err;
      // Bỏ cờ khỏi danh sách pending ngay trên UI.
      setFlags((prev) => prev.filter((f) => f.id !== flagId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi duyệt cờ (cần quyền admin/qa_manager).");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Hàng đợi cờ AL — chờ người duyệt</h2>
          <p className="text-[12px] text-slate-500">
            AL duyệt tạm để không nghẽn; mỗi cờ phải được người có thẩm quyền duyệt (bỏ cờ) hoặc từ chối.
          </p>
        </div>
        <button
          type="button"
          onClick={loadFlags}
          disabled={loading}
          className="rounded-md bg-slate-800 px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Đang tải…" : "Tải danh sách"}
        </button>
      </div>

      {error ? <p className="rounded-md bg-rose-50 px-3 py-2 text-[12px] text-rose-700">{error}</p> : null}

      {loaded && flags.length === 0 && !error ? (
        <p className="rounded-md bg-emerald-50 px-3 py-2 text-[12px] text-emerald-700">
          Không có cờ nào đang chờ duyệt.
        </p>
      ) : null}

      <ul className="space-y-3">
        {flags.map((f) => (
          <li key={f.id} className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[12px] font-semibold text-slate-800">{f.document_code}</span>
              {f.page_number != null ? (
                <span className="text-[11px] text-slate-500">trang {f.page_number}</span>
              ) : null}
              <VerdictBadge verdict={f.al_verdict} />
              <span className="text-[11px] text-slate-500">
                tin cậy: {f.al_confidence != null ? f.al_confidence : "—"}
              </span>
              <span className="ml-auto text-[11px] text-slate-400">{formatDate(f.created_at)}</span>
            </div>

            {Array.isArray(f.al_mismatch) && f.al_mismatch.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {f.al_mismatch.map((m, i) => (
                  <li key={i} className="rounded bg-amber-50 px-2 py-1 text-[11px] text-amber-900">
                    {m.provider ? <b>[{m.provider}] </b> : null}
                    {m.field ? <b>{m.field}: </b> : null}
                    {m.note}
                    {m.disputed_numbers && m.disputed_numbers.length ? (
                      <span className="text-amber-700"> — số lệch: {m.disputed_numbers.join(", ")}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-[11px] text-slate-500">Không có trường lệch cụ thể (AL duyệt tạm).</p>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <input
                type="text"
                placeholder="Ghi chú duyệt (tuỳ chọn)"
                value={notes[f.id] ?? ""}
                onChange={(e) => setNotes((prev) => ({ ...prev, [f.id]: e.target.value }))}
                className="min-w-[180px] flex-1 rounded-md border border-slate-200 px-2 py-1 text-[12px]"
              />
              <button
                type="button"
                onClick={() => decide(f.id, "HUMAN_APPROVED")}
                disabled={busyId === f.id}
                className="rounded-md bg-emerald-600 px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50"
              >
                Duyệt (bỏ cờ)
              </button>
              <button
                type="button"
                onClick={() => decide(f.id, "HUMAN_REJECTED")}
                disabled={busyId === f.id}
                className="rounded-md bg-rose-600 px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50"
              >
                Từ chối
              </button>
            </div>
          </li>
        ))}
      </ul>

      <p className="text-[11px] text-slate-400">
        Chỉ tài khoản có vai trò admin/qa_manager mới duyệt được (RPC clear_scan_flag SECURITY DEFINER).
      </p>
    </section>
  );
}
