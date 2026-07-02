#!/usr/bin/env python3
"""CRAVE — Nối gate local → webhook AL Vision Panel (khép kín pipeline, kèm JWT).

Đọc report của `crave_scan_gate.py`, với mỗi trang trạng thái AL_ADJUDICATION:
  1) render trang từ PDF (pypdfium2, JPEG ~90 DPI, nhẹ),
  2) POST tới webhook AL kèm `Authorization: Bearer <JWT>` (JWT Cách B),
  3) AL panel (Gemini+Groq+HF) phán xử → ghi scan_flag_queue → chờ người duyệt.

JWT lấy theo thứ tự:
  - env `CRAVE_AL_JWT` (access_token Supabase có sẵn), HOẶC
  - đăng nhập bằng env `CRAVE_AL_EMAIL` + `CRAVE_AL_PASSWORD`
    (POST /auth/v1/token?grant_type=password, apikey anon public-safe).

Không nhúng secret: chỉ dùng anon key (public-safe) + token/mật khẩu từ ENV.
Chạy: ./.venv-scan/bin/python scripts/ingest/crave_al_submit.py <report.json> <pdf> [--url ...]
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

SUPABASE_URL = os.environ.get("CRAVE_SUPABASE_URL", "https://bdttccztjtrcaztjgkot.supabase.co")
# Anon key public-safe (đã dùng ở frontend/WF-14). Chỉ để gọi /auth/v1 + apikey header.
ANON_KEY = os.environ.get(
    "CRAVE_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJkdHRjY3p0anRyY2F6dGpna290Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI0Nzc3MDAsImV4cCI6MjA5ODA1MzcwMH0."
    "27_xCRuqqW1wUGtLzMYac0YFlG8aOMO5Mem5LZCbZI8",
)
DEFAULT_WEBHOOK = os.environ.get("CRAVE_AL_WEBHOOK", "https://n8n.cpc1hn.com/webhook/crave-al-vision")
RENDER_DPI = 90
# Cloudflare trước n8n chặn UA lạ (error 1010) → giả UA trình duyệt.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def get_jwt() -> str | None:
    token = os.environ.get("CRAVE_AL_JWT")
    if token:
        return token.strip()
    email = os.environ.get("CRAVE_AL_EMAIL")
    password = os.environ.get("CRAVE_AL_PASSWORD")
    if not (email and password):
        return None
    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        data=body, method="POST",
        headers={"Content-Type": "application/json", "apikey": ANON_KEY, "User-Agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            return data.get("access_token")
    except urllib.error.HTTPError as e:
        print(f"[login] HTTP {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return None


def render_page_jpeg_b64(pdf_path: Path, page_1based: int, dpi: int = RENDER_DPI) -> str:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf_path))
    page = doc[page_1based - 1]
    img = page.render(scale=dpi / 72.0).to_pil().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    return base64.b64encode(buf.getvalue()).decode()


def post_al(url: str, jwt: str, payload: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {jwt}", "User-Agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> int:
    ap = argparse.ArgumentParser(description="Submit AL pages to webhook (JWT Cách B)")
    ap.add_argument("report", type=Path, help="report JSON của crave_scan_gate.py")
    ap.add_argument("pdf", type=Path, help="PDF gốc để render trang AL")
    ap.add_argument("--url", default=DEFAULT_WEBHOOK)
    args = ap.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    al_pages = report.get("al_pages", [])
    if not al_pages:
        print("Không có trang AL nào cần gửi.")
        return 0

    jwt = get_jwt()
    if not jwt:
        print(
            "THIẾU JWT: đặt env CRAVE_AL_JWT=<access_token>, hoặc "
            "CRAVE_AL_EMAIL + CRAVE_AL_PASSWORD (tài khoản service của gate).",
            file=sys.stderr,
        )
        return 2

    code = report.get("document_code", "")
    sha = report.get("source_sha256")
    # Lấy preview OCR/số lệch từ page_records để AL đối chiếu.
    prec = {r["page_1based"]: r for r in report.get("page_records", [])}
    ok = 0
    for pg in al_pages:
        rec = prec.get(pg, {})
        last = (rec.get("rounds") or [{}])[-1]
        engines = {e.get("engine"): e for e in last.get("engines", [])}
        disputed = []
        for c in last.get("comparisons", []):
            if c.get("pair") == "apple_vision~rapidocr":
                disputed = c.get("numeric_symmetric_diff", [])
        payload = {
            "document_code": code, "source_sha256": sha, "page_number": pg,
            "image_mime": "image/jpeg",
            "image_b64": render_page_jpeg_b64(args.pdf, pg),
            "apple_text": (engines.get("apple_vision") or {}).get("preview", ""),
            "rapid_text": (engines.get("rapidocr") or {}).get("preview", ""),
            "disputed_numbers": disputed,
        }
        status, resp = post_al(args.url, jwt, payload)
        print(f"page {pg}: HTTP {status} — {resp[:240]}")
        if status == 200:
            ok += 1
    print(f"Đã gửi {ok}/{len(al_pages)} trang AL thành công.")
    return 0 if ok == len(al_pages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
