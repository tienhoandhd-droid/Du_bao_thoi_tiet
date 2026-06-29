# Hợp đồng release manifest CRAVE

Release manifest cấp hệ thống là bằng chứng liên kết một release với Git,
Supabase, n8n, prompt, model và dataset eval. Manifest không phải lệnh triển khai
và không cấp quyền apply/import/publish.

## Trường bắt buộc

```json
{
  "manifestVersion": "1.0.0",
  "releaseId": "crave-YYYYMMDD-NN",
  "generatedAt": "2026-06-29T00:00:00Z",
  "project": "CRAVE GMP Validation Intelligence Platform",
  "git": {
    "sha": "40-hex-characters",
    "branch": "release/example"
  },
  "supabase": {
    "projectId": "bdttccztjtrcaztjgkot",
    "currentMigrationVersion": "022",
    "migrations": [
      {
        "version": "022",
        "up": "supabase/migrations/022_name.sql",
        "down": "supabase/rollbacks/022_name_down.sql",
        "upSha256": "64-hex-characters",
        "downSha256": "64-hex-characters"
      }
    ]
  },
  "n8n": {
    "expectedWorkflowCount": 14,
    "workflows": [
      {
        "workflowNumber": "01",
        "id": "n8n-workflow-id",
        "activeVersionId": "uuid",
        "file": "n8n/workflows/TKTL-WF-01-name.json",
        "sha256": "64-hex-characters"
      }
    ]
  },
  "prompts": [
    {
      "key": "answer-with-citation",
      "version": "1.0.0",
      "file": "prompts/answer-with-citation/v1.0.0.md",
      "sha256": "64-hex-characters"
    }
  ],
  "model": {
    "provider": "OpenAI",
    "name": "model-name",
    "version": "pinned-release-or-snapshot"
  },
  "dataset": {
    "name": "eval-dataset-name",
    "version": "1.0.0",
    "file": "eval/path/dataset.json",
    "sha256": "64-hex-characters"
  }
}
```

## Cổng kiểm soát

Validator `scripts/validate_release_manifest.py` từ chối release khi:

- Git SHA không phải SHA đầy đủ 40 ký tự hex.
- Migration thiếu file up/down, sai cặp số phiên bản hoặc sai SHA-256.
- Workflow thiếu file, trùng số/ID, sai số lượng kỳ vọng hoặc sai SHA-256.
- Prompt không nằm trong `prompts/<key>/vN[.N.N].md`, version không khớp tên
  file, thiếu file hoặc sai SHA-256.
- Model hoặc dataset không có version; dataset thiếu file hoặc sai SHA-256.
- Đường dẫn tuyệt đối, thoát khỏi repo hoặc trỏ vào symlink ra ngoài repo.
- Manifest hay artifact được khai báo có dấu hiệu chứa secret thật.

Thông báo secret chỉ nêu rule và đường dẫn, không in giá trị khớp. Placeholder
`REDACTED`, `PLACEHOLDER`, `YOUR_*`, `EXAMPLE` và dữ liệu fixture được phép nếu
không giống credential thật.

## Quan hệ với manifest Chat 04

`n8n/release-manifest.json` là manifest chuyên biệt ghi provenance và trạng thái
reconcile 14 workflow. Release manifest cấp hệ thống có thể tham chiếu các export
đó nhưng không ghi đè ý nghĩa hay schema của manifest Chat 04.

## Chạy kiểm tra

```bash
python3 scripts/validate_release_manifest.py --manifest path/to/release-manifest.json
python3 -m unittest scripts/test_release_manifest.py
```

Validator chỉ đọc file và phù hợp chạy trong GitHub Actions không có secret.
`scripts/scan_repository_secrets.py` bổ sung quét toàn cây để chặn file chưa được
khai báo trong manifest; báo lỗi chỉ chứa đường dẫn và tên rule.
