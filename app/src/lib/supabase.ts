import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { classifyEnvValue, getPublicEnv } from "@/lib/env";

function createPublicSupabaseClient(): SupabaseClient | null {
  const env = getPublicEnv();
  const urlStatus = classifyEnvValue(env.supabaseUrl, { requireHttp: true });
  const keyStatus = classifyEnvValue(env.supabaseAnonKey, { requireJwt: true });

  if (urlStatus !== "ok" || keyStatus !== "ok") {
    return null;
  }

  return createClient(env.supabaseUrl, env.supabaseAnonKey);
}

export const sb = createPublicSupabaseClient();
