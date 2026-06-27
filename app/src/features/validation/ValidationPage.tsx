import { type FormEvent, type ReactNode, useState } from "react";
import { ApiError, fetchCalculateReport, fetchCheckProtocol, fetchDraftProtocol } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  CalculateReportResponse,
  CheckProtocolResponse,
  DraftProtocolResponse,
  ProtocolFinding,
} from "@/types/api";

type Tab = "draft" | "check" | "calculate";

const TAB_LABELS: Record<Tab, string> = {
  draft: "Viết đề cương",
  check: "Kiểm tra đề cương",
  calculate: "Tính toán",
};

const PROTOCOL_TYPES = [
  { value: "iq", label: "IQ — Installation Qualification" },
  { value: "oq", label: "OQ — Operational Qualification" },
  { value: "pq", label: "PQ — Performance Qualification" },
  { value: "dq", label: "DQ — Design Qualification" },
  { value: "csv", label: "CSV — Computer System Validation" },
  { value: "cleaning_validation", label: "Cleaning Validation" },
];

const LANG_MODES = [
  { value: "vi", label: "Tiếng Việt" },
  { value: "en", label: "English" },
  { value: "vi-en", label: "Song ngữ (VI + EN)" },
];

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Đã xảy ra lỗi không xác định";
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

export function ValidationPage({
  token,
  onUnauthorized,
}: {
  token: string;
  onUnauthorized: () => void;
}) {
  const [tab, setTab] = useState<Tab>("draft");

  return (
    <div className="space-y-5">
      <div className="flex gap-2 overflow-x-auto pb-1">
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition-colors",
              tab === t
                ? "border-primary/20 bg-primary/10 text-primary"
                : "border-border bg-white text-slate-700 hover:bg-slate-50",
            )}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {tab === "draft" && (
        <DraftTab token={token} onUnauthorized={onUnauthorized} />
      )}
      {tab === "check" && (
        <CheckTab token={token} onUnauthorized={onUnauthorized} />
      )}
      {tab === "calculate" && (
        <CalculateTab token={token} onUnauthorized={onUnauthorized} />
      )}
    </div>
  );
}

function DraftTab({
  token,
  onUnauthorized,
}: {
  token: string;
  onUnauthorized: () => void;
}) {
  const [protocolType, setProtocolType] = useState("iq");
  const [equipmentCode, setEquipmentCode] = useState("");
  const [equipmentName, setEquipmentName] = useState("");
  const [languageMode, setLanguageMode] = useState("vi");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [location, setLocation] = useState("");
  const [intendedUse, setIntendedUse] = useState("");
  const [specialReq, setSpecialReq] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DraftProtocolResponse | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!equipmentCode.trim()) {
      setError("Vui lòng nhập mã thiết bị.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await fetchDraftProtocol(
        {
          protocol_type: protocolType,
          equipment_code: equipmentCode.trim(),
          equipment_name: equipmentName.trim() || undefined,
          language_mode: languageMode,
          manufacturer: manufacturer.trim() || undefined,
          model: model.trim() || undefined,
          location: location.trim() || undefined,
          intended_use: intendedUse.trim() || undefined,
          special_requirements: specialReq.trim() || undefined,
        },
        token,
      );
      setResult(data);
    } catch (err) {
      if (isUnauthorized(err)) { onUnauthorized(); return; }
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Panel title="Viết đề cương thẩm định (AI Draft)">
        <form className="space-y-4" onSubmit={(e) => void handleSubmit(e)}>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Loại đề cương *">
              <Select value={protocolType} onChange={(e) => setProtocolType(e.target.value)}>
                {PROTOCOL_TYPES.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Ngôn ngữ đầu ra">
              <Select value={languageMode} onChange={(e) => setLanguageMode(e.target.value)}>
                {LANG_MODES.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </Select>
            </FormField>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Mã thiết bị *">
              <Input
                placeholder="VD: HPLC-001"
                value={equipmentCode}
                onChange={(e) => setEquipmentCode(e.target.value)}
                maxLength={50}
                required
              />
            </FormField>
            <FormField label="Tên thiết bị">
              <Input
                placeholder="VD: Máy sắc ký lỏng hiệu năng cao"
                value={equipmentName}
                onChange={(e) => setEquipmentName(e.target.value)}
              />
            </FormField>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <FormField label="Nhà sản xuất">
              <Input placeholder="VD: Agilent" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} />
            </FormField>
            <FormField label="Model">
              <Input placeholder="VD: 1260 Infinity II" value={model} onChange={(e) => setModel(e.target.value)} />
            </FormField>
            <FormField label="Vị trí lắp đặt">
              <Input placeholder="VD: Phòng KCS-01" value={location} onChange={(e) => setLocation(e.target.value)} />
            </FormField>
          </div>
          <FormField label="Mục đích sử dụng">
            <Input placeholder="VD: Phân tích định lượng nguyên liệu dược" value={intendedUse} onChange={(e) => setIntendedUse(e.target.value)} />
          </FormField>
          <FormField label="Yêu cầu đặc biệt">
            <textarea
              className="h-20 w-full resize-none rounded-2xl border border-input bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20"
              placeholder="Các yêu cầu đặc biệt nếu có..."
              value={specialReq}
              onChange={(e) => setSpecialReq(e.target.value)}
            />
          </FormField>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Button type="submit" disabled={loading}>
            {loading ? "Đang tạo đề cương..." : "Tạo đề cương (AI)"}
          </Button>
        </form>
      </Panel>

      {loading ? <StateBlock>AI đang soạn đề cương, vui lòng đợi...</StateBlock> : null}

      {result ? (
        <Panel title={`Đề cương ${result.protocol_type?.toUpperCase() ?? ""} — ${result.equipment_code ?? ""}`}>
          <div className="space-y-4">
            <pre className="max-h-[500px] overflow-y-auto whitespace-pre-wrap rounded-2xl border border-border bg-slate-50 p-5 text-sm leading-7 text-slate-800">
              {result.content ?? "Không có nội dung."}
            </pre>
            <Alert tone="warning">
              ⚕ {result.disclaimer ?? "Nội dung do AI tạo. Cần người có chuyên môn GMP xem xét và chỉnh sửa trước khi sử dụng cho hồ sơ chính thức."}
            </Alert>
          </div>
        </Panel>
      ) : null}
    </>
  );
}

