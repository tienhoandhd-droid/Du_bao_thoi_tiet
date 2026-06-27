# Hợp đồng governance 4 tầng cho CRAVE

## 1. Mục đích và phạm vi

Hợp đồng này áp dụng cho mọi đường xử lý câu hỏi dùng RAG trong CRAVE, gồm AI Search, trợ lý agentic và mọi tool truy hồi được gọi từ workflow n8n. Mục tiêu là không để một tầng đơn lẻ quyết định độ an toàn của câu trả lời.

Frontend chỉ thực hiện kiểm tra sớm và hiển thị trạng thái. Workflow n8n và PostgreSQL là các điểm thực thi có thẩm quyền; client không được xem là ranh giới bảo mật.

## 2. Các bất biến bắt buộc

- Không hard-code URL, API key, JWT hoặc secret trong source. Cấu hình được đọc từ môi trường triển khai.
- n8n chỉ dùng hai credential đã phê duyệt: `GMP-check` và `OpenAl`.
- Không dùng n8n Variables, credential thứ ba hoặc community node.
- Mọi tool truy hồi tài liệu phải đi qua `hybrid_search_v3`; không được truy vấn thô `documents` hoặc `document_chunks` để tạo ngữ cảnh trả lời.
- Chỉ tài liệu đang được phê duyệt cho AI mới được vào tập ngữ cảnh.
- Không có điểm số nào thay thế quyết định chuyên môn hoặc phê duyệt GMP.

## 3. Ma trận bốn tầng phòng thủ

| Tầng | Cổng cho phép | Hành động khi không đạt | Bằng chứng cần lưu |
|---|---|---|---|
| 1. Input | Query sau khi trim không rỗng, tối đa 500 ký tự và không chứa mẫu SQL injection rõ ràng | Từ chối trước retrieval, không gọi model | Lý do từ chối, thời gian, user/session |
| 2. Retrieval | Chỉ nguồn `approved_for_ai_use=true`; mọi tool gọi `hybrid_search_v3` | Trả trạng thái không đủ nguồn, không tự bổ sung kiến thức | Tham số tìm kiếm, chunk/tài liệu, phiên bản, điểm truy hồi |
| 3. Generation | Prompt buộc trả lời chỉ từ ngữ cảnh và luôn có disclaimer | Không đủ ngữ cảnh thì nói không tìm thấy; không suy đoán | Model tag, prompt version, answer, citation |
| 4. Output | `grounded_pct >= 0.60` và confidence tối thiểu `MEDIUM` | Chặn nội dung khẳng định, hạ confidence và chuyển người có chuyên môn | Grounded flags, grounded_pct, confidence, kết quả gate |

## 4. Tầng 1 — Input validation

### Quy tắc

1. Chuẩn hóa bằng cách trim khoảng trắng đầu và cuối.
2. Từ chối chuỗi rỗng.
3. Từ chối chuỗi dài hơn 500 ký tự sau khi trim.
4. Từ chối các mẫu SQL injection rõ ràng, tối thiểu gồm:
   - comment token `--`, `/*` hoặc `*/`;
   - stacked statement như dấu chấm phẩy theo sau bởi `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE` hoặc `TRUNCATE`;
   - `UNION SELECT`;
   - lệnh thay đổi dữ liệu/schema như `INSERT INTO`, `DELETE FROM`, `UPDATE ... SET`, `DROP TABLE`, `ALTER TABLE`, `CREATE TABLE`, `TRUNCATE TABLE`.

Kiểm tra mẫu chỉ là một guard để từ chối sớm, không phải biện pháp chống injection duy nhất. Mọi truy vấn dữ liệu phía server vẫn phải dùng tham số bind hoặc RPC có kiểu; không được nối query người dùng vào SQL.

### Kết quả hợp đồng

- Đạt: chuyển query đã chuẩn hóa sang tầng Retrieval.
- Không đạt: trả lỗi validation có lý do, không gọi n8n retrieval hoặc OpenAI.

## 5. Tầng 2 — Retrieval governance

### Quy tắc

- `hybrid_search_v3` là cổng truy hồi duy nhất cho AI Search và mọi tool của AI Agent.
- Kết quả chỉ được phép chứa tài liệu có `approved_for_ai_use=true` và còn hiệu lực theo governance hiện hành.
- Workflow không được dùng node SQL để lấy trực tiếp nội dung từ `documents` hoặc `document_chunks` làm ngữ cảnh trả lời.
- Mỗi chunk phải giữ metadata truy xuất được: document id/code, version, chunk id, section/page, language và relevance score.
- Nếu không có ngữ cảnh đạt điều kiện, tầng Retrieval trả danh sách rỗng cùng mã lý do; không thay thế bằng kiến thức nền của model.

