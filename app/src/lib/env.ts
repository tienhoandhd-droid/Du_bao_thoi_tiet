import type { EnvStatus, PublicAppEnv, ValidationOptions } from "@/types/env";

const PLACEHOLDER = /^__.*__$/;
const JWT_LIKE = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;

function readEnv(name: keyof ImportMetaEnv): string {
  return (import.meta.env[name] ?? "").trim();
}

export function getPublicEnv(): PublicAppEnv {
  return {
    supabaseUrl: readEnv("VITE_SUPABASE_URL"),
    supabaseAnonKey: readEnv("VITE_SUPABASE_ANON_KEY"),
    webhookBase: readEnv("VITE_WEBHOOK_BASE"),
  };
}

export function isPlaceholder(value: string): boolean {
  return PLACEHOLDER.test(value);
}

export function normalizeBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

export function classifyEnvValue(
  value: string,
  options: ValidationOptions = {},
): EnvStatus {
  if (!value) return "missing";
  if (isPlaceholder(value)) return "placeholder";
  if (options.requireHttp && !/^https?:\/\//i.test(value)) return "invalid";
  if (options.requireJwt && !JWT_LIKE.test(value)) return "invalid";
  return "ok";
}

export function maskValue(value: string): string {
  if (value.length <= 12) return "••••••";
  return `${value.slice(0, 6)}…${value.slice(-4)} (${value.length} ký tự)`;
}

export function buildWebhookUrl(path: string): string {
  const base = normalizeBaseUrl(getPublicEnv().webhookBase);
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${base}${suffix}`;
}
