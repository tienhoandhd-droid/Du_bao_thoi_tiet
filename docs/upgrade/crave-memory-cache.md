# CRAVE Memory/Cache — tăng tốc & chất lượng trả lời (M10)

> Đánh giá & thiết kế áp dụng "bộ nhớ AI" vào CRAVE. Kết luận: **KHÔNG cần framework bộ nhớ bên thứ 3**
> (Mem0/Zep/Letta — hướng chatbot hội thoại, phụ thuộc ngoài, chống lại free/self-host + tính xác định GMP).
> Dùng **native pgvector** — hệ thống ĐÃ có `semantic_cache` (031b) + `claim_verdicts` (032); chỉ cần nối.
> Nguồn: Mem0 (ECAI 2025, ~48k★), Zep/Graphiti (temporal KG), Letta/MemGPT (tiered), semantic cache
> (arXiv 2411.05276 — giảm tới 68,8% lệnh LLM, nhanh tới ~300%), Proximity RAG cache 2025.

## Đánh giá "bộ nhớ AI có áp dụng được không?"
**CÓ — nhưng dạng phù hợp GMP, không phải memory hội thoại cá nhân hoá.** Vì thẩm định cần câu trả lời
**xác định, bám nguồn**, không nên để memory cá nhân "trôi" theo người dùng. Ta mượn *khái niệm*, làm *native*:

| Framework 2026 | Ý niệm mượn được | Đã có sẵn trong CRAVE |
|---|---|---|
| **Zep/Graphiti** (temporal KG — fact đúng *khi nào*) | Hiệu lực theo thời gian (tiêu chuẩn bị thay thế) | `document_versions` + verdict `outdated` |
| **Letta/MemGPT** (core/archival/recall tiers) | Phân tầng bộ nhớ | glossary=core · corpus=archival · truy vấn gần đây=recall |
| **Mem0** (trích fact bền, multi-signal retrieval) | Kho fact tái dùng | `claim_verdicts` = kho verdict đã kiểm chứng |
| **Semantic cache** (tái dùng câu tương tự) | Tăng tốc | `semantic_cache` (031b) — ĐÃ có, chưa nối |

## Thiết kế 3 tầng bộ nhớ (đều native pgvector)

```
Câu hỏi VI → framing → claim (VI+EN) → embed claim (OpenAI)
   │
   ├─ L1 VERDICT SEMANTIC CACHE (semantic_cache_lookup_v1, cosine ≥ 0.9, is_valid)
   │     └─ HIT → trả verdict tức thì (BỎ 5 lệnh LLM MoA) + nhãn "từ bộ nhớ · <ngày>" + nút Kiểm lại
   │     miss ↓
   ├─ L2 VERIFIED-CLAIM MEMORY (claim_verdicts đã human_signoff, cosine cao)
   │     └─ có prior đã người duyệt → dùng làm bằng chứng tin cậy CAO / trả thẳng (không cần chạy lại)
   │     miss ↓
   └─ CHẠY MoA v2 đầy đủ → lưu verdict → GHI vào semantic_cache (nếu verdict "đã ngã ngũ")
```

- **L3 Popularity/FAQ:** `semantic_cache.hit_count` sẵn có → xếp hạng câu phổ biến, **pre-warm** cache ngoài giờ,
  gợi ý "câu hỏi hay gặp". "Phần được tìm nhiều nhất" = đúng ý tưởng của bạn, đo bằng `hit_count`.

## Lợi ích
- **Tốc độ:** claim lặp/tương tự → bỏ toàn bộ MoA (5 LLM, ~44s) → trả trong <1s. Semantic cache giảm tới ~68,8% lệnh LLM.
- **Chất lượng/nhất quán:** cùng một câu hỏi luôn cho cùng verdict (không dao động theo lần gọi LLM); verdict đã
  human sign-off trở thành "trí nhớ tổ chức" tái dùng.
- **Chi phí:** ít lệnh OpenAI aggregator hơn.

## Ràng buộc GMP (bắt buộc)
- **Invalidate:** trigger `semantic_cache_invalidate_trg` (031b) đã tự vô hiệu khi `approved_for_ai_use` đổi.
  Bổ sung: gắn cache entry với **version tài liệu đã trích dẫn** → supersede version thì invalidate.
- **Minh bạch:** cache hit phải hiển thị nhãn "trả từ bộ nhớ ngày …" + cho **Kiểm lại** (chạy MoA mới).
- **Không cache câu chưa ngã ngũ:** verdict `insufficient`/`conflicting` KHÔNG cache như đã giải quyết.
- **Phân bậc tin cậy:** human-signed-off > AI-cache (DRAFT). Cache AI vẫn là DRAFT.
- **Ngưỡng chặt hơn cho GMP:** dùng cosine **≥ 0.9** (không 0.8) để tránh trả nhầm câu khác nghĩa vi tế
  (vd "oil aerosol" vs "oil vapor").

## Phụ thuộc & thứ tự
1. Cần **query embedding** (OpenAI text-embedding-3-small) làm khoá match L1/L2 — 1 call rẻ, **độc lập** với
   R06 (corpus embedding). Trước mắt có thể thêm **tầng exact-match** (hash `claim_text_en` chuẩn hoá) — chạy
   ngay không cần embedding.
2. Nối cache-lookup vào đầu workflow v2 + ghi cache ở cuối.
3. Panel "câu hỏi hay gặp" (L3) ở UI (M5).
