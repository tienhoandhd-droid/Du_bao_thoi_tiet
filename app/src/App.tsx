import { useMemo } from "react";
import { cn } from "@/lib/utils";

type CheckStatus = "ok" | "missing" | "placeholder";

interface EnvCheck {
  label: string;
  varName: string;
  display: string;
  status: CheckStatus;
}

// Placeholder kiểu cũ của bản vanilla, vd '__SUPABASE_URL__'
const PLACEHOLDER = /^__.*__$/;

function classify(raw: string | undefined): CheckStatus {
  if (!raw || raw.trim() === "") return "missing";
  if (PLACEHOLDER.test(raw.trim())) return "placeholder";
  return "ok";
}

// Che bí mật khi hiển thị (anon key tuy public-safe nhưng không cần phơi toàn bộ)
function mask(value: string): string {
  if (value.length <= 12) return "••••••";
  return `${value.slice(0, 6)}…${value.slice(-4)} (${value.length} ký tự)`;
}

export default function App() {
  const checks = useMemo<EnvCheck[]>(() => {
    const env = import.meta.env;
    const url = env.VITE_SUPABASE_URL;
    const anon = env.VITE_SUPABASE_ANON_KEY;
    const webhook = env.VITE_WEBHOOK_BASE;
    return [
      {
        label: "Supabase URL",
        varName: "VITE_SUPABASE_URL",
        display: url || "(rỗng)",
        status: classify(url),
      },
      {
        label: "Supabase Anon Key",
        varName: "VITE_SUPABASE_ANON_KEY",
        display: anon ? mask(anon) : "(rỗng)",
        status: classify(anon),
      },
      {
        label: "Webhook Base (n8n)",
        varName: "VITE_WEBHOOK_BASE",
        display: webhook || "(rỗng)",
        status: classify(webhook),
      },
    ];
  }, []);

  const allOk = checks.every((c) => c.status === "ok");

  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="w-full max-w-xl">
        <div className="overflow-hidden rounded-lg border border-border bg-card text-card-foreground shadow-sm">
          {/* dải băng giá */}
          <div className="h-1.5 bg-gradient-to-r from-primary via-accent to-primary" />
          <div className="space-y-6 p-6">
            <header className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                CRAVE · Chat 09 · nền móng TypeScript
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">
                GMP Validation Intelligence
              </h1>
              <p className="text-sm text-muted-foreground">
                Dashboard TypeScript (Vite + React + Tailwind + shadcn/ui). Trang này
                xác minh đường ống build và biến môi trường được inject lúc build.
              </p>
            </header>

            <section className="space-y-2">
              <h2 className="text-sm font-medium">
                Biến môi trường (inject lúc build từ GitHub Variables)
              </h2>
              <ul className="space-y-2">
                {checks.map((c) => (
                  <li
                    key={c.varName}
                    className="flex items-start justify-between gap-3 rounded-md border border-border bg-muted/40 px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{c.label}</p>
                      <p className="break-all font-mono text-xs text-muted-foreground">
                        {c.varName} = {c.display}
                      </p>
                    </div>
                    <StatusBadge status={c.status} />
                  </li>
                ))}
              </ul>
            </section>

            <footer
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium",
                allOk
                  ? "bg-primary/10 text-primary"
                  : "bg-destructive/10 text-destructive",
              )}
            >
              {allOk
                ? "Đủ 3 biến — đường ống build và inject hoạt động."
                : "Thiếu hoặc còn placeholder — kiểm tra Repository Variables rồi chạy lại Action."}
            </footer>
          </div>
        </div>

        <p className="mt-3 text-center text-xs text-muted-foreground">
          App vanilla cũ vẫn chạy song song tới khi đạt parity (Chat 10).
        </p>
      </div>
    </main>
  );
}

function StatusBadge({ status }: { status: CheckStatus }) {
  const map: Record<CheckStatus, { text: string; cls: string }> = {
    ok: { text: "OK", cls: "bg-primary/15 text-primary" },
    missing: { text: "RỖNG", cls: "bg-destructive/15 text-destructive" },
    placeholder: {
      text: "PLACEHOLDER",
      cls: "bg-destructive/15 text-destructive",
    },
  };
  const s = map[status];
  return (
    <span
      className={cn(
        "shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold",
        s.cls,
      )}
    >
      {s.text}
    </span>
  );
}
