#!/usr/bin/env python3
"""CRAVE — Cổng quét đa engine ĐỘC LẬP + thang retry/AL, TRƯỚC KHI DUYỆT.

Hiện thực `docs/governance/high-accuracy-ensemble-policy.md` cho lane nạp tài liệu:

  [1] Quét đa engine SONG SONG, ĐỘC LẬP (khác nhà → khác kiểu lỗi):
        - native  : PDF text-layer (pypdfium2)          — neo born-digital
        - apple   : Apple Vision OCR (on-device, riêng tư)
        - rapidocr: RapidOCR/PP-OCR (ONNX, khác nhà Apple) — độc lập thật
  [2] Tổng hợp: similarity ≥ ngưỡng + số/đơn vị khớp tuyệt đối (numeric-aware).
  [3] Chưa đạt ⇒ RETRY tăng DPI (300→400→600) / (chỗ để thêm engine).
  [4] Hết thang vẫn lệch ⇒ AL_ADJUDICATION: chuyển panel AL so BẢN GỐC (n8n
      MoA free-vision) + human — KHÔNG auto-approve tại đây.
  [5] Human duyệt (ngoài script). Mọi record: human_approved=false.

Cấm coi hai pass CÙNG một engine là hai phiếu độc lập. OCR chạy on-device/local,
không upload nội dung GMP lên cloud. Không ghi Supabase/n8n.
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
GATE = "CRAVE_SCAN_GATE_V2"
SCHEMA_VERSION = 2

# Ngưỡng đồng thuận (bảo thủ theo A26).
MIN_OCR_WORDS = 8            # dưới mức này coi như trang gần trống
MIN_SIMILARITY = 0.90        # tương đồng chuỗi tối thiểu giữa 2 engine ĐỘC LẬP
MAX_NUM_DELTA = 0            # số/đơn vị tới hạn phải khớp tuyệt đối
NATIVE_TEXT_MIN_CHARS = 40   # coi là có text-layer khi vượt mức này
DPI_LADDER = (300, 400, 600)  # [3] tăng chất lượng khi chưa đồng thuận

TOKEN_RE = re.compile(r"[^\W\d_]+|\d+(?:[.,]\d+)*", re.UNICODE)
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
    return re.sub(r"\s+", " ", value).strip()


def numeric_tokens(value: str) -> set[str]:
    out: set[str] = set()
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


def compare(a_text: str, b_text: str) -> dict[str, Any]:
    sim = similarity(a_text, b_text)
    diff = sorted(numeric_tokens(a_text) ^ numeric_tokens(b_text))
    return {
        "similarity": round(sim, 4),
        "numeric_symmetric_diff": diff[:20],
        "numeric_disagreements": len(diff),
        "agree": sim >= MIN_SIMILARITY and len(diff) <= MAX_NUM_DELTA,
    }


# --------------------------------------------------------------------------- #
# Engines (độc lập)
# --------------------------------------------------------------------------- #
def compile_vision_tool(output_path: Path) -> dict[str, Any]:
    clang = shutil.which("clang")
    if not clang:
        raise RuntimeError("clang không khả dụng; không compile được Apple Vision OCR.")
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
    return {"compiler": clang, "source_sha256": sha256_file(VISION_SOURCE),
            "binary_sha256": sha256_file(output_path)}


def render_page_png(document: "pdfium.PdfDocument", page_index: int, dpi: int, out: Path) -> Path:
    page = document[page_index]
    image = page.render(scale=dpi / 72.0, rotation=0).to_pil().convert("RGB")
    image.save(out, format="PNG")
    return out


def native_text(document: "pdfium.PdfDocument", page_index: int) -> str:
    textpage = document[page_index].get_textpage()
    try:
        return textpage.get_text_range() or ""
    finally:
        textpage.close()


def run_apple_vision(executable: Path, image_path: Path, languages: str) -> dict[str, Any]:
    command = [str(executable), str(image_path), "accurate", languages]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Apple Vision lỗi: {(completed.stderr or completed.stdout).strip()}")
    payload = json.loads(completed.stdout)
    return {
        "engine": "apple_vision", "text": str(payload.get("text", "")),
        "word_count": int(payload.get("word_count") or 0),
        "mean_confidence": round(float(payload.get("mean_confidence") or 0.0), 6),
    }


_RAPID_ENGINE = None


def run_rapidocr(image_path: Path) -> dict[str, Any]:
    global _RAPID_ENGINE
    if _RAPID_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR  # lazy: model load chậm
        _RAPID_ENGINE = RapidOCR()
    result, _ = _RAPID_ENGINE(str(image_path))
    lines = result or []
    # Sắp theo thứ tự đọc (trên→dưới) rồi ghép.
    ordered = sorted(lines, key=lambda ln: (round(min(p[1] for p in ln[0]) / 20), min(p[0] for p in ln[0])))
    text = "\n".join(str(ln[1]) for ln in ordered)
    confs = [float(ln[2]) for ln in lines if len(ln) > 2]
    return {
        "engine": "rapidocr", "text": text,
        "word_count": len(text.split()),
        "mean_confidence": round(sum(confs) / len(confs), 6) if confs else 0.0,
    }


# --------------------------------------------------------------------------- #
# Quyết định 1 vòng (1 mức DPI)
# --------------------------------------------------------------------------- #
def decide_round(native: str, apple: dict[str, Any], rapid: dict[str, Any]) -> dict[str, Any]:
    native_present = len(normalize(native)) >= NATIVE_TEXT_MIN_CHARS
    ocr_ready = [e for e in (apple, rapid) if e["word_count"] >= MIN_OCR_WORDS]

    comparisons: list[dict[str, Any]] = []
    # [2] hai engine OCR ĐỘC LẬP đối chiếu (apple vs rapid) — cross-check ảnh scan.
    ocr_agree = False
    if apple["word_count"] >= MIN_OCR_WORDS and rapid["word_count"] >= MIN_OCR_WORDS:
        c = {"pair": "apple_vision~rapidocr", **compare(apple["text"], rapid["text"])}
        comparisons.append(c)
        ocr_agree = c["agree"]
    # native neo với OCR tốt nhất (khi có text-layer).
    native_ocr_agree = False
    if native_present and ocr_ready:
        best = max(ocr_ready, key=lambda e: e["word_count"])
        c = {"pair": f'native~{best["engine"]}', **compare(native, best["text"])}
        comparisons.append(c)
        native_ocr_agree = c["agree"]

    if native_present and (native_ocr_agree or not ocr_ready):
        status = "PASS_CANDIDATE"
    elif not native_present and ocr_agree:
        status = "OCR_CONSENSUS_CANDIDATE"
    elif not native_present and not ocr_ready:
        status = "FAIL_EXTRACT"
    else:
        status = "RETRY"  # còn dư địa tăng DPI/đổi cách
    return {"native_present": native_present, "comparisons": comparisons, "status": status}


TERMINAL_PASS = {"PASS_CANDIDATE", "OCR_CONSENSUS_CANDIDATE"}


# --------------------------------------------------------------------------- #
# Driver: thang [1]→[3], hết thang → [4] AL
# --------------------------------------------------------------------------- #
def scan_page(document, page_index, vision_bin, languages, tmp_dir) -> dict[str, Any]:
    native = native_text(document, page_index)
    rounds: list[dict[str, Any]] = []
    final_status = "FAIL_EXTRACT"
    for dpi in DPI_LADDER:
        img = render_page_png(document, page_index, dpi, tmp_dir / f"p{page_index}_{dpi}.png")
        apple = run_apple_vision(vision_bin, img, languages)
        rapid = run_rapidocr(img)
        img.unlink(missing_ok=True)
        decision = decide_round(native, apple, rapid)
        rounds.append({
            "dpi": dpi,
            "engines": [
                {"engine": "native", "word_count": len(native.split()),
                 "mean_confidence": 1.0 if native.strip() else 0.0,
                 "preview": " ".join(native.split())[:140], "text_sha256": sha256_text(native)},
                {"engine": "apple_vision", "word_count": apple["word_count"],
                 "mean_confidence": apple["mean_confidence"],
                 "preview": " ".join(apple["text"].split())[:140], "text_sha256": sha256_text(apple["text"])},
                {"engine": "rapidocr", "word_count": rapid["word_count"],
                 "mean_confidence": rapid["mean_confidence"],
                 "preview": " ".join(rapid["text"].split())[:140], "text_sha256": sha256_text(rapid["text"])},
            ],
            "comparisons": decision["comparisons"],
            "native_present": decision["native_present"],
            "status": decision["status"],
        })
        final_status = decision["status"]
        if final_status in TERMINAL_PASS or final_status == "FAIL_EXTRACT":
            break  # đạt (hoặc không trích được) → dừng thang
        # RETRY → tăng DPI vòng sau
    else:
        # Hết thang mà vẫn RETRY ⇒ [4] AL adjudication so bản gốc.
        final_status = "AL_ADJUDICATION"
    if final_status == "RETRY":
        final_status = "AL_ADJUDICATION"
    return {"page_1based": page_index + 1, "rounds": rounds, "status": final_status,
            "al_required": final_status == "AL_ADJUDICATION"}


def sample_pages(total: int, requested: str | None) -> list[int]:
    if requested:
        idx = sorted({int(x) - 1 for x in requested.split(",") if x.strip()})
        return [i for i in idx if 0 <= i < total]
    if total <= 5:
        return list(range(total))
    return sorted({0, total // 4, total // 2, (3 * total) // 4, total - 1})


def scan_pdf(pdf_path: Path, document_code: str, languages: str, pages_arg: str | None) -> dict[str, Any]:
    document = pdfium.PdfDocument(str(pdf_path))
    total = len(document)
    pages = sample_pages(total, pages_arg)
    with tempfile.TemporaryDirectory(prefix="crave_scan_") as tmp:
        tmp_dir = Path(tmp)
        vision_bin = tmp_dir / "vision_ocr"
        compiler_evidence = compile_vision_tool(vision_bin)
        page_records = [scan_page(document, i, vision_bin, languages, tmp_dir) for i in pages]

    order = ["FAIL_EXTRACT", "AL_ADJUDICATION", "NEEDS_HUMAN_REVIEW",
             "OCR_CONSENSUS_CANDIDATE", "PASS_CANDIDATE"]
    statuses = [r["status"] for r in page_records] or ["FAIL_EXTRACT"]
    doc_status = min(statuses, key=lambda s: order.index(s) if s in order else 0)
    return {
        "gate": GATE, "schema_version": SCHEMA_VERSION,
        "policy": "docs/governance/high-accuracy-ensemble-policy.md",
        "document_code": document_code, "source_file": pdf_path.name,
        "source_sha256": sha256_file(pdf_path),
        "page_count": total, "sampled_pages": [p + 1 for p in pages],
        "compiler_evidence": compiler_evidence,
        "engines_independent": ["pdf_text_layer(pypdfium2)", "apple_vision(on-device)", "rapidocr(onnx)"],
        "dpi_ladder": list(DPI_LADDER),
        "page_records": page_records,
        "document_review_status": doc_status,
        "al_pages": [r["page_1based"] for r in page_records if r["status"] == "AL_ADJUDICATION"],
        "human_approved": False, "ai_use_allowed": False, "remote_mutation_allowed": False,
        "note": (
            "Đa engine độc lập → tổng hợp numeric-aware → retry tăng DPI → AL so bản gốc → "
            "human duyệt. Không auto-approve. OCR on-device, không upload GMP lên cloud."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CRAVE multi-engine scan-before-approve gate v2")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--code", required=True)
    parser.add_argument("--languages", default="vi,en")
    parser.add_argument("--pages", default=None, help="1-based CSV, vd '1,7,12'")
    parser.add_argument("--out", type=Path, default=None)
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