function CheckTab({
  token,
  onUnauthorized,
}: {
  token: string;
  onUnauthorized: () => void;
}) {
  const [documentText, setDocumentText] = useState("");
  const [protocolType, setProtocolType] = useState("iq");
  const [equipmentCode, setEquipmentCode] = useState("");
  const [documentLanguage, setDocumentLanguage] = useState("vi");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CheckProtocolResponse | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!documentText.trim()) {
      setError("Vui lòng dán nội dung đề cương cần kiểm tra.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await fetchCheckProtocol(
        {
          document_text: documentText.trim(),
          protocol_type: protocolType,
          equipment_code: equipmentCode.trim() || undefined,
          document_language: documentLanguage,
        },
        token,
      );
      setResult(data);
    } catch (err) {
      if (isUnauthorized(err)) { onUnauthorized(); return; }
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const statusClass =
    result?.overall_status === "PASS"
      ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/20"
      : result?.overall_status === "FAIL"
        ? "bg-rose-500/10 text-rose-700 border-rose-500/20"
        : "bg-amber-500/10 text-amber-700 border-amber-500/20";

  return (
    <>
      <Panel title="Kiểm tra đề cương (AI Check)">
        <form className="space-y-4" onSubmit={(e) => void handleSubmit(e)}>
          <div className="grid gap-3 md:grid-cols-3">
            <FormField label="Loại đề cương">
              <Select value={protocolType} onChange={(e) => setProtocolType(e.target.value)}>
                {PROTOCOL_TYPES.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Mã thiết bị">
              <Input placeholder="VD: HPLC-001" value={equipmentCode} onChange={(e) => setEquipmentCode(e.target.value)} maxLength={50} />
            </FormField>
            <FormField label="Ngôn ngữ tài liệu">
              <Select value={documentLanguage} onChange={(e) => setDocumentLanguage(e.target.value)}>
                <option value="vi">Tiếng Việt</option>
                <option value="en">English</option>
                <option value="vi-en">Song ngữ</option>
              </Select>
            </FormField>
          </div>
          <FormField label="Nội dung đề cương cần kiểm tra *">
            <textarea
              className="h-48 w-full resize-y rounded-2xl border border-input bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20"
              placeholder="Dán toàn bộ nội dung đề cương vào đây..."
              value={documentText}
              onChange={(e) => setDocumentText(e.target.value)}
              required
            />
          </FormField>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Button type="submit" disabled={loading}>
            {loading ? "Đang kiểm tra..." : "Kiểm tra đề cương (AI)"}
          </Button>
        </form>
      </Panel>

      {loading ? <StateBlock>AI đang phân tích đề cương theo 4 lớp...</StateBlock> : null}

      {result ? (
        <Panel title="Kết quả kiểm tra">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span
                className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold",
                  statusClass,
                )}
              >
                {result.overall_status ?? "CONDITIONAL"}
              </span>
              <span className="text-sm text-muted-foreground">
                Điểm: <strong>{result.overall_score ?? 0}</strong>/100
              </span>
              <span className="text-xs text-rose-700">Critical: {result.critical_count ?? 0}</span>
              <span className="text-xs text-amber-700">Major: {result.major_count ?? 0}</span>
              <span className="text-xs text-slate-600">Minor: {result.minor_count ?? 0}</span>
            </div>

            {result.findings && result.findings.length > 0 ? (
              <div className="overflow-hidden rounded-2xl border border-border">
                <table className="min-w-full border-collapse text-sm">
                  <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Mức độ</th>
                      <th className="px-4 py-3 font-semibold">Lớp kiểm</th>
                      <th className="px-4 py-3 font-semibold">Vị trí</th>
                      <th className="px-4 py-3 font-semibold">Phát hiện</th>
                      <th className="px-4 py-3 font-semibold">Đề xuất</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.findings.map((f: ProtocolFinding, i: number) => (
                      <tr key={i} className="border-t border-border/60">
                        <td className="px-4 py-3 align-top">
                          <span
                            className={cn(
                              "inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold",
                              f.severity === "critical"
                                ? "bg-rose-100 text-rose-700"
                                : f.severity === "major"
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-slate-100 text-slate-600",
                            )}
                          >
                            {f.severity ?? "-"}
                          </span>
                        </td>
                        <td className="px-4 py-3 align-top text-xs text-muted-foreground">{f.layer ?? "-"}</td>
                        <td className="px-4 py-3 align-top text-xs">{f.location ?? "-"}</td>
                        <td className="px-4 py-3 align-top">{f.finding ?? "-"}</td>
                        <td className="px-4 py-3 align-top text-slate-600">{f.recommendation ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <StateBlock>Không có phát hiện nào.</StateBlock>
            )}

            <Alert tone="warning">
              ⚕ {result.disclaimer ?? "Kết quả kiểm tra do AI thực hiện. Cần người có chuyên môn GMP xác nhận trước khi kết luận chính thức."}
            </Alert>
          </div>
        </Panel>
      ) : null}
    </>
  );
}

function CalculateTab({
  token,
  onUnauthorized,
}: {
  token: string;
  onUnauthorized: () => void;
}) {
  const [formulaCode, setFormulaCode] = useState("");
  const [inputDataRaw, setInputDataRaw] = useState("");
  const [jobName, setJobName] = useState("");
  const [jsonError, setJsonError] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CalculateReportResponse | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setJsonError("");
    if (!formulaCode.trim()) {
      setError("Vui lòng nhập mã công thức.");
      return;
    }
    if (!inputDataRaw.trim()) {
      setError("Vui lòng nhập dữ liệu đầu vào (JSON).");
      return;
    }

    let inputData: Record<string, number | string>;
    try {
      inputData = JSON.parse(inputDataRaw) as Record<string, number | string>;
    } catch {
      setJsonError("Dữ liệu đầu vào không đúng định dạng JSON.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await fetchCalculateReport(
        {
          formula_code: formulaCode.trim(),
          input_data: inputData,
          job_name: jobName.trim() || undefined,
        },
        token,
      );
      setResult(data);
    } catch (err) {
      if (isUnauthorized(err)) { onUnauthorized(); return; }
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const passFail = result?.pass_fail;
  const passFailClass =
    passFail === "pass"
      ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/20"
      : passFail === "fail"
        ? "bg-rose-500/10 text-rose-700 border-rose-500/20"
        : "bg-slate-100 text-slate-600 border-border";

  return (
    <>
      <Panel title="Tính toán thẩm định (Calculation Helper)">
        <form className="space-y-4" onSubmit={(e) => void handleSubmit(e)}>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Mã công thức *">
              <Input
                placeholder="VD: rsd_repeatability"
                value={formulaCode}
                onChange={(e) => setFormulaCode(e.target.value)}
                maxLength={50}
                required
              />
            </FormField>
            <FormField label="Tên job (tuỳ chọn)">
              <Input
                placeholder="VD: Kiểm tra RSD lô 240101"
                value={jobName}
                onChange={(e) => setJobName(e.target.value)}
              />
            </FormField>
          </div>
          <FormField label='Dữ liệu đầu vào (JSON) *'>
            <textarea
              className={cn(
                "h-28 w-full resize-y rounded-2xl border bg-white px-4 py-3 font-mono text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/20",
                jsonError ? "border-rose-400 focus:border-rose-400" : "border-input focus:border-primary",
              )}
              placeholder={'{\n  "values": [10.2, 10.5, 10.1]\n}'}
              value={inputDataRaw}
              onChange={(e) => { setInputDataRaw(e.target.value); setJsonError(""); }}
              required
            />
            {jsonError ? <p className="mt-1 text-xs text-rose-600">{jsonError}</p> : null}
          </FormField>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Button type="submit" disabled={loading}>
            {loading ? "Đang tính toán..." : "Chạy tính toán"}
          </Button>
        </form>
      </Panel>

      {loading ? <StateBlock>Đang thực hiện tính toán và diễn giải...</StateBlock> : null}

      {result ? (
        <Panel title={`Kết quả: ${result.formula ?? result.formula_code ?? ""}`}>
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm text-muted-foreground">
                Kết quả: <strong className="text-slate-900">{result.result ?? "-"}</strong>
              </span>
              {passFail && passFail !== "no_criteria" ? (
                <span className={cn("inline-flex rounded-full border px-3 py-1 text-xs font-semibold", passFailClass)}>
                  {passFail === "pass" ? "ĐẠT" : "KHÔNG ĐẠT"}
                </span>
              ) : null}
              {result.formula_version ? (
                <span className="text-xs text-muted-foreground">v{result.formula_version}</span>
              ) : null}
            </div>

            {result.formula_display ? (
              <div className="rounded-2xl border border-border bg-slate-50 px-4 py-3 font-mono text-sm text-slate-800">
                {result.formula_display}
              </div>
            ) : null}

            {result.criteria_note ? (
              <p className="text-sm text-slate-600">{result.criteria_note}</p>
            ) : null}

            {result.steps && result.steps.length > 0 ? (
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Các bước tính</p>
                {result.steps.map((s, i) => (
                  <div key={i} className="flex gap-2 text-sm">
                    <span className="shrink-0 font-medium text-slate-700">{s.step}:</span>
                    <span className="text-slate-600">{s.detail}</span>
                  </div>
                ))}
              </div>
            ) : null}

            {result.interpretation ? (
              <div className="rounded-2xl border border-border bg-white p-4 text-sm leading-7 text-slate-800">
                {result.interpretation}
              </div>
            ) : null}

            {result.reference_source ? (
              <p className="text-xs text-muted-foreground">Nguồn: {result.reference_source}</p>
            ) : null}

            <Alert tone="warning">
              ⚕ {result.disclaimer ?? "Diễn giải do AI thực hiện. Cần người có chuyên môn xác nhận trước khi đưa vào hồ sơ GMP."}
            </Alert>
          </div>
        </Panel>
      ) : null}
    </>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
      <div className="border-b border-border/60 px-5 py-4">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{title}</h3>
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function Alert({ tone, children }: { tone: "danger" | "warning" | "info"; children: ReactNode }) {
  const cls =
    tone === "danger"
      ? "border-rose-200 bg-rose-50 text-rose-800"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-sky-200 bg-sky-50 text-sky-800";
  return <div className={cn("rounded-2xl border px-4 py-3 text-sm", cls)}>{children}</div>;
}

function StateBlock({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
      {children}
    </div>
  );
}

function Button({
  children,
  disabled,
  type,
}: {
  children: ReactNode;
  disabled?: boolean;
  type?: "submit" | "button";
}) {
  return (
    <button
      type={type ?? "button"}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}

function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20",
        className,
      )}
      {...props}
    />
  );
}

function Select({
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className="h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
      {...props}
    >
      {children}
    </select>
  );
}

function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">{label}</span>
      {children}
    </label>
  );
}
