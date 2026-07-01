import { useMemo, useState } from "react";

/**
 * Trang tìm kiếm tài liệu ĐA PHƯƠNG THỨC (tài liệu · hình · sơ đồ · bảng).
 * Hiện thực hóa docs/upgrade/PROPOSAL-document-search-multimodal.md:
 *  - Kết quả kèm bảng đã QA + hình/sơ đồ, hiển thị cạnh crop bản gốc ("Xem bản gốc").
 *  - CHỈ ảnh/sơ đồ qua AL mới có nhãn "✔ AL xét duyệt"; ảnh qua app quét thì không nhãn.
 *  - Render React thuần, KHÔNG dùng dangerouslySetInnerHTML (chống XSS).
 *
 * Backend multimodal (Workflow-P + schema document_tables/figures) đang xây; trang
 * này chạy ở chế độ XEM TRƯỚC bằng dữ liệu mẫu và sẵn sàng nhận API thật sau.
 */

type ExtractionStatus = "CONSENSUS_PASS" | "RESCAN_PASS" | "AL_RESOLVED";

interface TableCell {
  row: number;
  col: number;
  isHeader?: boolean;
  value: string;
  status: ExtractionStatus;
  engineValues?: string[];
  reviewer?: string;
}

interface DocumentTable {
  tableId: string;
  page: number;
  rows: number;
  cols: number;
  cells: TableCell[];
  caption?: string;
}

interface DocumentFigure {
  figureId: string;
  elementClass: "picture" | "diagram" | "flowchart" | "formula" | "chart";
  page: number;
  caption?: string;
  labels?: string[];
  /** Chỉ set khi vùng/nhãn được AL xét duyệt → hiển thị nhãn "AL xét duyệt". */
  alReviewer?: string;
}

interface MultimodalResult {
  documentCode: string;
  versionLabel: string;
  title: string;
  page: number;
  section?: string;
  searchMode: "hybrid" | "fts_only" | "visual" | "no_source";
  text?: string;
  tables: DocumentTable[];
  figures: DocumentFigure[];
}

const ELEMENT_LABEL: Record<DocumentFigure["elementClass"], string> = {
  picture: "Hình ảnh",
  diagram: "Sơ đồ",
  flowchart: "Lưu đồ",
  formula: "Công thức",
  chart: "Biểu đồ",
};

/** Dữ liệu mẫu dựng theo benchmark R05-A08 (trang 7 tủ an toàn sinh học: bảng + sơ đồ). */
const SAMPLE_RESULTS: MultimodalResult[] = [
  {
    documentCode: "REF-BSC-A2",
    versionLabel: "v1.0",
    title: "Hướng dẫn lắp đặt & vận hành tủ an toàn sinh học cấp II loại A2",
    page: 7,
    section: "Thông số kỹ thuật / Sơ đồ luồng khí",
    searchMode: "hybrid",
    text:
      "Vận tốc gió mặt trước (inflow) và vận tốc gió thổi xuống (downflow) phải đạt " +
      "ngưỡng quy định để bảo đảm an toàn sinh học và bảo vệ mẫu.",
    tables: [
      {
        tableId: "TBL-REF-BSC-A2-p7-1",
        page: 7,
        rows: 4,
        cols: 4,
        caption: "Bảng thông số vận hành (14×4 — 2 đường line-aware khớp exact).",
        cells: [
          { row: 0, col: 0, isHeader: true, value: "Thông số", status: "CONSENSUS_PASS" },
          { row: 0, col: 1, isHeader: true, value: "Đơn vị", status: "CONSENSUS_PASS" },
          { row: 0, col: 2, isHeader: true, value: "Ngưỡng", status: "CONSENSUS_PASS" },
          { row: 0, col: 3, isHeader: true, value: "Ghi chú", status: "CONSENSUS_PASS" },

          { row: 1, col: 0, value: "Inflow velocity", status: "CONSENSUS_PASS" },
          { row: 1, col: 1, value: "m/s", status: "CONSENSUS_PASS" },
          {
            row: 1,
            col: 2,
            value: "0,53",
            status: "AL_RESOLVED",
            reviewer: "Hoàn",
            engineValues: ["0,53", "0.53", "0,5.3", "053"],
          },
          { row: 1, col: 3, value: "≥ 0,50", status: "CONSENSUS_PASS" },

          { row: 2, col: 0, value: "Downflow velocity", status: "CONSENSUS_PASS" },
          { row: 2, col: 1, value: "m/s", status: "CONSENSUS_PASS" },
          { row: 2, col: 2, value: "0,33", status: "RESCAN_PASS" },
          { row: 2, col: 3, value: "0,25 – 0,50", status: "CONSENSUS_PASS" },

          { row: 3, col: 0, value: "HEPA hiệu suất", status: "CONSENSUS_PASS" },
          { row: 3, col: 1, value: "%", status: "CONSENSUS_PASS" },
          {
            row: 3,
            col: 2,
            value: "99,999",
            status: "AL_RESOLVED",
            reviewer: "Hoàn",
            engineValues: ["99,999", "99.999", "99,99", "9,9999"],
          },
          { row: 3, col: 3, value: "@0,3µm (MPPS)", status: "CONSENSUS_PASS" },
        ],
      },
    ],
    figures: [
      {
        figureId: "FIG-REF-BSC-A2-p7-1",
        elementClass: "diagram",
        page: 7,
        caption: "Sơ đồ luồng khí tủ an toàn sinh học (có callout đánh số).",
        labels: ["1. Inflow", "2. Downflow", "3. HEPA cấp", "4. HEPA thải", "5. Vùng thao tác"],
        alReviewer: "Hoàn", // sơ đồ này qua AL → có nhãn
      },
      {
        figureId: "FIG-REF-BSC-A2-p7-2",
        elementClass: "picture",
        page: 7,
        caption: "Ảnh mặt trước tủ (trích tự động, đồng thuận đa engine).",
        labels: [],
        // không có alReviewer → KHÔNG gắn nhãn AL
      },
    ],
  },
];

