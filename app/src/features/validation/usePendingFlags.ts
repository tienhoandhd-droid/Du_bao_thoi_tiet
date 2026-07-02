import { useEffect, useState } from "react";
import { sb } from "@/lib/supabase";

// Trả về Set document_code đang có cờ AL pending (để hiện badge cảnh báo trên
// kết quả tra cứu). Dùng RPC flagged_document_codes (CRAVE-038): chỉ lộ danh sách
// code, không lộ chi tiết mismatch (chi tiết vẫn hạn chế QA qua scan_flags_pending).
export function usePendingFlagCodes(): Set<string> {
  const [codes, setCodes] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (!sb) return;
    let active = true;
    void (async () => {
      const { data, error } = await sb.rpc("flagged_document_codes");
      if (!active || error || !data) return;
      const arr = Array.isArray(data) ? (data as unknown[]) : [];
      const set = new Set<string>();
      for (const row of arr) {
        if (typeof row === "string") set.add(row);
        else if (row && typeof row === "object") {
          const v = Object.values(row as Record<string, unknown>)[0];
          if (v) set.add(String(v));
        }
      }
      setCodes(set);
    })();
    return () => {
      active = false;
    };
  }, []);
  return codes;
}
