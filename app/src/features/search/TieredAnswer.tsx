/**
 * Câu trả lời PHÂN TẦNG (progressive disclosure) cho RAG:
 *   Tầng 1 — Tóm tắt (luôn hiện)
 *   Tầng 2 — Chi tiết đầy đủ (mở khi cần)
 * Dùng <details> gốc (không cần state), React thuần (không dangerouslySetInnerHTML).
 * Nếu backend sau này trả `summary` riêng thì truyền vào; nếu không, tự rút gọn từ answer.
 */

function deriveSummary(text: string, maxChars = 260): string {
  const clean = text.trim().replace(/\s+/g, " ");
  if (clean.length <= maxChars) return clean;
  // Cắt theo ranh giới câu (. ! ? …) gần maxChars nhất.
  const slice = clean.slice(0, maxChars);
  const lastStop = Math.max(
    slice.lastIndexOf(". "),
    slice.lastIndexOf("! "),
    slice.lastIndexOf("? "),
    slice.lastIndexOf("; "),
  );
  if (lastStop > 80) return clean.slice(0, lastStop + 1);
  const lastSpace = slice.lastIndexOf(" ");
  return clean.slice(0, lastSpace > 80 ? lastSpace : maxChars) + "…";
}

export function TieredAnswer({ text, summary }: { text: string; summary?: string }) {
  const full = (text || "").trim();
  const tomTat = (summary || "").trim() || deriveSummary(full);
  const hasMore = full.length > tomTat.length + 8;

  return (
    <div className="rounded-2xl border border-border bg-white p-5 shadow-sm">
      {/* Tầng 1 — Tóm tắt */}
      <div className="mb-1 flex items-center gap-2">
        <span className="rounded bg-sky-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-sky-700">
          Tóm tắt
        </span>
      </div>
      <p className="whitespace-pre-wrap leading-7 text-slate-800">{tomTat || "Không có nội dung trả lời."}</p>

      {/* Tầng 2 — Chi tiết đầy đủ */}
      {hasMore ? (
        <details className="group mt-3 border-t border-border/60 pt-3">
          <summary className="cursor-pointer list-none text-sm font-medium text-sky-700 hover:underline">
            <span className="group-open:hidden">▸ Xem chi tiết đầy đủ</span>
            <span className="hidden group-open:inline">▾ Thu gọn</span>
          </summary>
          <p className="mt-2 whitespace-pre-wrap leading-7 text-slate-700">{full}</p>
        </details>
      ) : null}
    </div>
  );
}

export default TieredAnswer;
