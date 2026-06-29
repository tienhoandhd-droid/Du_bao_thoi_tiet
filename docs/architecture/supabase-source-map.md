# Supabase source map 001–022

Tài liệu này đối chiếu migration source trong Git với danh sách migration live của Supabase project `bdttccztjtrcaztjgkot` do Claude Code thu thập ngày **2026-06-29**. Phạm vi chỉ thuộc TKTL/CRAVE; không liên quan BMS, VMP hoặc QMS.

## Phân loại

- `exact`: có source repo mang cùng tên/ngữ nghĩa với record live được cung cấp.
- `baseline-only`: không có migration source riêng; chỉ có snapshot read-only để hỗ trợ điều tra.
- `missing evidence`: repo và live không đủ bằng chứng để khẳng định chuỗi source tương ứng chính xác.

| Số | Tên | Trạng thái source | Ghi chú |
|---|---|---|---|
| 001–011 | `(cũ)` | `baseline-only` | Không có file riêng; được áp dụng trước khi migration tracking bắt đầu. |
| 012 | `(để dành Plan B)` | `baseline-only` | Chủ ý skip; không tạo migration 012 trong Chat 03. |
| 013 | `citation_grounding` | `exact` | Repo `013_citation_grounding.sql`; live `013_citation_grounding`. |
| 014 | `chat_memory` | `exact` | Repo `014_chat_memory.sql`; live `014_chat_memory`. |
| 015 | `platform_security_hardening` | `exact` | Repo `015_platform_security_hardening.sql`; live `015_platform_security_hardening`. |
| 016 | `eval_harness` | `missing evidence` | Repo có `016_eval_harness.sql`, nhưng live không có record migration 016. Không coi đây là source live đã xác minh. |
| 017 | `equipment_glossary` | `exact` | Repo `017_equipment_glossary.sql`; live `017_equipment_glossary`. |
| 018 | `seed_validation_data` | `exact` | Repo `018_seed_validation_data.sql`; live `018_seed_validation_data`. |
| 019 | `drive_sync_log` | `exact` | Repo `019_drive_sync_log.sql`; live `019_drive_sync_log`. |
| 020 | `validation_sessions` | `exact` | Repo `020_validation_sessions.sql`; live `020_validation_sessions`. |
| 021 | `eval_harness` | `exact` | Repo `021_eval_harness.sql`; live `021_eval_harness`. Live mang nội dung eval harness ở số 021, không phải 016. |
| 021b | `eval_function_v2` | `exact` | Repo `021b_eval_function_v2.sql`; live `021b_eval_function_v2`. |
| 021c | `eval_function_v3_or_tsquery` | `exact` | Repo là `021c_eval_function_v3.sql`; record live là `021c_eval_function_v3_or_tsquery`. Definition progression phù hợp dữ liệu được cung cấp, nhưng tên file không byte-identical với tên live. |
| 021d | `eval_score_columns_fix` | `exact` | Repo `021d_eval_score_columns_fix.sql`; live `021d_eval_score_columns_fix`. |
| 022 | `fix_eval_rank_order` | `exact` | Chat 03 tạo `022_fix_eval_rank_order.sql` từ definition live đã được paste; không apply lại lên production. |

## Gaps và điểm cần điều tra

1. Migration 001–011 chỉ có baseline snapshot; chưa đủ để dựng database từ source.
2. Migration 012 được giữ cho Plan B và không có record live; đây là chủ ý, không phải file bị bỏ sót.
3. Repo có `016_eval_harness.sql`, nhưng danh sách live không có migration 016 và thay vào đó có `021_eval_harness`. Nguồn gốc, thời điểm đổi số và quan hệ giữa hai file cần được điều tra thêm ở **Chat S1**.
4. Tên file repo `021c_eval_function_v3.sql` không khớp hoàn toàn tên live `021c_eval_function_v3_or_tsquery`; cần giữ bằng chứng này trong review dù nội dung hiện có thể hiện OR-tsquery.
5. Rollback cũ 013–021d vẫn theo convention đặt trong `supabase/migrations/`; từ 022 trở đi rollback canonical nằm tại `supabase/rollbacks/`.

## Migration 022 và rollback

Forward source tái tạo function live với sửa lỗi hai tầng sắp xếp: tầng `DISTINCT ON` chọn chunk có rank cao nhất của từng `document_code`, sau đó outer query dùng `ORDER BY rank DESC` trước `LIMIT p_top_k`. Function được khóa `search_path` về `public, extensions` theo header chuẩn.

Không có definition cũ đầy đủ, vì vậy rollback 022 không bịa logic `ORDER BY document_code`: rollback chỉ drop đúng signature và ghi rõ **manual restore required**. Rollback không xóa các dòng mà function đã ghi vào `eval_runs` hoặc `eval_results`, nhằm giữ audit trail.

## Giới hạn bằng chứng

Source map này dựa trên danh sách migration live và definition `run_fts_eval_v1` được paste vào Chat 03. Nó không xác nhận policy, trigger, grant, function owner hoặc toàn bộ schema. Các thuộc tính đó cần Claude Code đối chiếu qua MCP trước khi dùng source package cho restore rehearsal hay migration tiếp theo.
