#!/usr/bin/env python3
"""CRAVE — Cổng quét đa engine TRƯỚC KHI DUYỆT (scan-before-approve gate).

Hợp nhất phương pháp đa engine đã định (R05-A06/A26/A29) thành một cổng chạy
được, dùng cho MỌI tài liệu trước khi accession vào corpus:

  1) Render trang bằng pypdfium2 (local, không cần poppler).
  2) Chạy nhiều "hình thức quét" độc lập trên mỗi trang mẫu:
       - native  : text-layer của PDF (pypdfium2.get_textpage)
       - vision_accurate : Apple Vision OCR (accurate) — on-device, riêng tư
       - vision_fast     : Apple Vision OCR (fast)     — pass thứ hai để đối chiếu
     (Tesseract/RapidOCR/MinerU có thể cắm thêm sau — cùng schema record.)
  3) Đồng thuận có trọng số số/đơn vị (numeric/unit-aware) giữa các engine.
  4) Kết luận trạng thái review, KHÔNG BAO GIỜ auto-approve:
       - PASS_CANDIDATE           : có text-layer + OCR đồng thuận
       - OCR_CONSENSUS_CANDIDATE  : ảnh scan; ≥2 pass OCR đồng thuận
       - NEEDS_HUMAN_REVIEW       : bất đồng / confidence thấp
       - FAIL_EXTRACT             : không trích được nội dung
  Mọi record: human_approved=false, ai_use_allowed=false, remote_mutation=false.

Không upload nội dung GMP lên cloud (OCR chạy local). Không ghi Supabase/n8n.
Bước accession chỉ được chạy sau khi con người duyệt record trong hàng đợi.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]  # scripts/ingest/<file> -> repo root
VISION_SOURCE = ROOT / "scripts/r05_a26_macos_vision_ocr.m"
GATE = "CRAVE_SCAN_GATE_V1"
SCHEMA_VERSION = 1

# Ngưỡng đồng thuận (giữ bảo thủ như A26).
MIN_OCR_WORDS = 8          # dưới mức này coi như trang gần trống
MIN_SIMILARITY = 0.90      # tương đồng chuỗi tối thiểu giữa 2 engine
MAX_NUM_DELTA = 0          # số/đơn vị tới hạn phải khớp tuyệt đối
NATIVE_TEXT_MIN_CHARS = 40  # native text-layer coi là "có" khi vượt mức này

PASS_SPECS = (
    {"pass_id": "native", "engine": "pdf_text_layer", "dpi": 0, "mode": "native"},
    {"pass_id": "vision_accurate", "engine": "apple_vision", "dpi": 300, "mode": "accurate"},
    {"pass_id": "vision_fast", "engine": "apple_vision", "dpi": 200, "mode": "fast"},
)

TOKEN_RE = re.compile(r"[^\W\d_]+|\d+(?:[.,]\d+)*", re.UNICODE)
# Số kèm đơn vị/ký hiệu tới hạn GMP (m/s, µm, Pa, %, °C, ISO class ...).
NUMERIC_RE = re.compile(
    r"[+-]?\d+(?:[.,]\d+)*\s?(?:%|°?[CF]\b|µm|um|nm|mm|cm|m/s|m3|m³|Pa|kPa|ppm|"
    r"CFU|cfu|h\b|min\b|s\b|mL|ml|L\b|kg|g\b|mg|µg)?",
    re.IGNORECASE,
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def tokens(value: str) -> list[str]:
    return TOKEN_RE.findall(normalize(value))


def numeric_tokens(value: str) -> set[str]:
    out = set()
    for match in NUMERIC_RE.findall(value or ""):
        token = re.sub(r"\s+", "", match).casefold()
        if any(ch.isdigit() for ch in token):
            out.add(token)
    return out


def similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


# --------------------------------------------------------------------------- #
# Engines
# --------------------------------------------------------------------------- #
def compile_vision_tool(output_path: Path) -> dict[str, Any]:
    clang = shutil.which("clang")
    if not clang:
        raise RuntimeError("clang không khả dụng; không compile được Vision OCR.")
    if not VISION_SOURCE.is_file():
        raise RuntimeError(f"Thiếu nguồn Vision OCR: {VISION_SOURCE}")
    command = [
        clang, "-fobjc-arc",
        "-framework", "Foundation", "-framework", "Vision",
        "-framework", "ImageIO", "-framework", "CoreGraphics",
        str(VISION_SOURCE), "-o", str(output_path),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Compile Vision OCR lỗi: {completed.stderr.strip()}")
    return {
        "compiler": clang,
        "source_sha256": sha256_file(VISION_SOURCE),
        "binary_sha256": sha256_file(output_path),
    }


def render_page_png(document: "pdfium.PdfDocument", page_index: int, dpi: int, out: Path) -> Path:
    page = document[page_index]
    bitmap = page.render(scale=dpi / 72.0, rotation=0)
    image = bitmap.to_pil().convert("RGB")
    image.save(out, format="PNG")
    return out


def native_text(document: "pdfium.PdfDocument", page_index: int) -> str:
    textpage = document[page_index].get_textpage()
    try:
        return textpage.get_text_range() or ""
    finally:
        textpage.close()


def run_vision(executable: Path, image_path: Path, mode: str, languages: str) -> dict[str, Any]:
    command = [str(executable), str(image_path), mode, languages]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Vision {mode} lỗi: {(completed.stderr or completed.stdout).strip()}")
    payload = json.loads(completed.stdout)
    return {
        "text": str(payload.get("text", "")),
        "char_count": int(payload.get("char_count") or 0),
        "word_count": int(payload.get("word_count") or 0),
        "mean_confidence": round(float(payload.get("mean_confidence") or 0.0), 6),
    }


# --------------------------------------------------------------------------- #
# Consensus
# --------------------------------------------------------------------------- #
def compare_pass_pair(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    sim = similarity(a["text"], b["text"])
    num_a, num_b = numeric_tokens(a["text"]), numeric_tokens(b["text"])
    num_missing = sorted((num_a ^ num_b))
    return {
        "pair": f'{a["pass_id"]}~{b["pass_id"]}',
        "similarity": round(sim, 4),
        "numeric_symmetric_diff": num_missing[:20],
        "numeric_disagreements": len(num_missing),
        "agree": sim >= MIN_SIMILARITY and len(num_missing) <= MAX_NUM_DELTA,
    }


def decide_page(passes: list[dict[str, Any]]) -> dict[str, Any]:
    native = next((p for p in passes if p["pass_id"] == "native"), None)
    ocr = [p for p in passes if p["engine"] == "apple_vision"]
    native_present = bool(native) and len(normalize(native["text"])) >= NATIVE_TEXT_MIN_CHARS
    ocr_present = [p for p in ocr if p["word_count"] >= MIN_OCR_WORDS]

    comparisons: list[dict[str, Any]] = []
    # OCR pass đối chiếu nhau (cross-check cho ảnh scan).
    for i in range(len(ocr_present)):
        for j in range(i + 1, len(ocr_present)):
            comparisons.append(compare_pass_pair(ocr_present[i], ocr_present[j]))
    # Native đối chiếu OCR tốt nhất (khi có text-layer).
    if native_present and ocr_present:
        best = max(ocr_present, key=lambda p: p["word_count"])
        comparisons.append(compare_pass_pair(native, best))

    ocr_pair_agree = [c for c in comparisons if "~vision" in c["pair"] or c["pair"].startswith("vision")]
    ocr_consensus = any(c["agree"] for c in ocr_pair_agree if "native" not in c["pair"])
    native_ocr_agree = any(c["agree"] for c in comparisons if "native" in c["pair"])

    if native_present and (native_ocr_agree or not ocr_present):
        status = "PASS_CANDIDATE"
    elif not native_present and ocr_present and ocr_consensus:
        status = "OCR_CONSENSUS_CANDIDATE"
    elif not native_present and not ocr_present:
        status = "FAIL_EXTRACT"
    else:
        status = "NEEDS_HUMAN_REVIEW"

    return {
        "native_present": native_present,
        "ocr_pass_count": len(ocr_present),
        "comparisons": comparisons,
        "status": status,
    }


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def sample_pages(total: int, requested: str | None) -> list[int]:
    if requested:
        idx = sorted({int(x) - 1 for x in requested.split(",") if x.strip()})
        return [i for i in idx if 0 <= i < total]
    if total <= 5:
        return list(range(total))
    # Đầu / giữa / cuối để lấy mẫu đại diện.
    return sorted({0, total // 4, total // 2, (3 * total) // 4, total - 1})


def scan_pdf(pdf_path: Path, document_code: str, languages: str, pages_arg: str | None) -> dict[str, Any]:
    document = pdfium.PdfDocument(str(pdf_path))
    total = len(document)
    pages = sample_pages(total, pages_arg)

    with tempfile.TemporaryDirectory(prefix="crave_scan_") as tmp:
        tmp_dir = Path(tmp)
        vision_bin = tmp_dir / "vision_ocr"
        compiler_evidence = compile_vision_tool(vision_bin)

        page_records: list[dict[str, Any]] = []
        for page_index in pages:
            passes: list[dict[str, Any]] = []
            # Engine 1: native text-layer
            ntext = native_text(document, page_index)
            passes.append({
                "pass_id": "native", "engine": "pdf_text_layer", "dpi": 0, "mode": "native",
                "text": ntext, "char_count": len(ntext),
                "word_count": len(ntext.split()), "mean_confidence": 1.0 if ntext.strip() else 0.0,
                "text_sha256": sha256_text(ntext),
            })
            # Engine 2+3: Apple Vision (accurate 300dpi, fast 200dpi)
            for spec in PASS_SPECS:
                if spec["engine"] != "apple_vision":
                    continue
                img = render_page_png(document, page_index, spec["dpi"], tmp_dir / f"p{page_index}_{spec['pass_id']}.png")
                res = run_vision(vision_bin, img, spec["mode"], languages)
                img.unlink(missing_ok=True)
                passes.append({
                    "pass_id": spec["pass_id"], "engine": "apple_vision",
                    "dpi": spec["dpi"], "mode": spec["mode"],
                    "text": res["text"], "char_count": res["char_count"],
                    "word_count": res["word_count"], "mean_confidence": res["mean_confidence"],
                    "text_sha256": sha256_text(res["text"]),
                })
            decision = decide_page(passes)
            page_records.append({
                "page_1based": page_index + 1,
                "engines": [
                    {k: v for k, v in p.items() if k != "text"} | {"preview": " ".join(p["text"].split())[:160]}
                    for p in passes
                ],
                **decision,
            })

    statuses = [r["status"] for r in page_records]
    order = ["FAIL_EXTRACT", "NEEDS_HUMAN_REVIEW", "OCR_CONSENSUS_CANDIDATE", "PASS_CANDIDATE"]
    worst = min(statuses, key=lambda s: order.index(s)) if statuses else "FAIL_EXTRACT"
    doc_status = {
        "PASS_CANDIDATE": "PASS_CANDIDATE",
        "OCR_CONSENSUS_CANDIDATE": "OCR_CONSENSUS_CANDIDATE",
    }.get(worst, "NEEDS_HUMAN_REVIEW" if worst != "FAIL_EXTRACT" else "FAIL_EXTRACT")

    return {
        "gate": GATE,
        "schema_version": SCHEMA_VERSION,
        "document_code": document_code,
        "source_file": pdf_path.name,
        "source_sha256": sha256_file(pdf_path),
        "page_count": total,
        "sampled_pages": [p + 1 for p in pages],
        "compiler_evidence": compiler_evidence,
        "engines_used": ["pdf_text_layer", "apple_vision(accurate)", "apple_vision(fast)"],
        "page_records": page_records,
        "document_review_status": doc_status,
        "human_approved": False,
        "ai_use_allowed": False,
        "remote_mutation_allowed": False,
        "note": (
            "Không auto-approve. Chỉ con người duyệt mới được accession. "
            "OCR chạy on-device (Apple Vision), không upload nội dung GMP lên cloud."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CRAVE multi-engine scan-before-approve gate")
    parser.add_argument("pdf", type=Path, help="Đường dẫn PDF local")
    parser.add_argument("--code", required=True, help="document_code (vd LV-BSC-A2)")
    parser.add_argument("--languages", default="vi,en", help="OCR languages CSV")
    parser.add_argument("--pages", default=None, help="1-based CSV, vd '1,3,7'; mặc định lấy mẫu")
    parser.add_argument("--out", type=Path, default=None, help="Ghi report JSON ra file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.pdf.is_file():
        raise SystemExit(f"Thiếu PDF: {args.pdf}")
    report = scan_pdf(args.pdf, args.code, args.languages, args.pages)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
