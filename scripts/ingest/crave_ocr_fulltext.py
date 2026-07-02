#!/usr/bin/env python3
"""OCR toàn trang → text sạch + chunks, cho tài liệu có text-layer hỏng (font mã hoá).
Đa engine: Apple Vision (nội dung chính, on-device) + RapidOCR (kiểm chứng đồng thuận).
Xuất chunks JSON sẵn để embed + accession. Dùng lại hàm của crave_scan_gate.
"""
import json
import sys
import tempfile
from pathlib import Path

import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crave_scan_gate import (  # type: ignore
    compile_vision_tool, render_page_png, run_apple_vision, run_rapidocr,
    similarity, sha256_text,
)

CHUNK_SIZE = 1500
OVERLAP = 200


def chunk_text(text: str) -> list[dict]:
    chunks, idx, start = [], 0, 0
    pages = text.split("\f")
    ci = 0
    for pnum, page in enumerate(pages, start=1):
        pt = page.strip()
        if not pt:
            continue
        start = 0
        while start < len(pt):
            end = min(start + CHUNK_SIZE, len(pt))
            if end < len(pt):
                bp = max(pt.rfind(". ", start, end), pt.rfind("\n", start, end))
                if bp > start + CHUNK_SIZE * 0.5:
                    end = bp + 1
            ct = pt[start:end].strip()
            if ct:
                chunks.append({"content": ct, "chunk_index": ci, "page_number": pnum,
                               "content_tokens": (len(ct) + 2) // 3})
                ci += 1
            if end >= len(pt):
                break
            start = end - OVERLAP
    return chunks


def main() -> None:
    pdf_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else pdf_path.with_suffix(".ocr.json")
    languages = "en-US,vi-VN"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        vision_bin = tmp / "vision_ocr"
        compile_vision_tool(vision_bin)
        doc = pdfium.PdfDocument(str(pdf_path))
        n = len(doc)
        page_texts, sims = [], []
        for i in range(n):
            img = render_page_png(doc, i, 300, tmp / f"p{i}.png")
            apple = run_apple_vision(vision_bin, img, languages)
            rapid = run_rapidocr(img)
            sim = similarity(apple["text"], rapid["text"])
            sims.append(sim)
            # Apple Vision = nội dung (chính xác cho bản in); RapidOCR = đồng thuận
            page_texts.append(apple["text"].strip())
            print(f"page {i+1}/{n}: apple {apple['word_count']}w, rapid {rapid['word_count']}w, consensus {sim:.3f}", flush=True)
        full = "\f".join(page_texts)
        chunks = chunk_text(full)
        avg_sim = round(sum(sims) / len(sims), 4) if sims else 0.0
        # readability
        low = full[:8000].lower()
        en = sum(low.count(w) for w in [" the ", " and ", " of ", " to ", " for ", " is ", " process "])
        result = {
            "pdf": str(pdf_path), "pages": n, "full_text_len": len(full),
            "avg_consensus": avg_sim, "readable_score": en,
            "chunk_count": len(chunks), "content_sha256": sha256_text(full),
            "sample": full[:300], "chunks": chunks,
        }
        out_path.write_text(json.dumps(result, ensure_ascii=False))
        print(f"OK: {n} pages, {len(chunks)} chunks, consensus {avg_sim}, readable {en}, len {len(full)}")
        print(f"sample: {full[:200]!r}")


if __name__ == "__main__":
    main()
