-- CRAVE Chat 15 - Migration 018: seed du lieu nghiep vu cho WF-03/04/05.
-- Cot NOT NULL can cung cap (khong co default):
--   validation_templates: template_code, template_name
--   calculation_formulas: formula_code, formula_name, category, formula_display, formula_js
--   equipment_registry:   equipment_code, equipment_name, equipment_type
-- Chien luoc validation_templates: UPDATE IQ/OQ (da co row); INSERT PQ (chua co).

begin;

-- ────────────────────────────────────────────────────────────
-- prompt_versions: 3 prompt, skip neu da ton tai.
-- ────────────────────────────────────────────────────────────

insert into public.prompt_versions (prompt_name, version, prompt_text, is_active)
select 'protocol_writer', 'v1.0',
'Bạn là chuyên gia thẩm định hệ thống và thiết bị trong ngành dược, làm việc theo nguyên tắc GMP và toàn vẹn dữ liệu ALCOA+.

Nhiệm vụ của bạn là soạn bản DỰ THẢO đề cương thẩm định từ đúng thông tin thiết bị, loại đề cương, cấu trúc template và yêu cầu đặc biệt do người dùng cung cấp. Không tự bịa tiêu chí chấp nhận, thông số kỹ thuật, tài liệu tham chiếu, kết quả thử nghiệm hoặc trạng thái phê duyệt. Khi đầu vào không đủ căn cứ, ghi rõ "CẦN BỔ SUNG/CẦN QA PHÊ DUYỆT" tại vị trí tương ứng.

Yêu cầu đầu ra:
1. Viết bằng tiếng Việt, định dạng Markdown rõ ràng; không trả JSON và không dùng code fence.
2. Giữ đúng thứ tự mọi section trong template; không bỏ qua section có required=true.
3. Mỗi phép thử phải nêu mục tiêu, điều kiện tiên quyết, dụng cụ/tài liệu, các bước thực hiện, bằng chứng cần lưu và tiêu chí chấp nhận có thể đo lường. Nếu chưa có căn cứ phê duyệt cho tiêu chí, để trạng thái CẦN BỔ SUNG thay vì suy đoán.
4. Phân biệt dữ liệu đầu vào, nội dung dự thảo và kết luận. Không tuyên bố thiết bị hoặc đề cương đã được phê duyệt.
5. Có các phần về vai trò/trách nhiệm, quản lý sai lệch, kiểm soát thay đổi, dữ liệu thô, phê duyệt và kết luận khi template yêu cầu.
6. Kết thúc bằng cảnh báo: "[AI-DRAFT] Nội dung do AI tạo, cần người có chuyên môn GMP xem xét và phê duyệt trước khi sử dụng."',
true
where not exists (
  select 1 from public.prompt_versions
  where prompt_name = 'protocol_writer' and version = 'v1.0'
)
on conflict do nothing;

insert into public.prompt_versions (prompt_name, version, prompt_text, is_active)
select 'protocol_checker', 'v1.0',
'Bạn là chuyên gia QA/GMP độc lập đang rà soát ngữ nghĩa một đề cương thẩm định. Chỉ đánh giá từ nội dung và bối cảnh được cung cấp; không bịa yêu cầu pháp lý, tiêu chí chấp nhận, thông số thiết bị hoặc nguồn tham chiếu. Không lặp lại các lỗi đã có trong danh sách FINDINGS TỪ RULE-CHECK, trừ khi cần bổ sung một rủi ro ngữ nghĩa khác biệt.

Tập trung kiểm tra: nội dung có phù hợp loại đề cương và mục đích sử dụng thiết bị hay không; trình tự thử nghiệm có khả thi hay không; tiêu chí chấp nhận có rõ ràng, đo được và truy nguyên đến căn cứ đã nêu hay không; dữ liệu/bằng chứng có đáp ứng ALCOA+ hay không; trách nhiệm, sai lệch, kiểm soát thay đổi và kết luận có nhất quán hay không.

