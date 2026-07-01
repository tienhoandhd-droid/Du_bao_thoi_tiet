#!/usr/bin/env python3
"""Build and inspect the isolated R05-A19 controlled draft PDF corpus.

The generated internal documents are review candidates, never authoritative
records. The official WHO TRS 996 PDF is copied byte-for-byte from an explicitly
provided local source. No network or remote-system operation is performed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output/pdf/r05_controlled_draft_corpus"
DEFAULT_MANIFEST = ROOT / "work/r05_a19_controlled_draft_corpus_manifest.csv"
DEFAULT_REPORT = ROOT / "work/r05_a19_controlled_draft_corpus_hash_parse_report.json"
DEFAULT_REVIEW = ROOT / "work/r05_a19_owner_review_queue.csv"

FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
FONT_ITALIC = Path("/System/Library/Fonts/Supplemental/Arial Italic.ttf")

STATUS_DRAFT = "AI_DRAFT_FOR_OWNER_REVIEW"
STATUS_OFFICIAL = "OFFICIAL_REFERENCE_PENDING_LICENSE_AND_OWNER_REVIEW"
AUTHORITATIVE_DENIAL = "DRAFT_NOT_APPROVED_FOR_GMP_USE"

EU_GMP = "https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en"
EU_ANNEX_11 = "https://health.ec.europa.eu/document/download/8d305550-dd22-4dad-8463-2ddb4a1345f1_en"
FDA_PROCESS_VALIDATION = "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/process-validation-general-principles-and-practices"
ICH_Q9 = "https://database.ich.org/sites/default/files/ICH_Q9-R1_Document_Step2_Guideline_2021_1118.pdf"
WHO_VALIDATION = "https://www.who.int/publications/m/item/trs1019-annex3"
WHO_TRS_996 = "https://www.who.int/publications-detail-redirect/WHO_TRS_996"


@dataclass(frozen=True)
class DraftSpec:
    code: str
    title: str
    owner: str
    purpose: str
    scope: str
    steps: tuple[str, ...]
    controls: tuple[str, ...]
    records: tuple[str, ...]
    references: tuple[tuple[str, str], ...]


SPECS = (
    DraftSpec(
        "GMP-SOP-001",
        "Quy trình Kiểm soát Sai lệch và CAPA",
        "QA",
        "Thiết lập luồng khai báo, kiểm soát tức thời, điều tra nguyên nhân, CAPA và kiểm tra hiệu lực có truy nguyên.",
        "Áp dụng cho sai lệch, OOS/OOT, khiếu nại, tự thanh tra và tín hiệu chất lượng có thể ảnh hưởng sản phẩm hoặc hệ thống GMP.",
        ("Khai báo và bảo toàn bằng chứng", "Kiểm soát tức thời", "Phân loại rủi ro", "Điều tra nguyên nhân", "Lập và phê duyệt CAPA", "Kiểm tra hiệu lực và đóng hồ sơ"),
        ("Không trì hoãn khai báo để chờ đủ thông tin.", "Phân loại phải dựa trên tác động đến bệnh nhân, sản phẩm và dữ liệu.", "Nguyên nhân gốc phải được chứng minh bằng bằng chứng, không chỉ ghi lỗi thao tác.", "CAPA phải có chủ sở hữu, hạn hoàn thành và tiêu chí hiệu lực được duyệt.", "Mọi gia hạn hoặc đóng hồ sơ cần QA phê duyệt."),
        ("Phiếu sai lệch", "Báo cáo điều tra", "Kế hoạch CAPA", "Biên bản kiểm tra hiệu lực"),
        (("ICH Q9(R1) Quality Risk Management", ICH_Q9), ("EU GMP Volume 4", EU_GMP)),
    ),
    DraftSpec(
        "GMP-SOP-002",
        "Hồ sơ Lô và Kiểm soát Tài liệu GMP",
        "QA",
        "Kiểm soát việc ban hành, ghi chép, rà soát, sửa lỗi, lưu trữ và thu hồi hồ sơ GMP theo nguyên tắc toàn vẹn dữ liệu.",
        "Áp dụng cho hồ sơ lô, biểu mẫu GMP, bản sao được kiểm soát, hồ sơ điện tử và tài liệu hướng dẫn công việc.",
        ("Soạn thảo và rà soát", "Phê duyệt trước ban hành", "Cấp phát bản kiểm soát", "Ghi chép đồng thời", "Rà soát và đối chiếu", "Lưu trữ, thu hồi và hủy"),
        ("Chỉ sử dụng phiên bản có hiệu lực.", "Sửa lỗi phải giữ được nội dung gốc, lý do, ngày và người sửa.", "Biểu mẫu trắng phải được kiểm soát và đối chiếu.", "Hồ sơ điện tử phải có quyền truy cập và audit trail phù hợp.", "Thời hạn lưu phải do QA và yêu cầu pháp lý xác nhận."),
        ("Danh mục tài liệu", "Sổ cấp phát", "Hồ sơ lô", "Biên bản thu hồi và hủy"),
        (("EU GMP Volume 4 - Chapter 4 Documentation", EU_GMP), ("WHO TRS 996 Annex 5", WHO_TRS_996)),
    ),
    DraftSpec(
        "GMP-SOP-003",
        "Kiểm soát Môi trường, Phòng Sạch và Thẩm định Vệ sinh",
        "QA/Microbiology",
        "Thiết lập chương trình kiểm soát nhiễm tích hợp cho khu vực sạch và hoạt động vệ sinh dựa trên quản lý rủi ro chất lượng.",
        "Áp dụng cho phân vùng sạch, luồng người và vật tư, giám sát môi trường, vệ sinh thiết bị dùng chung và xử lý excursion.",
        ("Xây dựng CCS", "Phân loại khu vực và luồng", "Lập kế hoạch giám sát", "Thực hiện vệ sinh và lấy mẫu", "Đánh giá xu hướng", "Điều tra excursion và CAPA"),
        ("Vị trí và tần suất lấy mẫu phải có cơ sở rủi ro.", "Giới hạn cảnh báo/hành động phải được QA phê duyệt từ dữ liệu và yêu cầu áp dụng.", "Phải đánh giá vi sinh phân lập khi cần.", "Cleaning validation phải liên kết thiết bị, sản phẩm và phương pháp lấy mẫu.", "Không tự điền giới hạn số học khi chưa có căn cứ được duyệt."),
        ("Kế hoạch CCS", "Phiếu giám sát môi trường", "Nhật ký vệ sinh", "Báo cáo xu hướng và excursion"),
        (("EU GMP Annex 1 - Manufacture of Sterile Medicinal Products", EU_GMP), ("ICH Q9(R1)", ICH_Q9)),
    ),
    DraftSpec(
        "GMP-SOP-004",
        "Kiểm soát Sản xuất: IPC, Lấy mẫu và Quản lý Kho",
        "Production/QA/QC",
        "Bảo đảm nguyên liệu, bán thành phẩm và thành phẩm được nhận diện, lấy mẫu, kiểm soát trong quá trình và bảo quản có truy nguyên.",
        "Áp dụng từ tiếp nhận, biệt trữ, lấy mẫu, cấp phát, sản xuất, IPC, line clearance đến lưu kho và vận chuyển.",
        ("Tiếp nhận và biệt trữ", "Lấy mẫu có kiểm soát", "Cấp phát và đối chiếu", "Thực hiện IPC", "Line clearance", "Bảo quản, FEFO và xử lý excursion"),
        ("Trạng thái vật tư phải rõ ràng và không thể nhầm lẫn.", "Kế hoạch lấy mẫu phải được phê duyệt theo rủi ro.", "IPC phải liên kết với hồ sơ lô và phương pháp đã duyệt.", "Line clearance phải hoàn tất trước khởi động lô mới.", "Excursion phải được cách ly và QA đánh giá trước quyết định sử dụng."),
        ("Phiếu tiếp nhận", "Phiếu lấy mẫu", "Hồ sơ IPC", "Checklist line clearance", "Báo cáo excursion"),
        (("EU GMP Volume 4 - Chapters 3, 5 and Annex 8", EU_GMP), ("ICH Q9(R1)", ICH_Q9)),
    ),
    DraftSpec(
        "GMP-SOP-005",
        "Hệ thống Máy tính GxP, Thẩm định và Độ Ổn định",
        "QA/IT/QC",
        "Quản lý vòng đời hệ thống máy tính GxP và dữ liệu độ ổn định theo mức độ rủi ro, toàn vẹn dữ liệu và truy nguyên quyết định.",
        "Áp dụng cho hệ thống tạo, xử lý, lưu hoặc báo cáo dữ liệu GxP và chương trình theo dõi độ ổn định liên quan.",
        ("Xác định URS và dữ liệu tới hạn", "Đánh giá nhà cung cấp và rủi ro", "Cấu hình và thẩm định", "Quản lý truy cập và audit trail", "Sao lưu, khôi phục và tính liên tục", "Change control, periodic review và OOT"),
        ("URS phải được chủ quy trình và QA phê duyệt.", "Quyền truy cập áp dụng least privilege và tài khoản cá nhân.", "Audit trail phải được bật, bảo vệ và rà soát theo rủi ro.", "Backup chỉ được coi là kiểm soát khi restore đã được thử nghiệm.", "OOT độ ổn định phải được điều tra và đánh giá tác động."),
        ("URS và ma trận truy nguyên", "Báo cáo thẩm định", "Danh sách quyền", "Biên bản audit-trail review", "Báo cáo OOT"),
        (("EU GMP Annex 11 - Computerised Systems", EU_ANNEX_11), ("WHO TRS 996 Annex 5", WHO_TRS_996)),
    ),
    DraftSpec(
        "GMP-SOP-006",
        "Thẩm định quy trình theo vòng đời - Process Validation Lifecycle (FDA 2011)",
        "Validation/QA/Production",
        "Quy định cách thiết kế, thẩm định và duy trì trạng thái kiểm soát của quy trình sản xuất trong toàn bộ vòng đời.",
        "Áp dụng cho quy trình thương mại mới, thay đổi đáng kể và chương trình continued process verification.",
        ("Stage 1 - Process Design", "Đánh giá sẵn sàng thiết bị và tiện ích", "Stage 2 - PPQ protocol", "Thực hiện PPQ và quản lý sai lệch", "Stage 3 - Continued Process Verification", "Đánh giá thay đổi và tái thẩm định"),
        ("CPP, CQA và control strategy phải có căn cứ khoa học.", "Số lô và kế hoạch lấy mẫu PPQ phải được biện minh, không dùng mặc định thiếu căn cứ.", "Sai lệch PPQ phải được đánh giá đối với tính hợp lệ của kết luận.", "Stage 3 phải có quy tắc phát hiện xu hướng và trách nhiệm phản ứng.", "Tái thẩm định được quyết định bằng change control và risk assessment."),
        ("Process development report", "PPQ protocol", "PPQ report", "CPV trend report", "Revalidation assessment"),
        (("FDA Process Validation Guidance, January 2011", FDA_PROCESS_VALIDATION), ("WHO TRS 1019 Annex 3", WHO_VALIDATION)),
    ),
    DraftSpec(
        "GMP-SOP-007",
        "Kiểm soát thống kê quy trình SPC và chỉ số năng lực Cpk",
        "QA/Statistics/Production",
        "Chuẩn hóa việc lựa chọn dữ liệu, biểu đồ kiểm soát, nhận diện tín hiệu và sử dụng chỉ số năng lực trong giám sát quy trình.",
        "Áp dụng cho dữ liệu CPV, IPC, QC và chỉ số quá trình được phê duyệt để phân tích thống kê.",
        ("Xác định mục tiêu và nguồn dữ liệu", "Xác nhận hệ thống đo và sampling", "Thiết lập baseline", "Áp dụng control chart", "Điều tra tín hiệu đặc biệt", "Đánh giá capability và xu hướng"),
        ("Không tính capability trước khi đánh giá tính ổn định thống kê.", "Giới hạn kiểm soát không thay thế specification.", "Loại dữ liệu phải có lý do, phê duyệt và audit trail.", "Quy tắc cảnh báo/hành động phải định trước.", "Mọi kết luận cần lưu tập dữ liệu, phiên bản công thức và người rà soát."),
        ("Data definition", "Biểu đồ kiểm soát", "Báo cáo capability", "Biên bản điều tra tín hiệu", "CPV report"),
        (("FDA Process Validation Guidance, January 2011", FDA_PROCESS_VALIDATION), ("ICH Q9(R1)", ICH_Q9)),
    ),
    DraftSpec(
        "GMP-SOP-008",
        "Thẩm định độ kín hệ bao bì - Container Closure Integrity CCI",
        "Packaging/Validation/QA",
        "Thiết lập chiến lược vòng đời để chứng minh hệ bao bì bảo vệ sản phẩm theo cấu hình và điều kiện sử dụng dự kiến.",
        "Áp dụng cho lựa chọn phương pháp CCI, thẩm định, transfer, kiểm soát thường quy, độ ổn định và thay đổi cấu hình bao bì.",
        ("Đánh giá rủi ro cấu hình bao bì", "Xác định mục tiêu và khuyết tật tới hạn", "Chọn phương pháp", "Thẩm định phương pháp", "Áp dụng trong vòng đời", "Đánh giá thay đổi và trend"),
        ("Phương pháp phải phù hợp sản phẩm và cấu hình thực tế.", "Mẫu kiểm soát hoặc khuyết tật chuẩn phải có truy nguyên.", "Tiêu chí phát hiện phải được phê duyệt từ dữ liệu thẩm định.", "Sample handling phải ngăn tạo sai lệch giả.", "Thay đổi stopper, vial, seal hoặc sterilization phải vào change control."),
        ("CCI risk assessment", "Method validation protocol", "Raw data", "Validation report", "Lifecycle monitoring report"),
        (("EU GMP Annex 1", EU_GMP), ("ICH Q9(R1)", ICH_Q9)),
    ),
    DraftSpec(
        "GMP-SOP-009",
        "Đảm bảo vô trùng và mô phỏng quy trình vô trùng - Media Fill APS",
        "Sterile Operations/Microbiology/QA",
        "Quy định việc thiết kế, thực hiện, đánh giá và điều tra APS như một phần của contamination control strategy.",
        "Áp dụng cho dây chuyền aseptic, ca làm việc, can thiệp thường quy/không thường quy và thay đổi có thể ảnh hưởng sterility assurance.",
        ("Xây dựng CCS và risk assessment", "Thiết kế APS worst case", "Chuẩn bị môi trường và điều kiện", "Thực hiện và ghi nhận can thiệp", "Ủ, kiểm tra và đối chiếu", "Điều tra contamination và quyết định tái thực hiện"),
        ("APS phải đại diện thao tác thực tế và điều kiện bất lợi hợp lý.", "Can thiệp phải được định nghĩa và ghi nhận có truy nguyên.", "Kết quả nghi ngờ hoặc contaminated unit phải được điều tra toàn diện.", "Không đặt tiêu chí số học khi chưa đối chiếu yêu cầu áp dụng và hồ sơ được duyệt.", "Tần suất phải xem xét rủi ro, thay đổi, lịch sử và yêu cầu quản lý."),
        ("APS protocol", "Intervention log", "Incubation record", "Inspection result", "Investigation and APS report"),
        (("EU GMP Annex 1", EU_GMP), ("ICH Q9(R1)", ICH_Q9)),
    ),
    DraftSpec(
        "GMP-SOP-010",
        "Vệ sinh cơ sở sản xuất GMP - Cleaning Schedule, Pest Control, Disinfectants",
        "Facilities/Production/QA",
        "Thiết lập chương trình vệ sinh cơ sở, kiểm soát côn trùng và sử dụng chất tẩy rửa/khử trùng có căn cứ rủi ro.",
        "Áp dụng cho khu vực GMP, bề mặt, thiết bị hỗ trợ, nhà thầu vệ sinh, hóa chất vệ sinh và hoạt động pest control.",
        ("Phân vùng và risk assessment", "Thiết lập cleaning schedule", "Phê duyệt phương pháp và hóa chất", "Thực hiện và xác nhận", "Pest control và contractor oversight", "Trend, deviation và cải tiến"),
        ("Tần suất phải liên kết cấp sạch, hoạt động và lịch sử.", "Nồng độ, thời gian tiếp xúc và tương thích bề mặt phải được QA phê duyệt.", "Disinfectant rotation cần biện minh khoa học, không luân phiên hình thức.", "Bẫy côn trùng không được tạo nguy cơ nhiễm cho khu vực.", "Nhà thầu phải được thẩm định, đào tạo và giám sát."),
        ("Cleaning master schedule", "Cleaning log", "Chemical preparation log", "Pest-control map/report", "Contractor training record"),
        (("EU GMP Volume 4", EU_GMP), ("EU GMP Annex 1", EU_GMP), ("ICH Q9(R1)", ICH_Q9)),
    ),
    DraftSpec(
        "VQ-QT-003",
        "Quy trình Thẩm định Thiết bị IQ/OQ/PQ",
        "Validation/Engineering/QA",
        "Quy định vòng đời qualification để chứng minh thiết bị và tiện ích phù hợp mục đích sử dụng trước và trong vận hành GMP.",
        "Áp dụng cho thiết bị, tiện ích và hệ thống có tác động trực tiếp hoặc gián tiếp đến chất lượng sản phẩm và dữ liệu GxP.",
        ("URS và đánh giá tác động", "DQ và supplier assessment", "IQ", "OQ", "PQ", "Traceability, deviation, release và requalification"),
        ("Phạm vi qualification phải dựa trên risk assessment.", "Mọi test case phải truy nguyên tới URS hoặc risk control.", "Thiết bị đo phải còn hiệu chuẩn trong khi thử nghiệm.", "Sai lệch phải được đóng hoặc đánh giá trước kết luận.", "Release for use cần QA phê duyệt; chữ ký trong draft này để trống."),
        ("URS", "Risk assessment", "DQ/IQ/OQ/PQ protocol", "Deviation log", "Summary report and release decision"),
        (("WHO TRS 1019 Annex 3", WHO_VALIDATION), ("EU GMP Annex 15", EU_GMP), ("ICH Q9(R1)", ICH_Q9)),
    ),
)


class InvariantCanvas(canvas.Canvas):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)


class ProcessFlow(Flowable):
    def __init__(self, labels: tuple[str, ...], width: float = 170 * mm) -> None:
        super().__init__()
        self.labels = labels[:6]
        self.width = width
        self.height = 48 * mm

    def draw(self) -> None:
        c = self.canv
        box_w = 50 * mm
        box_h = 13 * mm
        gap_x = 7 * mm
        row_y = (28 * mm, 5 * mm)
        c.setLineWidth(0.8)
        for idx, label in enumerate(self.labels):
            row = idx // 3
            col = idx % 3 if row == 0 else 5 - idx
            x = col * (box_w + gap_x)
            y = row_y[row]
            c.setFillColor(colors.HexColor("#EAF4F3"))
            c.setStrokeColor(colors.HexColor("#2D6A66"))
            c.roundRect(x, y, box_w, box_h, 2 * mm, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#173A38"))
            c.setFont("Arial", 7.2)
            words = label.split()
            midpoint = max(1, len(words) // 2)
            lines = (" ".join(words[:midpoint]), " ".join(words[midpoint:]))
            c.drawCentredString(x + box_w / 2, y + 7.3 * mm, lines[0][:34])
            if lines[1]:
                c.drawCentredString(x + box_w / 2, y + 3.8 * mm, lines[1][:34])
            if row == 0 and col < 2 and idx + 1 < len(self.labels):
                c.setStrokeColor(colors.HexColor("#55706F"))
                c.line(x + box_w, y + box_h / 2, x + box_w + gap_x - 2 * mm, y + box_h / 2)
                c.line(x + box_w + gap_x - 4 * mm, y + box_h / 2 + 1.5 * mm, x + box_w + gap_x - 2 * mm, y + box_h / 2)
                c.line(x + box_w + gap_x - 4 * mm, y + box_h / 2 - 1.5 * mm, x + box_w + gap_x - 2 * mm, y + box_h / 2)
            if row == 1 and col > 0 and idx + 1 < len(self.labels):
                c.setStrokeColor(colors.HexColor("#55706F"))
                c.line(x, y + box_h / 2, x - gap_x + 2 * mm, y + box_h / 2)
                c.line(x - gap_x + 4 * mm, y + box_h / 2 + 1.5 * mm, x - gap_x + 2 * mm, y + box_h / 2)
                c.line(x - gap_x + 4 * mm, y + box_h / 2 - 1.5 * mm, x - gap_x + 2 * mm, y + box_h / 2)
        if len(self.labels) > 3:
            c.setStrokeColor(colors.HexColor("#55706F"))
            x = 2 * (box_w + gap_x) + box_w / 2
            c.line(x, row_y[0], x, row_y[1] + box_h + 2 * mm)
            c.line(x, row_y[1] + box_h + 4 * mm, x - 1.5 * mm, row_y[1] + box_h + 2 * mm)
            c.line(x, row_y[1] + box_h + 4 * mm, x + 1.5 * mm, row_y[1] + box_h + 2 * mm)


def register_fonts() -> None:
    for path in (FONT_REGULAR, FONT_BOLD, FONT_ITALIC):
        if not path.exists():
            raise FileNotFoundError(f"Required font not found: {path}")
    pdfmetrics.registerFont(TTFont("Arial", str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_BOLD)))
    pdfmetrics.registerFont(TTFont("Arial-Italic", str(FONT_ITALIC)))


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("DraftTitle", parent=base["Title"], fontName="Arial-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#173A38"), alignment=TA_LEFT, spaceAfter=8),
        "subtitle": ParagraphStyle("DraftSubtitle", parent=base["BodyText"], fontName="Arial", fontSize=10, leading=14, textColor=colors.HexColor("#48615F"), spaceAfter=8),
        "h1": ParagraphStyle("DraftH1", parent=base["Heading1"], fontName="Arial-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#245D59"), spaceBefore=7, spaceAfter=5),
        "h2": ParagraphStyle("DraftH2", parent=base["Heading2"], fontName="Arial-Bold", fontSize=10.5, leading=13, textColor=colors.HexColor("#173A38"), spaceBefore=5, spaceAfter=3),
        "body": ParagraphStyle("DraftBody", parent=base["BodyText"], fontName="Arial", fontSize=9.2, leading=13.2, textColor=colors.HexColor("#243332"), alignment=TA_LEFT, spaceAfter=5),
        "small": ParagraphStyle("DraftSmall", parent=base["BodyText"], fontName="Arial", fontSize=7.4, leading=10, textColor=colors.HexColor("#405250")),
        "notice": ParagraphStyle("DraftNotice", parent=base["BodyText"], fontName="Arial-Bold", fontSize=10, leading=14, textColor=colors.HexColor("#8B1E1E"), alignment=TA_CENTER, borderColor=colors.HexColor("#C34A4A"), borderWidth=1, borderPadding=7, backColor=colors.HexColor("#FFF0F0"), spaceAfter=10),
    }


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(text).replace("\n", "<br/>"), style)


def draft_table(data: list[list[Any]], widths: list[float], header: bool = True) -> Table:
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands: list[tuple[Any, ...]] = [
        ("FONTNAME", (0, 0), (-1, -1), "Arial"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#8CA5A3")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D6A66")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ])
    table.setStyle(TableStyle(commands))
    return table


def page_decorator(spec: DraftSpec):
    def decorate(canv: canvas.Canvas, doc: SimpleDocTemplate) -> None:
        canv.saveState()
        canv.setTitle(f"{spec.code} - {spec.title}")
        canv.setAuthor("CRAVE Codex controlled draft generator")
        canv.setSubject(f"{STATUS_DRAFT} {AUTHORITATIVE_DENIAL}")
        canv.setKeywords(f"{spec.code}, CRAVE, controlled draft, owner review required")
        width, height = A4
        canv.setFillColor(colors.HexColor("#C53D3D"))
        canv.setFont("Arial-Bold", 8)
        canv.drawString(20 * mm, height - 13 * mm, f"{spec.code} | CONTROLLED DRAFT | OWNER REVIEW REQUIRED")
        canv.setStrokeColor(colors.HexColor("#AFC2C0"))
        canv.line(20 * mm, height - 15 * mm, width - 20 * mm, height - 15 * mm)
        canv.setFillColor(colors.HexColor("#657674"))
        canv.setFont("Arial", 7.5)
        canv.drawString(20 * mm, 10 * mm, AUTHORITATIVE_DENIAL)
        canv.drawRightString(width - 20 * mm, 10 * mm, f"Trang {doc.page}")
        canv.restoreState()
    return decorate


def build_draft_pdf(spec: DraftSpec, path: Path) -> None:
    s = styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=17 * mm,
        title=f"{spec.code} - {spec.title}",
        author="CRAVE Codex controlled draft generator",
        subject=f"{STATUS_DRAFT} {AUTHORITATIVE_DENIAL}",
    )
    story: list[Any] = []
    story.extend([
        Spacer(1, 9 * mm),
        p(spec.code, s["subtitle"]),
        p(spec.title, s["title"]),
        p("BẢN DỰ THẢO DO AI TẠO - CHƯA ĐƯỢC PHÊ DUYỆT - KHÔNG DÙNG ĐỂ THỰC HIỆN GMP", s["notice"]),
        draft_table([
            ["Trường kiểm soát", "Giá trị"],
            ["Mã tài liệu", spec.code],
            ["Phiên bản", "DRAFT-0.1"],
            ["Trạng thái máy", STATUS_DRAFT],
            ["Chủ sở hữu dự kiến", spec.owner],
            ["Ngày hiệu lực", "ĐỂ TRỐNG - CẦN CHỦ TÀI LIỆU PHÊ DUYỆT"],
            ["Thay thế phiên bản", "KHÔNG - đây là review candidate độc lập"],
        ], [50 * mm, 118 * mm]),
        p("1. Mục đích", s["h1"]),
        p(spec.purpose, s["body"]),
        p("2. Phạm vi", s["h1"]),
        p(spec.scope, s["body"]),
        p("3. Ràng buộc sử dụng", s["h1"]),
        p("Tài liệu này chỉ phục vụ kiểm thử corpus, hash, parse, bảng, hình và quy trình review của CRAVE. Mọi tiêu chí số học, tần suất, thời hạn, vai trò và biểu mẫu phải được SME/QA đối chiếu với quy định áp dụng và hệ thống chất lượng của cơ sở trước khi phê duyệt. AI không có quyền phê duyệt tài liệu GMP.", s["body"]),
        PageBreak(),
        p("4. Vai trò và trách nhiệm dự kiến", s["h1"]),
        draft_table([
            ["Vai trò", "Trách nhiệm dự kiến - cần xác nhận"],
            ["Chủ quy trình", "Cung cấp yêu cầu nghiệp vụ, dữ liệu nguồn và đánh giá khả thi."],
            ["SME", "Đối chiếu kỹ thuật, thuật ngữ, thông số và bằng chứng."],
            ["QA", "Rà soát GMP, risk control, biểu mẫu, hiệu lực và quyết định phê duyệt."],
            ["Người thực hiện", "Chỉ thực hiện sau đào tạo trên phiên bản đã phê duyệt."],
        ], [43 * mm, 125 * mm]),
        p("5. Luồng quy trình đề xuất", s["h1"]),
        p("Hình 1. Luồng xử lý review candidate", s["small"]),
        ProcessFlow(spec.steps),
        Spacer(1, 3 * mm),
    ])
    for index, step in enumerate(spec.steps, start=1):
        story.extend([
            p(f"5.{index} {step}", s["h2"]),
            p(f"Người thực hiện phải ghi nhận đầu vào, thời điểm, bằng chứng, quyết định và ngoại lệ của bước '{step}'. Trường bắt buộc, tiêu chí chấp nhận và thẩm quyền phê duyệt phải được chủ tài liệu xác nhận trước khi ban hành.", s["body"]),
        ])
    story.extend([
        PageBreak(),
        p("6. Kiểm soát trọng yếu", s["h1"]),
    ])
    for index, control in enumerate(spec.controls, start=1):
        story.append(p(f"6.{index} {control}", s["body"]))
    matrix: list[list[Any]] = [["Bước", "Bằng chứng tối thiểu", "Tiêu chí/Quyết định"]]
    for index, step in enumerate(spec.steps, start=1):
        matrix.append([
            p(f"{index}. {step}", s["small"]),
            p("Bản ghi có người, thời gian, nguồn dữ liệu và liên kết hồ sơ.", s["small"]),
            p("CẦN SME/QA XÁC NHẬN; không tự suy đoán giới hạn.", s["small"]),
        ])
    story.extend([
        p("7. Ma trận bằng chứng và quyết định", s["h1"]),
        draft_table(matrix, [54 * mm, 58 * mm, 56 * mm]),
        p("8. Hồ sơ phải lưu", s["h1"]),
        draft_table(
            [["Hồ sơ", "Chủ sở hữu", "Thời hạn lưu"]]
            + [[p(record, s["small"]), spec.owner, "CẦN QA XÁC NHẬN"] for record in spec.records],
            [76 * mm, 45 * mm, 47 * mm],
        ),
        PageBreak(),
        p("9. Sai lệch, thay đổi và đào tạo", s["h1"]),
        p("Mọi sai lệch phát sinh khi áp dụng phiên bản đã phê duyệt phải được ghi nhận theo hệ thống deviation/CAPA. Thay đổi nội dung, biểu mẫu, hệ thống hoặc trách nhiệm phải qua change control phù hợp. Nhân sự chỉ được thực hiện sau khi đào tạo và đánh giá năng lực theo yêu cầu đã duyệt.", s["body"]),
        p("10. Tài liệu tham chiếu dùng để soạn draft", s["h1"]),
    ])
    for index, (label, url) in enumerate(spec.references, start=1):
        story.append(p(f"{index}. {label}: {url}", s["small"]))
    story.extend([
        p("11. Hàng đợi rà soát và phê duyệt", s["h1"]),
        draft_table([
            ["Gate", "Người/Ngày", "Trạng thái"],
            ["SME kỹ thuật", "ĐỂ TRỐNG", "PENDING_OWNER_REVIEW"],
            ["QA/GMP", "ĐỂ TRỐNG", "PENDING_OWNER_REVIEW"],
            ["Data integrity", "ĐỂ TRỐNG", "PENDING_OWNER_REVIEW"],
            ["Chủ tài liệu", "ĐỂ TRỐNG", "PENDING_OWNER_REVIEW"],
        ], [53 * mm, 55 * mm, 60 * mm]),
        Spacer(1, 8 * mm),
        draft_table([
            ["Người soạn draft", "Người rà soát", "Người phê duyệt"],
            ["Codex GPT\nKhông có quyền phê duyệt", "Tên/chữ ký/ngày: ĐỂ TRỐNG", "Tên/chữ ký/ngày: ĐỂ TRỐNG"],
        ], [56 * mm, 56 * mm, 56 * mm]),
        Spacer(1, 8 * mm),
        p(f"Machine status: {STATUS_DRAFT} | Authority: DENY | Production import/index: DENY", s["notice"]),
    ])
    decorator = page_decorator(spec)
    doc.build(story, onFirstPage=decorator, onLaterPages=decorator, canvasmaker=InvariantCanvas)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sampled_page_indexes(reader: PdfReader, official: bool) -> list[int]:
    if not official:
        return list(range(len(reader.pages)))
    indexes = set(range(min(5, len(reader.pages))))
    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        normalized = " ".join(text.lower().split())
        if "annex 5" in normalized and "data" in normalized:
            indexes.update({max(0, index - 1), index, min(len(reader.pages) - 1, index + 1)})
            break
    indexes.add(len(reader.pages) - 1)
    return sorted(indexes)


def inspect_pdf(path: Path, code: str, official: bool) -> dict[str, Any]:
    reader = PdfReader(str(path))
    sample_indexes = sampled_page_indexes(reader, official)
    sampled_texts = [(reader.pages[index].extract_text() or "") for index in sample_indexes]
    sampled_text = "\n".join(sampled_texts)
    tables = 0
    with pdfplumber.open(path) as pdf:
        for index in sample_indexes[:8]:
            tables += len(pdf.pages[index].extract_tables() or [])
    expected_identity = "WHO" if official else code
    return {
        "document_code": code,
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "page_count": len(reader.pages),
        "sampled_page_numbers": [index + 1 for index in sample_indexes],
        "sampled_text_char_count": len(sampled_text),
        "sampled_text_sha256": hashlib.sha256(sampled_text.encode("utf-8")).hexdigest(),
        "sampled_nonempty_page_count": sum(bool(text.strip()) for text in sampled_texts),
        "sampled_table_count": tables,
        "figure_marker_count": sampled_text.count("Hình 1"),
        "identity_present": expected_identity.lower() in sampled_text.lower(),
        "draft_marker_present": STATUS_DRAFT in sampled_text or STATUS_DRAFT.encode("ascii") in path.read_bytes(),
        "pdf_signature_valid": path.read_bytes()[:5] == b"%PDF-",
        "encrypted": bool(reader.is_encrypted),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_corpus(output_dir: Path, who_source: Path, manifest_path: Path, report_path: Path, review_path: Path) -> dict[str, Any]:
    register_fonts()
    if not who_source.exists():
        raise FileNotFoundError(f"WHO TRS 996 source not found: {who_source}")
    if who_source.read_bytes()[:5] != b"%PDF-":
        raise ValueError("WHO TRS 996 source is not a PDF binary.")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".r05_draft_lane.json").write_text(
        json.dumps({
            "lane": "R05-A19_CONTROLLED_DRAFT_CORPUS",
            "authoritative_eligible": False,
            "production_import_allowed": False,
            "required_transition": "HUMAN_OWNER_REVIEW_AND_EXACT_LIVE_APPROVAL",
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for spec in SPECS:
        build_draft_pdf(spec, output_dir / f"{spec.code}.pdf")
    who_target = output_dir / "WHO-TRS-996.pdf"
    shutil.copyfile(who_source, who_target)

    title_by_code = {spec.code: spec.title for spec in SPECS}
    title_by_code["WHO-TRS-996"] = "WHO Technical Report Series 996 - official WHO report"
    paths = [output_dir / f"{spec.code}.pdf" for spec in SPECS] + [who_target]
    records: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    for path in paths:
        code = path.stem
        official = code == "WHO-TRS-996"
        evidence = inspect_pdf(path, code, official)
        status = STATUS_OFFICIAL if official else STATUS_DRAFT
        record = {
            "document_code": code,
            "document_title": title_by_code[code],
            "file_name": path.name,
            "artifact_status": status,
            "source_type": "official_external_reference" if official else "codex_generated_internal_draft",
            "source_url": WHO_TRS_996 if official else "local://r05-a19-controlled-draft-generator",
            "license_status": "CC_BY_NC_SA_3_0_IGO_REVIEW_REQUIRED" if official else "USER_OWNED_DRAFT_PENDING_OWNER_ACCEPTANCE",
            "owner_review_status": "PENDING_OWNER_REVIEW",
            "authoritative_confirmed": "false",
            "mime_type": "application/pdf",
            **evidence,
        }
        records.append(record)
        review_rows.append({
            "document_code": code,
            "document_title": title_by_code[code],
            "artifact_status": status,
            "technical_sme_decision": "PENDING",
            "qa_gmp_decision": "PENDING",
            "data_integrity_decision": "PENDING",
            "license_owner_decision": "PENDING",
            "reviewer_name": "",
            "reviewed_at": "",
            "review_notes": "",
            "promotion_decision": "DENY_UNTIL_ALL_REQUIRED_REVIEWS_PASS",
        })

    manifest_fields = [
        "document_code", "document_title", "file_name", "artifact_status", "source_type",
        "source_url", "license_status", "owner_review_status", "authoritative_confirmed",
        "mime_type", "size_bytes", "sha256", "page_count", "sampled_page_numbers",
        "sampled_text_char_count", "sampled_text_sha256", "sampled_nonempty_page_count",
        "sampled_table_count", "figure_marker_count", "identity_present", "draft_marker_present",
        "pdf_signature_valid", "encrypted",
    ]
    csv_records = []
    for record in records:
        csv_record = dict(record)
        csv_record["sampled_page_numbers"] = ",".join(map(str, record["sampled_page_numbers"]))
        csv_records.append(csv_record)
    write_csv(manifest_path, csv_records, manifest_fields)
    write_csv(review_path, review_rows, list(review_rows[0]))

    report = {
        "schema_version": 1,
        "rhythm": "R05-A19",
        "decision": "READY_FOR_OWNER_REVIEW_NOT_PRODUCTION",
        "ok": True,
        "corpus_lane": "CONTROLLED_DRAFT_ISOLATED",
        "output_directory": str(output_dir),
        "document_count": len(records),
        "draft_document_count": sum(record["artifact_status"] == STATUS_DRAFT for record in records),
        "official_reference_count": sum(record["artifact_status"] == STATUS_OFFICIAL for record in records),
        "authoritative_confirmed_count": 0,
        "production_import_allowed": False,
        "retrieval_enablement_allowed": False,
        "records": records,
        "aggregate": {
            "total_bytes": sum(record["size_bytes"] for record in records),
            "total_pages": sum(record["page_count"] for record in records),
            "sampled_text_char_count": sum(record["sampled_text_char_count"] for record in records),
            "sampled_table_count": sum(record["sampled_table_count"] for record in records),
            "figure_marker_count": sum(record["figure_marker_count"] for record in records),
            "pdf_signature_pass": sum(bool(record["pdf_signature_valid"]) for record in records),
            "identity_pass": sum(bool(record["identity_present"]) for record in records),
            "unique_binary_sha256": len({record["sha256"] for record in records}),
        },
        "blockers": {
            "BLK-003": "OPEN_DRAFT_AND_LOCAL_BINARY_EVIDENCE_NOT_CURRENT_VERSION_LINKAGE",
            "BLK-004": "OPEN_PARSE_EVIDENCE_AWAITS_OWNER_REVIEW",
            "BLK-006": "OPEN_RETRIEVAL_REMAINS_FAIL_CLOSED",
            "BLK-007": "OPEN_U10_U15_AND_AGENT_CANARY_NOT_RUN",
        },
        "required_next_transition": [
            "Human technical SME, QA/GMP, data-integrity and license/owner review.",
            "Create corrected authoritative corpus only from records explicitly accepted by the owner.",
            "Prepare a fresh exact Supabase/n8n live-mutation plan for approved versions only.",
        ],
        "remote_operations": {"supabase": [], "n8n": [], "git": []},
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--who-trs-996-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_corpus(args.output_dir, args.who_trs_996_source, args.manifest, args.report, args.review_queue)
    print(json.dumps({
        "decision": report["decision"],
        "document_count": report["document_count"],
        "draft_document_count": report["draft_document_count"],
        "official_reference_count": report["official_reference_count"],
        "authoritative_confirmed_count": report["authoritative_confirmed_count"],
        "aggregate": report["aggregate"],
        "remote_operations": report["remote_operations"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
