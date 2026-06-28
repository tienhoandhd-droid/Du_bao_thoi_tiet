-- CRAVE Chat 15 - Rollback Migration 018.
-- Xoa seed rows va khoi phuc template_structure goc cua IQ/OQ.

begin;

delete from public.equipment_registry
where equipment_code in ('HPLC-001', 'BALANCE-001');

delete from public.calculation_formulas
where formula_code in ('rsd_repeatability', 'recovery_rate', 'lod_lod_calc')
  and version = '1.0';

-- Xoa PQ (row moi duoc tao boi 018).
delete from public.validation_templates
where template_code = 'TPL-PQ-001';

-- Khoi phuc template_structure goc cua TPL-IQ-001 (truoc khi 018 UPDATE).
update public.validation_templates
set
  template_structure = '[
    {"title":"Mục đích","section":"1","required":true,"description":"Mục đích của đề cương IQ"},
    {"title":"Phạm vi","section":"2","required":true,"description":"Phạm vi áp dụng"},
    {"title":"Tài liệu tham chiếu","section":"3","required":true,"description":"SOP, guideline, manual liên quan"},
    {"title":"Định nghĩa và viết tắt","section":"4","required":true},
    {"title":"Trách nhiệm","section":"5","required":true,"description":"Ai soạn, ai thực hiện, ai duyệt"},
    {"title":"Điều kiện tiên quyết","section":"6","required":true,"description":"DQ/FAT/SAT, URS, đào tạo..."},
    {"title":"Mô tả thiết bị","section":"7","required":true,"description":"Tên, mã, NSX, model, vị trí, công dụng"},
    {"title":"Quy trình thẩm định IQ","section":"8","required":true},
    {"title":"Kiểm tra tài liệu","section":"8.1","required":true},
    {"title":"Kiểm tra lắp đặt cơ học","section":"8.2","required":true},
    {"title":"Kiểm tra kết nối điện","section":"8.3","required":true},
    {"title":"Kiểm tra hệ thống tiện ích","section":"8.4","required":true},
    {"title":"Kiểm tra hiệu chuẩn","section":"8.5","required":true},
    {"title":"Tiêu chí chấp nhận","section":"9","required":true},
    {"title":"Xử lý sai lệch","section":"10","required":true},
    {"title":"Kết luận","section":"11","required":true},
    {"title":"Phụ lục","section":"12","required":false}
  ]'::jsonb,
  updated_at = now()
where template_code = 'TPL-IQ-001'
  and language_code = 'vi';

-- Khoi phuc template_structure goc cua TPL-OQ-001.
update public.validation_templates
set
  template_structure = '[
    {"title":"Mục đích","section":"1","required":true},
    {"title":"Phạm vi","section":"2","required":true},
    {"title":"Tài liệu tham chiếu","section":"3","required":true},
    {"title":"Định nghĩa","section":"4","required":true},
    {"title":"Trách nhiệm","section":"5","required":true},
    {"title":"Điều kiện tiên quyết","section":"6","required":true,"description":"IQ approved, thiết bị đã hiệu chuẩn"},
    {"title":"Mô tả thiết bị","section":"7","required":true},
    {"title":"Quy trình thẩm định OQ","section":"8","required":true},
    {"title":"Kiểm tra chức năng vận hành","section":"8.1","required":true},
    {"title":"Kiểm tra báo động / interlock","section":"8.2","required":true},
    {"title":"Kiểm tra điều kiện giới hạn","section":"8.3","required":true},
    {"title":"Tiêu chí chấp nhận","section":"9","required":true},
    {"title":"Xử lý sai lệch","section":"10","required":true},
    {"title":"Kết luận","section":"11","required":true},
    {"title":"Phụ lục","section":"12","required":false}
  ]'::jsonb,
  updated_at = now()
where template_code = 'TPL-OQ-001'
  and language_code = 'vi';

delete from public.prompt_versions
where prompt_name in ('protocol_writer', 'protocol_checker', 'calculation_reviewer')
  and version = 'v1.0';

commit;