Chỉ trả về một JSON object hợp lệ, không Markdown, không code fence và không có văn bản ngoài JSON. Schema bắt buộc: {"overall_status":"PASS | CONDITIONAL | FAIL","critical_findings":[{"location":"vị trí","finding":"phát hiện","risk":"rủi ro","recommendation":"hành động đề xuất"}],"major_findings":[],"minor_findings":[],"summary":"tóm tắt ngắn"}. Mọi mảng phải tồn tại dù rỗng. Không đưa ra tuyên bố phê duyệt cuối cùng.',
true
where not exists (
  select 1 from public.prompt_versions
  where prompt_name = 'protocol_checker' and version = 'v1.0'
)
on conflict do nothing;

insert into public.prompt_versions (prompt_name, version, prompt_text, is_active)
select 'calculation_reviewer', 'v1.0',
'Bạn là chuyên gia rà soát tính toán thẩm định theo GMP. Kết quả số học trong yêu cầu đã được tính bằng công thức JavaScript deterministic; tuyệt đối không thay đổi, làm tròn lại hoặc thay thế kết quả đó bằng phép tính của AI.

Hãy diễn giải bằng tiếng Việt, ngắn gọn và có cấu trúc:
- Nêu tên/mã/phiên bản công thức và ý nghĩa của phép tính.
- Tóm tắt input, đơn vị (nếu được cung cấp), kết quả và nguồn công thức.
- Nếu có tiêu chí chấp nhận, giải thích vì sao kết quả ĐẠT hoặc KHÔNG ĐẠT đúng theo toán tử đã cung cấp. Nếu không có tiêu chí đã duyệt, ghi rõ "CHƯA THỂ KẾT LUẬN ĐẠT/KHÔNG ĐẠT".
- Nêu các điều kiện có thể làm kết quả không hợp lệ, như thiếu đơn vị, dữ liệu đầu vào không truy nguyên được, số lần lặp không đủ hoặc công thức không phù hợp mục đích sử dụng.
- Không bịa dữ liệu, giới hạn GMP hoặc trạng thái phê duyệt; không tự đặt tiêu chí chấp nhận.

Kết thúc bằng cảnh báo: "Diễn giải do AI tạo; người có chuyên môn phải xác nhận công thức, dữ liệu đầu vào, đơn vị và tiêu chí trước khi đưa vào hồ sơ GMP."',
true
where not exists (
  select 1 from public.prompt_versions
  where prompt_name = 'calculation_reviewer' and version = 'v1.0'
)
on conflict do nothing;

-- ────────────────────────────────────────────────────────────
-- validation_templates: UPDATE IQ/OQ, INSERT PQ.
-- ────────────────────────────────────────────────────────────

update public.validation_templates
set
  template_structure = '[{"section":"1","title":"Thông tin và kiểm soát tài liệu","required":true},{"section":"2","title":"Mục đích","required":true},{"section":"3","title":"Phạm vi","required":true},{"section":"4","title":"Tài liệu tham chiếu","required":true},{"section":"5","title":"Thuật ngữ và chữ viết tắt","required":false},{"section":"6","title":"Vai trò và trách nhiệm","required":true},{"section":"7","title":"Mô tả thiết bị và cấu hình","required":true},{"section":"8","title":"Kiểm tra hồ sơ và bản vẽ lắp đặt","required":true},{"section":"9","title":"Kiểm tra thành phần, tiện ích và điều kiện môi trường","required":true},{"section":"10","title":"Kiểm tra hiệu chuẩn và an toàn","required":true},{"section":"11","title":"Quản lý dữ liệu, tài khoản và sao lưu","required":true},{"section":"12","title":"Sai lệch và hành động khắc phục","required":true},{"section":"13","title":"Tổng hợp kết quả và kết luận IQ","required":true},{"section":"14","title":"Phê duyệt","required":true}]'::jsonb,
  updated_at = now()
