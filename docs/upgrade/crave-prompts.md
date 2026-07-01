# CRAVE — Bộ prompt kiểm chứng nhận định (GĐ4.5 / M3)

> Nguồn chân lý của prompt là bảng `prompt_versions` (seed migration `033`). File này là **spec I/O**
> để review; khi sửa prompt, tăng `version` và cập nhật cả hai. Mọi prompt: **trả lời tiếng Việt**,
> **trích dẫn giữ nguyên EN gốc**, **chỉ dùng dữ kiện trong context** (chống bịa), output **JSON** khớp
> cột DB migration `032`.

## Luồng 4 bước

```
Câu hỏi VI
  └─(1) crave_claim_framing ─► claims{claim_text_vi, claim_text_en, frame_used, facets}
        └─ retrieval_queries → hybrid_search_v4 (R) + glossary (A) → CONTEXT = [{chunk_id, text_en}]
              ├─(2) crave_support_agent (free #1)  ─► ai_query_sources.stance = support
              └─(3) crave_refute_agent  (free #2)  ─► stance = refute | limiting
                    └─(4) crave_judge (free #3)    ─► claim_verdicts{verdict, confidence, ...}
                          └─ requires_human_signoff / escalation_target → OpenAI hoặc human (DRAFT)
```

## Hợp đồng I/O

### (1) `crave_claim_framing` — bước C
- **Vào:** câu hỏi tiếng Việt.
- **Ra:** `{claim_text_vi, claim_text_en, frame_used ∈ {pcc,pico,peco}, facets{population,concept,context,comparison,exposure,outcome,threshold,doc_type}, retrieval_queries{vi[],en[]}}`.
- **Chọn khung:** `pico` khi so sánh 2 phương án · `peco` khi ảnh hưởng điều kiện/phơi nhiễm · `pcc` mặc định.
- **Ghi DB:** `claims.frame_used`, `claims.facets`, `claims.claim_text_vi/en`.

### (2) `crave_support_agent` — bước V (ủng hộ), free-tier #1
- **Vào:** claim + CONTEXT (chunk_id + text_en).
- **Ra:** `{stance:"support", no_evidence, evidence:[{chunk_id, quote_en, stance_strength 0..1, note_vi}]}`.
- **Ghi DB:** mỗi evidence → `ai_query_sources` với `stance='support'`, `stance_strength`.

### (3) `crave_refute_agent` — bước V (phản bác/giới hạn), free-tier #2 (khác provider)
- **Ra:** `{no_evidence, evidence:[{chunk_id, quote_en, stance:"refute|limiting", stance_strength, note_vi}]}`.
- **Ghi DB:** `ai_query_sources.stance ∈ {refute, limiting}`.
- Dùng **provider khác** Support để có tính độc lập thật.

### (4) `crave_judge` — bước E
- **Vào:** claim + danh sách bằng chứng ủng hộ + phản bác/giới hạn.
- **Ra:** `{verdict, confidence, rationale_vi, answer_vi, support_count, refute_count, requires_human_signoff, escalation_target ∈ {null,openai,human}, citations:[{chunk_id, quote_en}]}`.
- **Verdict taxonomy (khớp check DB):** `supported | conditional | conflicting | outdated | insufficient`.
- **Ghi DB:** `claim_verdicts` (một dòng, append-only).

## Quy tắc quyết định (Judge)

| Tình huống bằng chứng | verdict | human sign-off |
|---|---|---|
| Ủng hộ mạnh, phản bác không đáng kể | `supported` | không |
| Đúng nhưng chỉ trong điều kiện (limiting) | `conditional` | không (nêu rõ điều kiện) |
| Hai phía đáng kể / nguồn mâu thuẫn | `conflicting` | **có** |
| Dấu hiệu nguồn bị thay thế/lỗi thời | `outdated` | **có** |
| Không đủ bằng chứng trong corpus | `insufficient` | có nếu câu tới hạn; **từ chối kết luận** |

- `requires_human_signoff = true` khi verdict ∈ {conflicting, outdated}, hoặc insufficient cho câu GMP tới hạn, hoặc `confidence < 0.6`.
- `escalation_target='openai'` khi mệnh đề tới hạn nhưng bằng chứng chưa ngã ngũ (orchestrator chạy lại Judge bằng OpenAI); `='human'` khi cần người duyệt.
- Ràng buộc DB `032`: `escalated = (escalation_target is not null)`.

## Escalation ladder (khớp §0 roadmap free-tier)
```
free-tier Judge → confidence thấp / tới hạn ─► OpenAI Judge ─► vẫn không chắc ─► human sign-off (DRAFT)
mọi lượt ghi append-only: ai_query_sources (stance) + claim_verdicts + audit_log
```
