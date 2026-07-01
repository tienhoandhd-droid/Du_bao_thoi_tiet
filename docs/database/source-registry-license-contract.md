# Source Registry và License Gate Contract — CRAVE-025

## Mục tiêu

Mọi nguồn bên ngoài phải được phân loại trước khi fetch hoặc ingest. Không có
record, record chưa active, chưa được approve hoặc hết hiệu lực đều phải `deny`.
`web_sources.is_active` legacy không được coi là approval pháp lý.

## Quyết định

| Decision | Được lấy nội dung | Được giữ metadata | Yêu cầu |
|---|---:|---:|---|
| `allow` | Có | Có | Active, approval, effective window và rule/source match |
| `curated` | Có, theo phạm vi curator | Có | Active, approval, effective window; workflow vẫn cần human-review gate |
| `metadata_only` | Không | Có | Chỉ title/URL/provenance; không tạo raw file/chunk |
| `deny` | Không | Chỉ denial evidence tối thiểu | Unknown, inactive, expired hoặc explicit deny |

## Legacy reconciliation

- `web_sources`: gom theo normalized domain; giữ mọi UUID trong
  `legacy_web_source_ids` và mọi URL trong `seed_urls`.
- Ba record EMA cùng `health.ec.europa.eu` trở thành một registry record, không
  tạo ba nguồn canonical trùng domain.
- Vì live baseline không có `approved_by/approved_at`, toàn bộ legacy web source
  được tạo ở `metadata_only`, `is_active=false`.
- `approved_sources`: nếu có record hợp lệ thì giữ UUID trong
  `legacy_approved_source_ids`; chỉ active khi có đủ owner, approver, timestamp
  và license summary. Mapping legacy dùng approver làm owner ban đầu và vẫn cần
  governance review sau migration.
- Không sửa hoặc xóa hai bảng legacy trong migration 025.

## Writer/reader

- Writer: admin/QA manager qua PostgREST/SQL được kiểm soát; RLS chỉ cho
  `authenticated` có đúng role insert/update source và insert license rule.
- Reader: WF-09/WF-11/WF-14 và governance UI gọi
  `resolve_source_policy_v1(text,timestamptz)`.
- `license_rules` append-only; thay đổi quyết định bằng row mới/effective window,
  không UPDATE/DELETE/TRUNCATE lịch sử.

## Resolver contract

Input:

- `p_url`: URL bắt buộc, tối đa 2048 ký tự.
- `p_at`: thời điểm đánh giá; mặc định `now()`.

Output JSON allowlist:

- `matched`, `source_registry_id`, `source_name`, `domain`;
- `decision`, `allow_fetch`, `metadata_only`, `rule_id`, `reason`;
- `public_only`, `robots_required`, `crawl_delay_seconds`,
  `allowed_content_types`, `evaluated_at`.

Unknown/inactive/expired trả:

```json
{
  "matched": false,
  "decision": "deny",
  "allow_fetch": false,
  "reason": "unknown_inactive_or_expired_source"
}
```

## Rollback/recovery

Rollback tự động chỉ được phép khi chưa có `license_rules`, chưa có source mới,
không source nào active/approved và mọi row vẫn là legacy `metadata_only`. Khi đã
có governance evidence, rollback từ chối phá dữ liệu; dùng compatibility hoặc
roll-forward recovery.

Migration/rollback vẫn cần exact live approval riêng. Package này không tự apply.