where template_code = 'TPL-IQ-001' and language_code = 'vi';

update public.validation_templates
set
  template_structure = '[{"section":"1","title":"Thông tin và kiểm soát tài liệu","required":true},{"section":"2","title":"Mục đích","required":true},{"section":"3","title":"Phạm vi","required":true},{"section":"4","title":"Tài liệu tham chiếu","required":true},{"section":"5","title":"Vai trò và trách nhiệm","required":true},{"section":"6","title":"Điều kiện tiên quyết","required":true},{"section":"7","title":"Mô tả chức năng và dải vận hành","required":true},{"section":"8","title":"Thử nghiệm chức năng và liên động","required":true},{"section":"9","title":"Thử nghiệm cảnh báo và điều kiện biên","required":true},{"section":"10","title":"Thử nghiệm bảo mật và toàn vẹn dữ liệu","required":true},{"section":"11","title":"Kiểm tra audit trail, sao lưu và khôi phục","required":true},{"section":"12","title":"Sai lệch và hành động khắc phục","required":true},{"section":"13","title":"Tổng hợp kết quả và kết luận OQ","required":true},{"section":"14","title":"Phê duyệt","required":true}]'::jsonb,
  updated_at = now()
where template_code = 'TPL-OQ-001' and language_code = 'vi';

insert into public.validation_templates (
  template_code, template_name, protocol_type, language_code,
  version, status, template_structure, is_active
)
select
  'TPL-PQ-001',
  'Template đề cương PQ thiết bị chung',
  'pq', 'vi', '01', 'approved_for_ai_use',
  '[{"section":"1","title":"Thông tin và kiểm soát tài liệu","required":true},{"section":"2","title":"Mục đích","required":true},{"section":"3","title":"Phạm vi","required":true},{"section":"4","title":"Tài liệu tham chiếu","required":true},{"section":"5","title":"Vai trò và trách nhiệm","required":true},{"section":"6","title":"Điều kiện tiên quyết và trạng thái IQ/OQ","required":true},{"section":"7","title":"Quy trình vận hành thường quy và kế hoạch lấy mẫu","required":true},{"section":"8","title":"Thử nghiệm hiệu năng trong điều kiện sử dụng dự kiến","required":true},{"section":"9","title":"Dữ liệu thô và phương pháp tính toán","required":true},{"section":"10","title":"Phân tích xu hướng, độ lặp lại và độ ổn định","required":true},{"section":"11","title":"Tiêu chí chấp nhận và đánh giá kết quả","required":true},{"section":"12","title":"Sai lệch và hành động khắc phục","required":true},{"section":"13","title":"Tổng hợp kết quả và kết luận PQ","required":true},{"section":"14","title":"Phê duyệt và kế hoạch tái thẩm định","required":true}]'::jsonb,
  true
where not exists (
  select 1 from public.validation_templates where template_code = 'TPL-PQ-001'
)
on conflict do nothing;

-- ────────────────────────────────────────────────────────────
-- calculation_formulas: 3 cong thuc ICH Q2(R2). category NOT NULL.
-- ────────────────────────────────────────────────────────────

insert into public.calculation_formulas (
  formula_code, formula_name, category,
  formula_js, formula_display, reference_source, version, is_active
)
select
  'rsd_repeatability',
  'Độ lệch chuẩn tương đối của độ lặp lại',
  'precision',
  '(() => { if (!Array.isArray(values) || values.length < 2) throw new Error(''values phải có ít nhất 2 giá trị''); const numbers = values.map(Number); if (numbers.some((v) => !Number.isFinite(v))) throw new Error(''values chứa giá trị không hợp lệ''); const mean = numbers.reduce((s, v) => s + v, 0) / numbers.length; if (mean === 0) throw new Error(''Giá trị trung bình phải khác 0''); const sd = Math.sqrt(numbers.reduce((s, v) => s + (v - mean) ** 2, 0) / (numbers.length - 1)); return sd / Math.abs(mean) * 100; })()',
  'RSD (%) = s / |x̄| × 100; s = sqrt(Σ(xᵢ - x̄)² / (n - 1))',
  'ICH Q2(R2), mục 3.3.2 - Precision (bản hiệu chỉnh 2025)',
  '1.0', true
