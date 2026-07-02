# CRAVE claim-verification — eval baseline (LAMSAFE)

> Chạy `scripts/ingest/crave_eval_claims.py` trên
> `eval/datasets/crave_golden_claims_lamsafe.jsonl` (6 golden claims grounded vào
> tài liệu thật LV-BSC-A2). Ngày 2026-07-02. KHÔNG chế số — kết quả thật qua webhook MoA.

## Kết quả

| Claim | Nội dung | Verdict (thật) | Conf | Khớp verdict | Citation | Refusal |
|---|---|---|---|---|---|---|
| LV-C01 | Vận tốc gió trung bình | `supported` | 0.90 | ✅ | ✅ 2 | ✅ |
| LV-C02 | Tần suất thay HEPA (2-3 năm) | `conditional` | 0.80 | ✅ | ✅ 1 | ✅ |
| LV-C03 | HEPA lọc khí độc? | `conflicting` | 0.85 | ✅ | ✅ 1 | ✅ |
| LV-C04 | Công suất W (KHÔNG có trong doc) | `insufficient` | 0.55 | ✅ | ⚠ vẫn kèm 2 cite | ✅ refuse |
| LV-C05 | Chiều cao cửa mở (20cm) | `supported` | 0.90 | ✅ | ✅ 3 | ✅ |
| LV-C06 | Dùng ngọn lửa? | `supported` | 0.85 | ✅ | ✅ 2 | ✅ |

*(LV-C06 gặp 404 tạm thời lần chạy batch đầu do webhook vừa publish; retry PASS.)*

## Metrics baseline
- **verdict_match_rate = 6/6 = 1.0** — mọi verdict rơi đúng nhóm kỳ vọng
  (supported / conditional / conflicting / insufficient).
- **refusal_ok_rate = 6/6 = 1.0** — claim ngoài phạm vi (công suất W) → `insufficient`
  đúng (no-source refusal hoạt động).
- **citation_ok_rate = 5/6** — chỉ LV-C04 (insufficient) vẫn kèm citation; không sai
  bản chất nhưng nên siết: insufficient không nên trả citation "khẳng định".

## Nhận xét
- CRAVE MoA (Gemini+2×Groq proposer → OpenAI aggregator, có framing fallback Groq)
  **phân biệt đúng cả 4 loại verdict** trên tài liệu thật, trích dẫn chunk có thật,
  và **từ chối đúng** khi thiếu bằng chứng — đạt tinh thần GMP fail-closed.
- Ngưỡng roadmap (faithfulness ≥0,90, no-source refusal ≥90%): baseline này đạt về
  refusal (100%) và verdict; faithfulness cấp mệnh đề (LLM judge) là bước eval kế tiếp.
- Hạn chế: n=6 (1 tài liệu LV-BSC-A2). Mở rộng golden set khi corpus tăng.

## Cập nhật sau siết prompt (aggregator v1.1 — migration 039)
Đã thêm rule fail-closed: `insufficient` ⇒ support=[]/citations=[]. **Verify lại C04**
(công suất W): verdict `insufficient`, **support=0, citations=0, refute=0** →
**citation_ok = 6/6 = 1.0**. Workflow MoA đọc prompt theo `is_active` (tự dùng v1.1).

## Việc tiếp
1. ✅ (xong) Siết prompt aggregator: insufficient không kèm citation.
2. Thêm faithfulness judge cấp mệnh đề (free LLM) vào runner.
3. Mở rộng golden claims theo corpus mới.
