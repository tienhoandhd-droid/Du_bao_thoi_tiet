# Provenance workflow Chat 04

## Kết luận

14 file có sẵn lúc bắt đầu Chat 04 đều nằm trong thư mục untracked `n8n/workflows/`. Chúng không có commit, PR hoặc release record; trường `_crave_meta.exported_by` chỉ là tự khai và không đủ làm chain-of-custody. Vì vậy chúng không được dùng làm bằng chứng live duy nhất.

Sau reconciliation, gói Chat 04 được commit `7ddb730` và đưa vào PR #3. Remediation WF-14 sau đó được người dùng phê duyệt riêng, thực thi trên đúng workflow `6USn5CYpK9VlyExu`, test và publish trước khi export lại active graph.

## Nguồn đã kiểm tra

1. n8n live qua MCP read-only: `search_workflows(query=TKTL)` trả đúng 14 workflow; `get_workflow_details` lấy draft metadata và active graph cho từng ID.
2. Git: năm source lịch sử có provenance:
   - `n8n/WF-03.json`, `WF-04.json`, `WF-05.json`: commit `fd9d3bc`, 2026-06-28.
   - `n8n/WF-10.json`: commit `084c96b`, 2026-06-28.
   - `n8n/WF-13.json`: commit `9b51546`, 2026-06-28.
3. 14 file untracked ban đầu có mtime 2026-06-28 22:56–23:15 UTC và tự khai “Claude Code Chat 04”, nhưng không có Git provenance.

## Sai lệch của bộ file ban đầu

- WF-02 parse được nhưng chỉ có 0 node/0 connection; live active có 26 node/27 connection.
- WF-12, WF-13 và WF-14 ghi version UUID không khớp live.
- Một số `node_count` trong metadata không khớp số node thật.
- WF-14 cũ tuy ghi đã redaction nhưng dùng UUID giả/khác live, nên không đủ bằng chứng canonical.

## Quy tắc export mới

- Nguồn graph: `activeVersion.nodes` + `activeVersion.connections` từ live.
- Top-level `versionId` của file bằng `activeVersionId` để graph và version không mâu thuẫn.
- `active: false` là guard an toàn import, không mô tả trạng thái live; trạng thái live nằm trong `_crave_meta.liveState.published`.
- Supabase anon key/JWT-like material được thay bằng placeholder; không lưu hash của secret để tránh tạo thêm material có thể dùng đối chiếu.
- Tavily key không còn nằm trong graph hoặc request body; credential `CRAVE-Tavily` được tạo qua UI và giới hạn domain `api.tavily.com`.
- MCP loại bỏ `credentials`; binding thông thường được phục hồi theo source repo/loại node và inventory credential đã phê duyệt. Riêng `CRAVE-Tavily` có evidence UI binding + positive executions `1451221`/`1451310` nhưng credential material vẫn không được export.

## Ranh giới

Không truy vấn, đọc chi tiết hay thay đổi BMS-GMP, VMP, QMSTeam hoặc GMP Kiểm Tạp. Live mutation chỉ áp dụng WF-14 theo phê duyệt: tạo credential, update draft, chạy test, publish và revoke Tavily key cũ. Không ghi Supabase; positive test pin node audit để tránh INSERT production.
