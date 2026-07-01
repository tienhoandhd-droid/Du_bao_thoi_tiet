#!/usr/bin/env python3
"""Run Docling/TableFormer for R05-A08 one-page table benchmark."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--page", type=int, default=7)
    args = parser.parse_args()

    is_image = args.input.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    options.table_structure_options.mode = TableFormerMode.ACCURATE
    options.table_structure_options.do_cell_matching = True
    input_format = InputFormat.IMAGE if is_image else InputFormat.PDF
    format_option = ImageFormatOption(pipeline_options=options) if is_image else PdfFormatOption(pipeline_options=options)
    converter = DocumentConverter(format_options={input_format: format_option})

    started = time.monotonic()
    result = converter.convert(args.input, max_num_pages=1, max_file_size=10_000_000)
    tables = []
    for index, table in enumerate(result.document.tables, 1):
        dataframe = table.export_to_dataframe(doc=result.document)
        tables.append(
            {
                "index": index,
                "rows": int(dataframe.shape[0]),
                "columns": int(dataframe.shape[1]),
                "cells": dataframe.fillna("").astype(str).values.tolist(),
                "provenance": [item.model_dump(mode="json") for item in table.prov],
            }
        )

    payload = {
        "engine": "Docling/TableFormer",
        "engine_version": "docling-2.107.0",
        "mode": "accurate",
        "page": args.page,
        "source_type": "image" if is_image else "one_page_pdf",
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "table_count": len(tables),
        "tables": tables,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"table_count": len(tables), "shapes": [[t["rows"], t["columns"]] for t in tables]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