where not exists (
  select 1 from public.calculation_formulas
  where formula_code = 'rsd_repeatability' and version = '1.0'
)
on conflict do nothing;

insert into public.calculation_formulas (
  formula_code, formula_name, category,
  formula_js, formula_display, reference_source, version, is_active
)
select
  'recovery_rate',
  'Tỷ lệ thu hồi trong nghiên cứu thêm chuẩn',
  'accuracy',
  '(() => { const sv = Number(spiked); const uv = Number(unspiked); const av = Number(added); if (![sv, uv, av].every(Number.isFinite)) throw new Error(''spiked, unspiked và added phải là số hợp lệ''); if (av === 0) throw new Error(''added phải khác 0''); return (sv - uv) / av * 100; })()',
  'Recovery (%) = (kết quả mẫu thêm chuẩn - kết quả mẫu không thêm chuẩn) / lượng chuẩn đã thêm × 100',
  'ICH Q2(R2), mục 3.3.1.2 - Spiking Study (bản hiệu chỉnh 2025)',
  '1.0', true
where not exists (
  select 1 from public.calculation_formulas
  where formula_code = 'recovery_rate' and version = '1.0'
)
on conflict do nothing;

insert into public.calculation_formulas (
  formula_code, formula_name, category,
  formula_js, formula_display, reference_source, version, is_active
)
select
  'lod_lod_calc',
  'Giới hạn phát hiện theo độ lệch chuẩn đáp ứng và độ dốc',
  'sensitivity',
  '(() => { const rsd = Number(response_sd); const sl = Number(slope); if (![rsd, sl].every(Number.isFinite)) throw new Error(''response_sd và slope phải là số hợp lệ''); if (rsd < 0) throw new Error(''response_sd không được âm''); if (sl === 0) throw new Error(''slope phải khác 0''); return 3.3 * rsd / Math.abs(sl); })()',
  'LOD = 3.3 × σ / |S|; σ = độ lệch chuẩn của đáp ứng, S = độ dốc đường chuẩn',
  'ICH Q2(R2), mục 3.2.3.3 - Standard Deviation of a Linear Response and a Slope (bản hiệu chỉnh 2025)',
  '1.0', true
where not exists (
  select 1 from public.calculation_formulas
  where formula_code = 'lod_lod_calc' and version = '1.0'
)
on conflict do nothing;

-- ────────────────────────────────────────────────────────────
-- equipment_registry: 2 thiet bi mau.
-- ────────────────────────────────────────────────────────────

insert into public.equipment_registry (
  equipment_code, equipment_name, equipment_type,
  manufacturer, model, location, intended_use, is_active
)
select
  'HPLC-001', 'Máy sắc ký lỏng hiệu năng cao', 'hplc',
  'Agilent Technologies', '1260 Infinity II', 'Phòng Kiểm nghiệm hóa lý',
  'Định tính, định lượng và kiểm tra tạp chất của nguyên liệu, bán thành phẩm và thành phẩm',
  true
where not exists (
  select 1 from public.equipment_registry where equipment_code = 'HPLC-001'
)
on conflict do nothing;

insert into public.equipment_registry (
  equipment_code, equipment_name, equipment_type,
  manufacturer, model, location, intended_use, is_active
)
select
  'BALANCE-001', 'Cân phân tích', 'analytical_balance',
  'Mettler Toledo', 'XPR205', 'Phòng Cân - Kiểm nghiệm hóa lý',
  'Cân mẫu và chất chuẩn phục vụ thử nghiệm kiểm nghiệm chất lượng',
  true
where not exists (
  select 1 from public.equipment_registry where equipment_code = 'BALANCE-001'
)
on conflict do nothing;

commit;