### Kiểm tra release

- Rà toàn bộ workflow prefix `TKTL` để xác nhận các tool retrieval gọi `hybrid_search_v3`.
- Kiểm tra không có nhánh fallback đọc thô bảng tài liệu.
- Kiểm tra policy/phân quyền không mở dữ liệu chưa duyệt cho `anon`.

## 6. Tầng 3 — Generation constraint

System prompt của nhánh generation phải có đủ ba mệnh đề:

1. Chỉ trả lời từ retrieved contexts được cung cấp.
2. Không sáng tạo, suy đoán hoặc điền phần thiếu bằng kiến thức ngoài nguồn.
3. Khi nguồn không đủ, nói rõ không tìm thấy thông tin phù hợp và yêu cầu người có chuyên môn kiểm tra.

Mọi câu trả lời, kể cả câu trả lời bị hạ confidence, phải có disclaimer:

> Nội dung do AI tạo từ nguồn đã duyệt, cần người có chuyên môn xem xét trước khi dùng cho quyết định hoặc hồ sơ GMP chính thức.

Prompt version và model tag phải được ghi cùng audit/evaluation record để một kết quả có thể tái hiện và so sánh.

## 7. Tầng 4 — Output grounding và confidence

### Cách tính grounding

`grounded_pct` là tỷ lệ citation/claim được đánh dấu `grounded=true` trên tổng citation/claim có kết quả grounding. Giá trị được chuẩn hóa về khoảng 0 đến 1.

- Gate grounding đạt khi `grounded_pct >= 0.60`.
- Gate confidence đạt khi confidence là `HIGH` hoặc `MEDIUM`.
- Output chỉ được phát hành bình thường khi cả hai gate đạt.

Nếu thiếu citation, không tính được grounding, `grounded_pct < 0.60`, hoặc confidence là `LOW`/`BLOCKED`, hệ thống phải:

- không trình bày nội dung như một kết luận GMP đã xác nhận;
- trả trạng thái thiếu căn cứ hoặc cần kiểm tra chuyên môn;
- vẫn hiển thị disclaimer;
- lưu kết quả gate, citation và nguyên nhân chặn vào audit trail.

## 8. Liên hệ với evaluation harness

- `eval_results` lưu ba điểm Ragas: faithfulness, answer relevancy và context recall, cùng `grounded_pct` và raw JSON.
- Điểm của một câu là trung bình ba metric; câu đạt khi điểm trung bình tối thiểu 0.90.
- `eval_runs.score_mean` là trung bình điểm câu; cả run đạt khi `score_mean >= 0.90`.
- Ngưỡng evaluation 0.90 đo chất lượng hồi quy; ngưỡng grounding 0.60 là gate phát hành output. Hai ngưỡng có mục đích khác nhau và không được thay thế cho nhau.

## 9. Phân công thực thi

| Thành phần | Trách nhiệm |
|---|---|
| React frontend | Validate sớm input, giới hạn 500 ký tự, hiển thị bốn tầng và trạng thái nguồn/confidence |
| n8n workflow `TKTL` | Xác thực JWT, gọi duy nhất RPC retrieval được phê duyệt, áp prompt constraint và output gate |
| Supabase/PostgreSQL | RLS, policy, governance filter, lưu audit và eval append-only theo quyền đã cấp |
| Eval harness | Chạy golden questions, chấm Ragas, lưu run/result và báo pass/fail |
| QA/người có chuyên môn | Rà soát output bị cảnh báo, phê duyệt quyết định GMP và xử lý CAPA khi cần |

## 10. Tiêu chí nghiệm thu

- Query rỗng, quá 500 ký tự và payload SQL injection mẫu đều bị chặn trước API call.
- Retrieval không trả tài liệu chưa được phê duyệt cho AI.
- Không tool retrieval nào đi vòng ngoài `hybrid_search_v3`.
- Câu trả lời thiếu nguồn không được model tự hoàn thiện.
- Disclaimer xuất hiện trên mọi output.
- Output có `grounded_pct < 0.60` hoặc confidence dưới `MEDIUM` bị chặn/hạ cấp.
- Eval run lưu đủ số câu, ba metric, grounding, raw JSON và kết quả pass theo ngưỡng 0.90.
