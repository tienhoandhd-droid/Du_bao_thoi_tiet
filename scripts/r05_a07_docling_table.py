#!/usr/bin/env python3
"""Run Docling/TableFormer on a one-page derivative of approved PDF page 10."""

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
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    is_image = args.pdf.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    options.table_structure_options.mode = TableFormerMode.ACCURATE
    options.table_structure_options.do_cell_matching = True
    input_format = InputFormat.IMAGE if is_image else InputFormat.PDF
    format_option = (
        ImageFormatOption(pipeline_options=options)
        if is_image
        else PdfFormatOption(pipeline_options=options)
    )
    converter = DocumentConverter(format_options={input_format: format_option})

    started = time.monotonic()
    convert_options = {"max_num_pages": 1, "max_file_size": 10_000_000}
    if not is_image:
        convert_options["page_range"] = (1, 1)
    result = converter.convert(args.pdf, **convert_options)
    tables = []
    for index, table in enumerate(result.document.tables, 1):
        dataframe = table.export_to_dataframe(doc=result.document)
        provenance = [item.model_dump(mode="json") for item in table.prov]
        tables.append(
            {
                "index": index,
                "rows": int(dataframe.shape[0]),
                "columns": int(dataframe.shape[1]),
                "cells": dataframe.fillna("").astype(str).values.tolist(),
                "provenance": provenance,
            }
        )

    payload = {
        "engine": "Docling/TableFormer",
        "engine_version": "docling-2.107.0",
        "mode": "accurate",
        "source_type": "image" if is_image else "one_page_pdf",
        "page": 10,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "table_count": len(tables),
        "tables": tables,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