function StatusDot({ status }: { status: ExtractionStatus }) {
  const map: Record<ExtractionStatus, { c: string; t: string }> = {
    CONSENSUS_PASS: { c: "bg-emerald-400", t: "Đồng thuận đa engine" },
    RESCAN_PASS: { c: "bg-sky-400", t: "Đạt sau khi quét lại/nâng chất lượng" },
    AL_RESOLVED: { c: "bg-amber-400", t: "Do AL xét duyệt" },
  };
  const it = map[status];
  return <span className={`inline-block h-2 w-2 rounded-full ${it.c}`} title={it.t} />;
}

function TableView({ table }: { table: DocumentTable }) {
  const [showSource, setShowSource] = useState(false);
  const grid = useMemo(() => {
    const g: (TableCell | undefined)[][] = Array.from({ length: table.rows }, () =>
      Array.from({ length: table.cols }, () => undefined),
    );
    for (const c of table.cells) if (g[c.row]) g[c.row][c.col] = c;
    return g;
  }, [table]);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-slate-500">{table.caption}</p>
        <button
          type="button"
          onClick={() => setShowSource((v) => !v)}
          className="shrink-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
        >
          {showSource ? "Ẩn bản gốc" : "Xem bản gốc"}
        </button>
      </div>
      <div className={showSource ? "grid grid-cols-1 gap-3 md:grid-cols-2" : ""}>
        {showSource ? (
          <div className="flex min-h-[140px] items-center justify-center rounded border border-dashed border-slate-300 bg-slate-50 p-3 text-center text-xs text-slate-400">
            [Crop trang gốc {table.page} — bảng]
            <br />
            (ảnh crop có SHA-256 + bbox từ pipeline)
          </div>
        ) : null}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <tbody>
              {grid.map((rowCells, r) => (
                <tr key={r}>
                  {rowCells.map((cell, c) => {
                    if (!cell)
                      return (
                        <td key={c} className="border border-slate-200 px-2 py-1 text-slate-300">
                          —
                        </td>
                      );
                    const Tag = cell.isHeader ? "th" : "td";
                    return (
                      <Tag
                        key={c}
                        title={
                          cell.status === "AL_RESOLVED"
                            ? `AL xét duyệt (${cell.reviewer}) — engine: ${(cell.engineValues || []).join(" | ")}`
                            : undefined
                        }
                        className={`border border-slate-200 px-2 py-1 text-left align-top ${
                          cell.isHeader ? "bg-slate-100 font-semibold text-slate-700" : "text-slate-700"
                        } ${cell.status === "AL_RESOLVED" ? "bg-amber-50" : ""}`}
                      >
                        <span className="mr-1 align-middle">
                          <StatusDot status={cell.status} />
                        </span>
                        {cell.value}
                        {cell.status === "AL_RESOLVED" ? (
                          <span className="ml-1 rounded bg-amber-100 px-1 text-[10px] font-medium text-amber-700">
                            ✔ AL: {cell.reviewer}
                          </span>
                        ) : null}
                      </Tag>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function FigureView({ figure }: { figure: DocumentFigure }) {
  const [showSource, setShowSource] = useState(false);
  const isAl = Boolean(figure.alReviewer);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-slate-500">
          {ELEMENT_LABEL[figure.elementClass]} · trang {figure.page}
        </p>
        <button
          type="button"
          onClick={() => setShowSource((v) => !v)}
          className="shrink-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
        >
          {showSource ? "Ẩn bản gốc" : "Xem bản gốc"}
        </button>
      </div>
      <div className={showSource ? "grid grid-cols-1 gap-3 md:grid-cols-2" : ""}>
        <div className="relative flex min-h-[140px] items-center justify-center rounded border border-dashed border-slate-300 bg-slate-50 p-3 text-center text-xs text-slate-400">
          [{ELEMENT_LABEL[figure.elementClass]} — thumbnail crop]
          {/* Nhãn AL CHỈ hiển thị khi hình/sơ đồ qua AL */}
          {isAl ? (
            <span className="absolute right-1 top-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 shadow-sm">
              ✔ AL xét duyệt — {figure.alReviewer}
            </span>
          ) : null}
        </div>
        {showSource ? (
          <div className="flex min-h-[140px] items-center justify-center rounded border border-dashed border-slate-300 bg-slate-50 p-3 text-center text-xs text-slate-400">
            [Crop trang gốc {figure.page}]
          </div>
        ) : null}
      </div>
      {figure.caption ? <p className="mt-2 text-xs text-slate-500">{figure.caption}</p> : null}
      {figure.labels && figure.labels.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {figure.labels.map((l) => (
            <span key={l} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
              {l}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ResultCard({ result }: { result: MultimodalResult }) {
  return (
    <article className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
      <header className="flex flex-wrap items-center gap-2">
        <span className="rounded bg-sky-100 px-2 py-0.5 text-xs font-semibold text-sky-700">
          {result.documentCode} · {result.versionLabel}
        </span>
        <span className="rounded bg-slate-200 px-2 py-0.5 text-[11px] text-slate-600">
          trang {result.page}
          {result.section ? ` · ${result.section}` : ""}
        </span>
        <span className="rounded bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
          mode: {result.searchMode}
        </span>
      </header>
      <h3 className="text-sm font-semibold text-slate-800">{result.title}</h3>
      {result.text ? <p className="text-sm text-slate-600">{result.text}</p> : null}

      {result.tables.length > 0 ? (
        <section className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Bảng</p>
          {result.tables.map((t) => (
            <TableView key={t.tableId} table={t} />
          ))}
        </section>
      ) : null}

      {result.figures.length > 0 ? (
        <section className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Hình / Sơ đồ</p>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {result.figures.map((f) => (
              <FigureView key={f.figureId} figure={f} />
            ))}
          </div>
        </section>
      ) : null}
    </article>
  );
}

export default function MultimodalSearchPage() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-800">🖼️ Tìm kiếm tài liệu đa phương thức</h2>
        <p className="mt-1 text-sm text-slate-500">
          Kết quả trả về gồm tài liệu, <strong>bảng</strong>, <strong>hình</strong> và{" "}
          <strong>sơ đồ</strong> trích từ trang gốc, xem cạnh bản gốc ("Xem bản gốc"). Chỉ
          ảnh/sơ đồ đã qua <strong>AL (người xét duyệt)</strong> mới mang nhãn “✔ AL xét duyệt”.
        </p>
        <form
          className="mt-3 flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(true);
          }}
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ví dụ: vận tốc gió tủ an toàn sinh học cấp II…"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
          >
            Tìm kiếm
          </button>
        </form>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
        ⚠️ <strong>Xem trước giao diện — dữ liệu mẫu.</strong> Backend đa phương thức (Workflow-P
        staging + schema <code>document_tables</code>/<code>document_figures</code>) đang được xây;
        khi có API thật, trang này sẽ hiển thị kết quả sống. Mọi output GMP vẫn là DRAFT tới khi
        người có thẩm quyền duyệt.
      </div>

      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <StatusDot status="CONSENSUS_PASS" /> Đồng thuận đa engine
        </span>
        <span className="flex items-center gap-1">
          <StatusDot status="RESCAN_PASS" /> Đạt sau quét lại
        </span>
        <span className="flex items-center gap-1">
          <StatusDot status="AL_RESOLVED" /> AL xét duyệt
        </span>
      </div>

      <div className="space-y-4">
        {SAMPLE_RESULTS.map((r) => (
          <ResultCard key={r.documentCode} result={r} />
        ))}
      </div>
      {submitted ? (
        <p className="text-xs text-slate-400">
          (Truy vấn “{query || "—"}” — hiện trả dữ liệu mẫu; API thật sẽ nối khi backend sẵn sàng.)
        </p>
      ) : null}
    </div>
  );
}
