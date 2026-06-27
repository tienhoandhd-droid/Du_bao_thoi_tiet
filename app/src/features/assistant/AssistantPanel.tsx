import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { fetchAssistant } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  AssistantCitation,
  AssistantQueryResponse,
  AssistantToolCall,
} from "@/types/api";

type ChatRole = "user" | "assistant";

interface ChatTurn {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
  sessionId?: string;
  confidence?: string;
  disclaimer?: string;
  toolCalls?: AssistantToolCall[];
  citations?: AssistantCitation[];
}

function stringify(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function normalizeTools(response: AssistantQueryResponse): AssistantToolCall[] {
  return (response.tool_calls ?? response.tools ?? []).filter(Boolean);
}

function normalizeCitations(response: AssistantQueryResponse): AssistantCitation[] {
  return (response.citations ?? response.sources ?? []).filter(Boolean);
}

function badgeClass(grounded?: boolean): string {
  return grounded
    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
    : "border-amber-200 bg-amber-50 text-amber-700";
}

function confidenceClass(confidence?: string): string {
  switch ((confidence ?? "").toUpperCase()) {
    case "HIGH":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "MEDIUM":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "LOW":
      return "border-rose-200 bg-rose-50 text-rose-700";
    case "BLOCKED":
      return "border-slate-200 bg-slate-50 text-slate-600";
    default:
      return "border-border bg-muted text-muted-foreground";
  }
}

function preview(value: unknown): string {
  const text = stringify(value);
  return text.length > 200 ? `${text.slice(0, 200)}…` : text;
}

export function AssistantPanel({ token }: { token: string }) {
  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setSessionId("");
    setInput("");
    setTurns([]);
    setError("");
    setLoading(false);
  }, [token]);

  const hasHistory = turns.length > 0;

  const submit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const query = input.trim();
      if (!query || !token || loading) return;

      const userTurn: ChatTurn = {
        id: `user-${Date.now()}`,
        role: "user",
        content: query,
        createdAt: Date.now(),
      };

      setTurns((current) => [...current, userTurn]);
      setInput("");
      setLoading(true);
      setError("");

      try {
        const response = await fetchAssistant(
          {
            query,
            session_id: sessionId || undefined,
            response_language: "vi",
            message: query,
          },
          token,
        );

        const assistantTurn: ChatTurn = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.answer || response.message || "Không có nội dung trả lời.",
          createdAt: Date.now(),
          sessionId: response.session_id || sessionId || undefined,
          confidence: response.confidence,
          disclaimer: response.disclaimer,
          toolCalls: normalizeTools(response),
          citations: normalizeCitations(response),
        };

        if (assistantTurn.sessionId) {
          setSessionId(assistantTurn.sessionId);
        }

        setTurns((current) => [...current, assistantTurn]);
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : "Lỗi không xác định";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [input, loading, sessionId, token],
  );

  const totalToolCalls = useMemo(
    () => turns.reduce((count, turn) => count + (turn.toolCalls?.length ?? 0), 0),
    [turns],
  );

  return (
    <section className="overflow-hidden rounded-3xl border border-border/70 bg-white/80 shadow-[0_8px_30px_rgba(13,27,42,0.06)] backdrop-blur">
      <div className="border-b border-border/60 px-5 py-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Trợ lý WF-12
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Nối webhook `/assistant-query`, hiển thị tool-call và citation grounding.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px] font-semibold">
            <Pill className="border-primary/20 bg-primary/10 text-primary">
              Session: {sessionId || "chưa có"}
            </Pill>
            <Pill className="border-slate-200 bg-slate-50 text-slate-700">
              Turns: {turns.length}
            </Pill>
            <Pill className="border-slate-200 bg-slate-50 text-slate-700">
              Tool calls: {totalToolCalls}
            </Pill>
          </div>
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="border-b border-border/60 p-5 lg:border-b-0 lg:border-r">
          <form className="space-y-3" onSubmit={submit}>
            <label className="block space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
                Câu hỏi trợ lý
              </span>
              <textarea
                className="min-h-[110px] w-full rounded-2xl border border-input bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20"
                placeholder="Ví dụ: Tài liệu nào xác minh điều kiện tiên quyết IQ?"
                value={input}
                onChange={(event) => setInput(event.target.value)}
              />
            </label>

            {error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                {error}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <button
                className={cn(
                  "inline-flex items-center justify-center rounded-2xl px-4 py-2.5 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60",
                  "bg-primary text-primary-foreground hover:bg-primary/90",
                )}
                disabled={!token || loading}
                type="submit"
              >
                {loading ? "Đang hỏi WF-12..." : "Gửi câu hỏi"}
              </button>
              <button
                className="inline-flex items-center justify-center rounded-2xl border border-border bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50"
                disabled={loading || !turns.length}
                type="button"
                onClick={() => {
                  setTurns([]);
                  setSessionId("");
                  setError("");
                }}
              >
                Xóa lịch sử
              </button>
            </div>
          </form>

          <div className="mt-5 space-y-3">
            {hasHistory ? (
              turns.map((turn) => (
                <article
                  key={turn.id}
                  className={cn(
                    "rounded-2xl border px-4 py-3",
                    turn.role === "user"
                      ? "border-primary/15 bg-primary/5"
                      : "border-border bg-white",
                  )}
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      {turn.role === "user" ? "Người dùng" : "Trợ lý"}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {new Date(turn.createdAt).toLocaleTimeString("vi-VN")}
                    </span>
                  </div>
                  {turn.role === "user" ? (
                    <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">
                      {turn.content}
                    </p>
                  ) : (
                    <div className="space-y-4">
                      <div className="whitespace-pre-wrap rounded-2xl bg-slate-50 p-4 text-sm leading-7 text-slate-800">
                        {turn.content}
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        {turn.confidence ? (
                          <span
                            className={cn(
                              "rounded-full border px-2.5 py-1 text-[11px] font-semibold",
                              confidenceClass(turn.confidence),
                            )}
                          >
                            confidence={turn.confidence}
                          </span>
                        ) : null}
                        {turn.sessionId ? (
                          <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-700">
                            session_id={turn.sessionId}
                          </span>
                        ) : null}
                      </div>

                      {turn.toolCalls?.length ? (
                        <ToolCallTable toolCalls={turn.toolCalls} />
                      ) : null}

                      {turn.citations?.length ? (
                        <CitationTable citations={turn.citations} />
                      ) : null}

                      {turn.disclaimer ? (
                        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
                          ⚕ {turn.disclaimer}
                        </div>
                      ) : null}
                    </div>
                  )}
                </article>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-8 text-center text-sm text-muted-foreground">
                Chưa có cuộc hội thoại nào. Gửi câu hỏi đầu tiên để gọi WF-12.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-5 p-5">
          <SummaryCard title="Tool-call">
            <p className="text-sm text-muted-foreground">
              Bảng này phản ánh các tool WF-12 đã gọi qua webhook, không đụng logic
              backend.
            </p>
          </SummaryCard>

          <SummaryCard title="Citation grounding">
            <p className="text-sm text-muted-foreground">
              Badge `grounded=true/false` lấy trực tiếp từ response để phân biệt
              citation đã xác minh.
            </p>
          </SummaryCard>

          <SummaryCard title="Lưu ý vận hành">
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Chỉ dùng token hiện tại của Supabase Auth.</li>
              <li>• Không đổi WF-12 backend, chỉ tiêu thụ `/assistant-query`.</li>
              <li>• Citation table hiển thị cả claim_text/snippet khi có.</li>
            </ul>
          </SummaryCard>
        </div>
      </div>
    </section>
  );
}

function ToolCallTable({ toolCalls }: { toolCalls: AssistantToolCall[] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
      <div className="border-b border-border px-4 py-3">
        <h4 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Tool-call
        </h4>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
            <tr>
              <Th>#</Th>
              <Th>Tên</Th>
              <Th>Trạng thái</Th>
              <Th>Arguments</Th>
              <Th>Result</Th>
            </tr>
          </thead>
          <tbody>
            {toolCalls.map((tool, index) => (
              <tr key={`${tool.name ?? tool.tool_name ?? "tool"}-${index}`} className="border-t border-border/60">
                <Td>{index + 1}</Td>
                <Td className="font-semibold">
                  {tool.name || tool.tool_name || "-"}
                </Td>
                <Td>
                  <Badge className="bg-slate-100 text-slate-700">
                    {tool.status || "-"}
                  </Badge>
                </Td>
                <Td>
                  <pre className="max-w-[260px] whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-3 text-xs text-slate-700">
                    {preview(tool.arguments)}
                  </pre>
                </Td>
                <Td>
                  <pre className="max-w-[260px] whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-3 text-xs text-slate-700">
                    {preview(tool.result ?? tool.message)}
                  </pre>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CitationTable({ citations }: { citations: AssistantCitation[] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
      <div className="border-b border-border px-4 py-3">
        <h4 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Citation grounding
        </h4>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.14em] text-slate-500">
            <tr>
              <Th>#</Th>
              <Th>Mã tài liệu</Th>
              <Th>Phiên bản</Th>
              <Th>Trang</Th>
              <Th>Trạng thái</Th>
              <Th>Claim</Th>
            </tr>
          </thead>
          <tbody>
            {citations.map((citation, index) => (
              <tr key={`${citation.document_code ?? "citation"}-${index}`} className="border-t border-border/60">
                <Td>{citation.citation_rank ?? index + 1}</Td>
                <Td className="font-semibold">
                  {citation.document_code || "-"}
                </Td>
                <Td>{citation.version ?? "-"}</Td>
                <Td>{citation.page_number ?? "-"}</Td>
                <Td>
                  <span
                    className={cn(
                      "inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold",
                      badgeClass(citation.grounded),
                    )}
                  >
                    grounded={citation.grounded ? "true" : "false"}
                  </span>
                </Td>
                <Td>
                  <div className="max-w-[300px] whitespace-normal text-slate-600">
                    {citation.claim_text || citation.snippet || "-"}
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-3xl border border-border bg-white p-5 shadow-sm">
      <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {title}
      </h4>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Badge({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold",
        className,
      )}
    >
      {children}
    </span>
  );
}

function Pill({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold",
        className,
      )}
    >
      {children}
    </span>
  );
}

function Th({ children }: { children: ReactNode }) {
  return <th className="px-4 py-3 font-semibold">{children}</th>;
}

function Td({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <td className={cn("px-4 py-3 align-top", className)}>{children}</td>;
}
