# SOP: Chuyển SUPABASE_SERVICE_ROLE_KEY từ Variables sang Secrets

**Mã:** SOP-GITHUB-001
**Phiên bản:** 1.0 — 2026-06-28
**Owner:** Claude Code — Chat 02
**Lý do:** Service-role key trong GitHub Variables không được mã hóa và không bị mask trong log → lỗ hổng P0-A (nangcap.md).

---

## Tác động khi thực hiện

| Trước | Sau |
|-------|-----|
| `vars.SUPABASE_SERVICE_ROLE_KEY` | `secrets.SUPABASE_SERVICE_ROLE_KEY` |
| Không mask trong log | Tự động mask `***` trong mọi log |
| Visible với mọi repo member | Chỉ GitHub Actions runner đọc được |
| `eval.yml` dùng `vars.*` | `eval.yml` đã sửa sang `secrets.*` |

**Sau khi thực hiện:** `eval.yml` sẽ FAIL bước kiểm tra cho đến khi bạn thêm Secret (bước 2 bên dưới). Đây là hành vi đúng — tránh chạy với key cũ trong Variables.

---

## Bước thực hiện

### Bước 1 — Lấy service-role key hiện tại

1. Vào [Supabase Dashboard](https://supabase.com/dashboard) → Project `bdttccztjtrcaztjgkot`
2. **Settings → API**
3. Tìm mục **service_role** (secret key) → Copy giá trị

> ⚠ Key này có quyền bypass RLS. Không paste vào bất kỳ chat, issue, hay source code nào.

### Bước 2 — Thêm Secret trên GitHub

1. Vào repo `tienhoandhd-droid/Du_bao_thoi_tiet` → **Settings → Secrets and variables → Actions**
2. Tab **Secrets** → **New repository secret**
3. Name: `SUPABASE_SERVICE_ROLE_KEY`
4. Value: paste key từ bước 1
5. **Add secret**

### Bước 3 — Xóa khỏi Variables (sau khi Secret đã tạo)

1. Cùng trang Settings → tab **Variables**
2. Tìm `SUPABASE_SERVICE_ROLE_KEY` → **Delete**
3. Xác nhận xóa

> Chỉ xóa Variable SAU KHI đã tạo Secret thành công — tránh mất key giữa chừng.

### Bước 4 — Verify

1. Vào tab **Actions** → chọn **GMP Eval Harness — FTS Retrieval**
2. **Run workflow** (giữ nguyên giá trị mặc định)
3. Xác nhận:
   - Bước "Kiểm tra biến bắt buộc" PASS (không còn báo `vars.*`)
   - Curl request chạy không lộ key trong log (hiện `***`)
   - Kết quả eval PASS (Hit@5 ≥ 80%)

---

## Rollback

Nếu Secret bị nhập sai và cần sửa:
1. **Settings → Secrets → SUPABASE_SERVICE_ROLE_KEY → Update**
2. Paste lại key đúng → Save

Nếu cần rotate key hoàn toàn (key bị lộ):
1. Supabase Dashboard → Settings → API → **Reset service role key**
2. Copy key mới
3. Cập nhật GitHub Secret (bước 2 ở trên)
4. Ghi incident record vào `docs/governance/change-register.md`

---

## Lưu ý bảo mật

- Service-role key **bypass RLS** — không truyền về frontend, không hardcode trong source.
- Chỉ dùng trong GitHub Actions Secrets và n8n credential `GMP-check`.
- Rotate ngay nếu nghi ngờ bị lộ (không chờ xác nhận).
