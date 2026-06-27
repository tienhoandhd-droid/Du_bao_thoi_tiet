export type EnvStatus = "ok" | "missing" | "placeholder" | "invalid";

export interface PublicAppEnv {
  supabaseUrl: string;
  supabaseAnonKey: string;
  webhookBase: string;
}

export interface EnvCheck {
  label: string;
  varName: string;
  display: string;
  status: EnvStatus;
}

export interface ValidationOptions {
  requireHttp?: boolean;
  requireJwt?: boolean;
}
