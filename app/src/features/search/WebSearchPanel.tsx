import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, fetchWebSearch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { WebSearchResult, WebSearchMode } from "@/types/api";

const SEARCH_MODES: { value: WebSearchMode; label: string; description: string }[] = [
  { value: "general", label: "Tổng hợp", description: "Tất cả nguồn, ưu tiên độ tin cậy" },
  { value: "guideline", label: "Guideline GMP", description: "WHO, ICH, PIC/S, FDA, Bộ Y tế" },
  { value: "literature", label: "Văn học KH", description: "PubMed, NCBI, Europe PMC" },
  { value: "forum", label: "Diễn đàn", description: "Cộng đồng dược, forum chuyên ngành" },
];

const TRUST_LEVEL_INFO: Record<number, { color: string; border: string }> = {
  4: { color: "text-sky-700 bg-sky-50", border: "border-sky-200" },
  3: { color: "text-emerald-700 bg-emerald-50", border: "border-emerald-200" },
  2: { color: "text-amber-700 bg-amber-50", border: "border-amber-200" },
  1: { color: "text-slate-600 bg-slate-50", border: "border-slate-200" },
};

export function WebSearchPanel({
  token,
  initQuery,
  onUnauthorized,
}: {
  token: string;
  initQuery?: string;
  onUnauthorized: () => void;
}) {
  const [query, setQuery] = useState(initQuery ?? "");
  const [mode, setMode] = useState<WebSearchMode>("guideline");
  const [results, setResults] = useState<WebSearchResult[]>([]);
  const [searchMeta, setSearchMeta] = useState<{ query: string; total: number; mode: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const lastInitRef = useRef("");

  async function doSearch(q: string, searchMode: WebSearchMode) {
    setLoading(true);
    setError("");
    setResults([]);
    setSearchMeta(null);
    try {
      const data = await fetchWebSearch({ query: q, search_mode: searchMode, max_results: 10 }, token);
      setResults(data.results ?? []);
      setSearchMeta({ query: data.query ?? q, total: data.total ?? 0, mode: data.search_mode ?? searchMode });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { onUnauthorized(); return; }
      setError(err instanceof Error ? err.message : "Đã xảy ra lỗi không xác định.");
    } finally {
      setLoading(false);
    }
  }

  // Auto-fill + search when parent passes initQuery (CRAG redirect from AI Search)
  useEffect(() => {
    const q = initQuery?.trim() ?? "";
    if (!q || q === lastInitRef.current) return;
    lastInitRef.current = q;
    setQuery(q);
    void doSearch(q, "guideline");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initQuery]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) { setError("Vui lòng nhập từ khóa tìm kiếm."); return; }
    if (trimmed.length > 2000) { setError("Từ khóa quá dài (tối đa 2000 ký tự)."); return; }
    await doSearch(trimmed, mode);
  }

  return (
    <div className="space-y-5">
      <Panel title="Tìm kiếm tài liệu web — Đa nguồn có phân tầng tin cậy">
        <form className="space-y-4" onSubmit={(e) => void handleSubmit(e)}>
          <div className="flex flex-col gap-3 lg:flex-row">
            <input
              className="h-11 min-w-0 flex-1 rounded-2xl border border-input bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20"
              maxLength={2000}
              placeholder="VD: GMP requirements for HVAC qualification, tiêu chuẩn phòng sạch WHO..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-11 shrink-0 items-center justify-center rounded-2xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Đang tìm..." : "🔎 Tìm kiếm"}
            </button>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {SEARCH_MODES.map((m) => (
              <button
                key={m.value}
                type="button"
                onClick={() => setMode(m.value)}
                className={cn(
                  "rounded-2xl border px-3 py-2.5 text-left text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30",
                  mode === m.value
                    ? "border-primary/30 bg-primary/8 text-primary"
                    : "border-border bg-white text-slate-700 hover:bg-slate-50",
                )}
              >
                <div className="font-semibold">{m.label}</div>
                <div className="mt-0.5 text-[11px] text-muted-foreground">{m.description}</div>
              </button>
            ))}
          </div>
        </form>

        <div className="mt-4 rounded-2xl border border-border/60 bg-slate-50/70 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Phân tầng độ tin cậy
          </p>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 font-semibold text-sky-700">
              🔵 Cơ quan quản lý — trust 4 (WHO, ICH, PIC/S, FDA, Bộ Y tế)
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-semibold text-emerald-700">
              🟢 Tổ chức uy tín — trust 3 (ISPE, PDA, PubMed)
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 font-semibold text-amber-700">
              🟡 Chuyên ngành — trust 2
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-600">
              ⚪ Nguồn khác — trust 1
            </span>
          </div>
        </div>
      </Panel>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-8 text-center text-sm text-muted-foreground">
          Đang tìm kiếm và phân tầng nguồn...
        </div>
      ) : null}

      {searchMeta && !loading ? (
        <Panel title={`Kết quả — "${searchMeta.query}" · ${searchMeta.total} nguồn`}>
          {results.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
              Không tìm thấy kết quả. Thử từ khóa khác hoặc chế độ tìm kiếm khác.
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result) => (
                <ResultCard key={result.url} result={result} />
              ))}
            </div>
          )}
        </Panel>
      ) : null}

      {!loading && !searchMeta ? (
        <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-8 text-center text-sm text-muted-foreground">
          Nhập từ khóa và chọn chế độ tìm kiếm để bắt đầu. Kết quả được phân loại theo độ tin cậy nguồn tự động.
        </div>
      ) : null}

      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        ⚕ Tìm kiếm từ nguồn web công khai. Kết quả mang tính tham khảo — cần đối chiếu với SOP nội bộ và nguồn chính thức trước khi áp dụng vào hồ sơ GMP.
      </div>
    </div>
  );
}

function ResultCard({ result }: { result: WebSearchResult }) {
  const [expanded, setExpanded] = useState(false);
  const trust = TRUST_LEVEL_INFO[result.trust_level] ?? TRUST_LEVEL_INFO[1];
  const isLong = result.content.length > 280;
  const displayContent = expanded ? result.content : result.content.slice(0, 280);

  return (
    <article className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
      <div className="flex items-start gap-3 px-5 py-4">
        <span className="mt-0.5 text-sm font-semibold text-muted-foreground">
          #{result.rank}
        </span>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
                trust.color,
                trust.border,
              )}
            >
              {result.trust_badge}
            </span>
            {result.published_date ? (
              <span className="text-[11px] text-muted-foreground">{result.published_date}</span>
            ) : null}
            <span className="text-[11px] font-mono text-muted-foreground">{result.source_domain}</span>
            <span className="ml-auto text-[11px] text-muted-foreground">
              Điểm: {result.relevance_score.toFixed(2)}
            </span>
          </div>

          <a
            href={result.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block font-semibold leading-5 text-slate-900 hover:text-primary hover:underline"
          >
            {result.title || result.url}
          </a>

          <p className="text-sm leading-6 text-slate-600">
            {displayContent}
            {isLong && !expanded ? "..." : null}
          </p>

          {isLong ? (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-xs text-primary hover:underline"
            >
              {expanded ? "Thu gọn" : "Xem thêm"}
            </button>
          ) : null}

          <a
            href={result.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block break-all font-mono text-[11px] text-muted-foreground hover:underline"
          >
            {result.url}
          </a>
        </div>
      </div>
    </article>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
      <div className="border-b border-border/60 px-5 py-4">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          {title}
        </h3>
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}
