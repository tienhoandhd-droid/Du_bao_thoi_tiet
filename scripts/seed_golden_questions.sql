-- CRAVE - Bổ sung 43 câu hỏi GMP vào 7 câu hiện có (tổng mục tiêu: 50).
--
-- Schema live của bdttccztjtrcaztjgkot dùng question_text/expected_sources và
-- yêu cầu expected_answer NOT NULL. CTE giữ tên logic question và
-- expected_keywords theo hợp đồng PHA 1B, sau đó ánh xạ:
--   question          -> question_text
--   expected_keywords -> expected_sources
--
-- Idempotency được bảo đảm bởi advisory lock + NOT EXISTS theo nội dung câu hỏi.
-- ON CONFLICT (id) vẫn là lớp bảo vệ cuối; chỉ riêng ON CONFLICT không đủ vì id
-- được sinh mới bằng gen_random_uuid() ở mỗi lần chạy.

begin;

select pg_advisory_xact_lock(hashtext('CRAVE-016-seed-golden-questions'));

with seed_data(question, expected_answer, expected_keywords, category) as (
  values
    (
      'Một SOP dược phẩm phải được soạn thảo, phê duyệt, ban hành và rà soát định kỳ như thế nào?',
      'SOP phải có mã và phiên bản kiểm soát, được người có thẩm quyền soạn thảo, rà soát độc lập và phê duyệt trước khi có hiệu lực. SOP phải quy định ngày hiệu lực, chu kỳ rà soát, lịch sử sửa đổi và cơ chế thu hồi bản hết hiệu lực.',
      array['mã SOP', 'phiên bản', 'phê duyệt', 'ngày hiệu lực', 'rà soát định kỳ', 'lịch sử sửa đổi']::text[],
      'sop_control'
    ),
    (
      'Bản SOP hết hiệu lực tại khu vực sản xuất phải được kiểm soát ra sao?',
      'Bản hết hiệu lực phải được thu hồi kịp thời khỏi điểm sử dụng, đánh dấu hoặc hủy theo quy trình và lưu bản gốc theo thời hạn hồ sơ. Chỉ bản được kiểm soát và đang có hiệu lực mới được phép sử dụng.',
      array['thu hồi', 'bản hết hiệu lực', 'điểm sử dụng', 'bản được kiểm soát', 'lưu hồ sơ']::text[],
      'sop_control'
    ),
    (
      'Hồ sơ lô sản xuất tối thiểu phải ghi nhận những thông tin nào?',
      'Hồ sơ lô phải nhận diện sản phẩm và số lô, nguyên liệu cùng số lô và lượng dùng, thiết bị, công đoạn, thời gian, thông số thực tế, kết quả kiểm tra trong quá trình, sản lượng, đối chiếu, sai lệch và chữ ký người thực hiện lẫn người kiểm tra.',
      array['số lô', 'nguyên liệu', 'thiết bị', 'thông số thực tế', 'IPC', 'sản lượng', 'sai lệch', 'chữ ký']::text[],
      'batch_records'
    ),
    (
      'Khi ghi sai trong hồ sơ lô giấy, nhân viên phải sửa như thế nào để bảo đảm data integrity?',
      'Phải gạch một đường để nội dung cũ vẫn đọc được, ghi nội dung đúng, ký hoặc ký tắt, ghi ngày sửa và nêu lý do khi cần. Không được tẩy xóa, dùng bút xóa hoặc ghi đè che mất dữ liệu gốc.',
      array['gạch một đường', 'dữ liệu gốc', 'ký tắt', 'ngày sửa', 'lý do', 'không tẩy xóa']::text[],
      'batch_records'
    ),
    (
      'Đối chiếu sản lượng trong hồ sơ lô được thực hiện nhằm mục đích gì?',
      'Đối chiếu so sánh lượng đầu vào, sản lượng lý thuyết, sản lượng thực tế, phế phẩm và mẫu đã lấy để phát hiện chênh lệch bất thường. Chênh lệch ngoài giới hạn phải được điều tra và phê duyệt trước khi quyết định lô.',
      array['đầu vào', 'sản lượng lý thuyết', 'sản lượng thực tế', 'phế phẩm', 'chênh lệch', 'điều tra']::text[],
      'batch_records'
    ),
    (
      'Khi cấp phát nguyên liệu cho một lô thuốc, cần kiểm tra và ghi nhận những gì?',
      'Phải kiểm tra tên, mã, số lô, tình trạng phê duyệt, hạn dùng hoặc ngày tái kiểm, điều kiện bảo quản và khối lượng nguyên liệu. Việc cân cấp phát phải dùng thiết bị phù hợp, có kiểm tra độc lập và truy xuất được người thực hiện.',
      array['tên nguyên liệu', 'số lô', 'phê duyệt', 'hạn dùng', 'khối lượng', 'kiểm tra độc lập', 'truy xuất']::text[],
      'dispensing'
    ),
    (
      'Trước khi cân cấp phát nguyên liệu, khu vực cân phải được line clearance như thế nào?',
      'Khu vực phải được dọn sạch nguyên liệu, nhãn, tài liệu và dụng cụ của hoạt động trước; xác nhận tình trạng vệ sinh, thiết bị và cân; kiểm tra đúng hồ sơ lô và nguyên liệu; sau đó ghi nhận line clearance bởi người thực hiện và người kiểm tra.',
      array['line clearance', 'vệ sinh', 'hoạt động trước', 'cân', 'hồ sơ lô', 'người kiểm tra']::text[],
      'dispensing'
    ),
    (
      'Các thông số trọng yếu của công đoạn pha chế phải được kiểm soát ra sao?',
      'Các thông số như thứ tự nạp, tốc độ khuấy, thời gian, nhiệt độ, pH và thể tích phải theo hồ sơ lô đã phê duyệt, được ghi nhận theo thời gian thực và kiểm tra trong giới hạn. Sai lệch phải được đánh giá trước khi tiếp tục.',
      array['thứ tự nạp', 'tốc độ khuấy', 'thời gian', 'nhiệt độ', 'pH', 'giới hạn', 'sai lệch']::text[],
      'manufacturing_control'
    ),
    (
      'Thời gian lưu bán thành phẩm giữa hai công đoạn được quản lý như thế nào?',
      'Phải xác lập hold time có căn cứ hoặc đã thẩm định, ghi rõ thời điểm bắt đầu và kết thúc, điều kiện bảo quản cùng giới hạn cho phép. Vượt hold time phải được đánh giá sai lệch và tác động chất lượng trước khi xử lý tiếp.',
      array['hold time', 'thẩm định', 'bắt đầu', 'kết thúc', 'điều kiện bảo quản', 'sai lệch']::text[],
      'manufacturing_control'
    ),
    (
      'Kiểm tra trong quá trình sản xuất phải được lấy mẫu và xử lý kết quả như thế nào?',
      'Mẫu IPC phải được lấy theo vị trí, tần suất và cỡ mẫu đã phê duyệt bằng phương pháp tránh nhiễm hoặc nhầm lẫn. Kết quả phải ghi ngay, so với giới hạn và mọi kết quả không đạt phải được cách ly, đánh giá theo quy trình.',
      array['IPC', 'vị trí lấy mẫu', 'tần suất', 'cỡ mẫu', 'giới hạn', 'kết quả không đạt']::text[],
      'in_process_control'
    ),
    (
      'Nhiệt độ và độ ẩm kho nguyên liệu phải được giám sát như thế nào?',
      'Điều kiện kho phải dựa trên yêu cầu bảo quản đã phê duyệt, được giám sát bằng thiết bị hiệu chuẩn tại các vị trí đại diện theo mapping. Dữ liệu phải được rà soát, cảnh báo phải được phản ứng và mọi excursion phải được đánh giá tác động.',
      array['nhiệt độ', 'độ ẩm', 'mapping', 'thiết bị hiệu chuẩn', 'cảnh báo', 'excursion']::text[],
      'storage'
    ),
    (
      'Nguyên tắc FEFO trong kho dược được áp dụng như thế nào?',
      'FEFO ưu tiên xuất lô có hạn dùng hoặc ngày tái kiểm sớm nhất trước, đồng thời vẫn duy trì nhận diện và truy xuất lô. Ngoại lệ phải có lý do, được phê duyệt và ghi nhận để tránh dùng nguyên liệu hết hạn.',
      array['FEFO', 'hạn dùng', 'ngày tái kiểm', 'truy xuất lô', 'ngoại lệ', 'phê duyệt']::text[],
      'storage'
    ),
    (
      'Khi xảy ra excursion nhiệt độ trong vận chuyển lạnh, lô hàng phải được xử lý thế nào?',
      'Lô phải được cách ly, bảo toàn dữ liệu nhiệt độ và ghi nhận thời gian, mức độ excursion. QA phải đánh giá dựa trên dữ liệu ổn định, điều kiện vận chuyển và lịch sử lô trước khi quyết định chấp nhận, tái xử lý hoặc loại bỏ.',
      array['excursion', 'cách ly', 'dữ liệu nhiệt độ', 'đánh giá QA', 'dữ liệu ổn định', 'quyết định lô']::text[],
      'cold_chain'
    ),
    (
      'Thiết bị pha chế sau mỗi lô phải được vệ sinh và xác nhận tình trạng như thế nào?',
      'Thiết bị phải được vệ sinh theo SOP đã phê duyệt trong thời gian quy định, kiểm tra sạch bằng phương pháp xác định và gắn nhãn trạng thái gồm thiết bị, ngày giờ, người vệ sinh và thời hạn sạch. Hoạt động phải được ghi trong logbook.',
      array['SOP vệ sinh', 'thời gian quy định', 'kiểm tra sạch', 'nhãn trạng thái', 'thời hạn sạch', 'logbook']::text[],
      'equipment_cleaning'
    ),
    (
      'Nhãn trạng thái sạch hoặc bẩn của thiết bị cần có thông tin gì?',
      'Nhãn phải nhận diện thiết bị, trạng thái sạch hoặc bẩn, sản phẩm và lô trước nếu liên quan, ngày giờ hoàn thành, người thực hiện, người kiểm tra và thời hạn sử dụng hoặc thời hạn sạch. Nhãn phải rõ ràng và được kiểm soát.',
      array['nhận diện thiết bị', 'trạng thái', 'sản phẩm trước', 'ngày giờ', 'người thực hiện', 'thời hạn sạch']::text[],
      'equipment_cleaning'
    ),
    (
      'Nhật ký sử dụng thiết bị GMP phải ghi những nội dung nào?',
      'Logbook phải ghi ngày giờ, sản phẩm và số lô, hoạt động sử dụng, vệ sinh, hiệu chuẩn hoặc bảo trì, tình trạng trước và sau, sai lệch cùng chữ ký người thực hiện. Các mục phải theo trình tự thời gian và truy xuất được.',
      array['logbook', 'ngày giờ', 'sản phẩm', 'số lô', 'vệ sinh', 'hiệu chuẩn', 'bảo trì', 'chữ ký']::text[],
      'equipment_logbook'
    ),
    (
      'Sản phẩm worst case trong thẩm định vệ sinh được lựa chọn dựa trên tiêu chí nào?',
      'Lựa chọn worst case phải dựa trên đánh giá rủi ro gồm độc tính hoặc PDE, độ hòa tan, khả năng làm sạch, hàm lượng, độ bám dính, diện tích tiếp xúc và tần suất sản xuất. Cơ sở lựa chọn phải được lập tài liệu và phê duyệt.',
      array['worst case', 'đánh giá rủi ro', 'PDE', 'độ hòa tan', 'khả năng làm sạch', 'diện tích tiếp xúc']::text[],
      'cleaning_validation'
    ),
    (
      'Line clearance trước đóng gói phải xác nhận những điểm nào?',
      'Phải xác nhận đã loại bỏ sản phẩm, bao bì, nhãn, mã in và tài liệu của lô trước; khu vực và thiết bị sạch; vật liệu đúng với lô mới; bộ đếm được đặt phù hợp. Kết quả phải được hai người ghi nhận theo hồ sơ lô.',
      array['line clearance', 'bao bì', 'nhãn', 'mã in', 'lô trước', 'thiết bị sạch', 'hai người']::text[],
      'line_clearance'
    ),
    (
      'Chiến lược kiểm soát nhiễm trong cơ sở sản xuất vô trùng cần bao quát những yếu tố nào?',
      'Chiến lược phải tích hợp thiết kế nhà xưởng, luồng người và vật liệu, HVAC, vệ sinh khử khuẩn, giám sát môi trường, kiểm soát nguyên liệu, bảo trì, thẩm định, đào tạo và quản lý xu hướng. Các biện pháp phải dựa trên quản lý rủi ro chất lượng.',
      array['CCS', 'HVAC', 'luồng người', 'khử khuẩn', 'giám sát môi trường', 'thẩm định', 'quản lý rủi ro']::text[],
      'contamination_control'
    ),
    (
      'Nguy cơ nhiễm chéo giữa hai sản phẩm được đánh giá và kiểm soát như thế nào?',
      'Phải đánh giá độc tính, hoạt lực, dạng bào chế, khả năng phát tán, quy trình, thiết bị dùng chung và hiệu quả vệ sinh. Kiểm soát có thể gồm khu vực chuyên biệt, chiến dịch sản xuất, hệ thống kín, chênh áp, vệ sinh đã thẩm định và giới hạn phơi nhiễm dựa trên sức khỏe.',
      array['nhiễm chéo', 'đánh giá rủi ro', 'thiết bị dùng chung', 'hệ thống kín', 'vệ sinh thẩm định', 'HBEL']::text[],
      'cross_contamination'
    ),
    (
      'Khi kết quả giám sát môi trường vượt action limit, cần thực hiện những bước gì?',
      'Phải thông báo, xác nhận và điều tra kịp thời; đánh giá vi sinh vật, vị trí, xu hướng, hoạt động đang diễn ra và tác động tới lô. Cần lập CAPA phù hợp, tăng cường giám sát khi cần và QA quyết định tình trạng lô.',
      array['action limit', 'điều tra', 'định danh vi sinh', 'xu hướng', 'tác động lô', 'CAPA', 'QA']::text[],
      'environmental_monitoring'
    ),
    (
      'Chênh áp giữa các phòng sạch được kiểm soát nhằm mục đích gì và xử lý cảnh báo ra sao?',
      'Chênh áp duy trì hướng dòng khí để bảo vệ sản phẩm hoặc ngăn phát tán nhiễm. Giá trị phải được giám sát theo giới hạn, cảnh báo phải được phản ứng, ghi nhận và điều tra; tác động tới điều kiện phòng và sản phẩm phải được đánh giá.',
      array['chênh áp', 'hướng dòng khí', 'giới hạn', 'cảnh báo', 'điều tra', 'tác động sản phẩm']::text[],
      'cleanroom'
    ),
    (
      'Yêu cầu vệ sinh cá nhân đối với nhân viên vào khu vực sản xuất GMP gồm những gì?',
      'Nhân viên phải tuân thủ tình trạng sức khỏe, rửa và sát khuẩn tay, mặc bảo hộ đúng cấp, không mang trang sức, mỹ phẩm, thức ăn hoặc vật dụng không cho phép. Bệnh hoặc tổn thương có nguy cơ phải được báo cáo và đánh giá trước khi vào khu vực.',
      array['vệ sinh cá nhân', 'rửa tay', 'bảo hộ', 'không trang sức', 'tình trạng sức khỏe', 'báo cáo']::text[],
      'personnel_hygiene'
    ),
    (
      'Quy trình thay trang phục khi vào phòng sạch phải được kiểm soát như thế nào?',
      'Trình tự thay đồ phải được quy định và đào tạo, phân tách vùng sạch bẩn, kiểm tra tính nguyên vẹn của trang phục và tránh chạm bề mặt gây nhiễm. Việc tuân thủ phải được quan sát định kỳ và trang phục phải được giặt, tiệt trùng hoặc thay theo quy định.',
      array['trình tự thay đồ', 'vùng sạch bẩn', 'tính nguyên vẹn', 'tránh nhiễm', 'đào tạo', 'giám sát tuân thủ']::text[],
      'gowning'
    ),
    (
      'Đào tạo nhân viên thực hiện thao tác GMP phải được chứng minh hiệu quả ra sao?',
      'Ngoài ghi nhận tham dự, phải đánh giá hiểu biết và năng lực bằng bài kiểm tra, quan sát thao tác hoặc thực hành có giám sát. Chỉ người đạt yêu cầu mới được phân công độc lập; nhu cầu đào tạo lại phải dựa trên thay đổi, sai lệch và đánh giá định kỳ.',
      array['đào tạo', 'đánh giá hiệu quả', 'quan sát thao tác', 'năng lực', 'đào tạo lại', 'phân công']::text[],
      'training'
    ),
    (
      'Một sai lệch trong sản xuất phải được ghi nhận và điều tra theo trình tự nào?',
      'Sai lệch phải được báo cáo ngay, mô tả sự kiện và hành động kiểm soát tức thời, phân loại rủi ro, điều tra nguyên nhân gốc, đánh giá tác động sản phẩm và dữ liệu, đề xuất CAPA, được QA phê duyệt và đóng đúng hạn.',
      array['sai lệch', 'báo cáo ngay', 'kiểm soát tức thời', 'nguyên nhân gốc', 'tác động sản phẩm', 'CAPA', 'QA']::text[],
      'deviations'
    ),
    (
      'CAPA được xem là hoàn thành khi đáp ứng những điều kiện nào?',
      'CAPA chỉ hoàn thành sau khi hành động sửa chữa và phòng ngừa được triển khai đúng hạn, có bằng chứng, không tạo rủi ro mới và đã kiểm tra hiệu lực theo tiêu chí định trước. Kết quả phải được QA rà soát và phê duyệt đóng.',
      array['CAPA', 'bằng chứng', 'đúng hạn', 'kiểm tra hiệu lực', 'tiêu chí định trước', 'QA phê duyệt']::text[],
      'capa'
    ),
    (
      'Một thay đổi thiết bị hoặc quy trình phải được đánh giá trước khi triển khai như thế nào?',
      'Change control phải mô tả lý do và phạm vi, đánh giá rủi ro và tác động tới chất lượng, hồ sơ, thẩm định, đăng ký, đào tạo và chuỗi cung ứng. Các phê duyệt, hành động tiền triển khai, kiểm tra sau triển khai và ngày hiệu lực phải được kiểm soát.',
      array['change control', 'đánh giá rủi ro', 'tác động chất lượng', 'thẩm định', 'đào tạo', 'phê duyệt', 'sau triển khai']::text[],
      'change_control'
    ),
    (
      'Kết quả kiểm nghiệm OOS phải được xử lý như thế nào trước khi thử lại?',
      'Phải tiến hành điều tra phòng kiểm nghiệm kịp thời, bảo toàn dữ liệu và mẫu, kiểm tra tính phù hợp hệ thống, thao tác, thiết bị và tính toán. Chỉ thử lại theo giả thuyết khoa học và kế hoạch được phê duyệt; không được thử lặp đến khi có kết quả đạt.',
      array['OOS', 'điều tra phòng kiểm nghiệm', 'bảo toàn dữ liệu', 'thử lại', 'giả thuyết khoa học', 'không testing into compliance']::text[],
      'oos'
    ),
    (
      'Nguyên tắc ALCOA+ áp dụng cho dữ liệu GMP bao gồm những thuộc tính nào?',
      'Dữ liệu phải có thể quy trách nhiệm, rõ ràng, ghi đồng thời, nguyên gốc và chính xác; đồng thời phải đầy đủ, nhất quán, bền vững và sẵn có trong suốt vòng đời dữ liệu. Kiểm soát phải áp dụng cho cả hồ sơ giấy và điện tử.',
      array['attributable', 'legible', 'contemporaneous', 'original', 'accurate', 'complete', 'consistent', 'enduring', 'available']::text[],
      'data_integrity'
    ),
    (
      'Audit trail của hệ thống GxP phải được rà soát khi nào và tập trung vào nội dung gì?',
      'Tần suất rà soát phải dựa trên rủi ro và phù hợp với việc xem xét dữ liệu hoặc quyết định lô. Rà soát phải tập trung vào tạo, sửa, xóa, quyền truy cập, thay đổi cấu hình, lý do thay đổi, thời gian và người thực hiện; bất thường phải được điều tra.',
      array['audit trail review', 'dựa trên rủi ro', 'sửa xóa', 'quyền truy cập', 'lý do thay đổi', 'người thực hiện', 'điều tra']::text[],
      'audit_trail'
    ),
    (
      'Khi phát hiện thiết bị đo đã hiệu chuẩn nhưng bị out of tolerance, phải làm gì?',
      'Phải ngừng sử dụng và nhận diện thiết bị, đánh giá từ lần hiệu chuẩn đạt gần nhất toàn bộ phép đo và lô có thể bị ảnh hưởng, điều tra nguyên nhân, hiệu chỉnh hoặc sửa chữa và hiệu chuẩn lại. QA phải quyết định hành động đối với dữ liệu và sản phẩm liên quan.',
      array['out of tolerance', 'ngừng sử dụng', 'lần hiệu chuẩn đạt gần nhất', 'đánh giá tác động', 'hiệu chuẩn lại', 'QA']::text[],
      'calibration'
    ),
    (
      'Thiết bị quá hạn bảo trì phòng ngừa có được tiếp tục sử dụng không?',
      'Không được mặc nhiên tiếp tục sử dụng. Thiết bị phải được đánh giá tình trạng và rủi ro, ghi nhận sai lệch, xem xét tác động tới hoạt động từ lần bảo trì trước, hoàn tất bảo trì và kiểm tra chức năng trước khi QA hoặc bộ phận có thẩm quyền cho phép dùng lại.',
      array['quá hạn bảo trì', 'đánh giá rủi ro', 'sai lệch', 'tác động', 'kiểm tra chức năng', 'cho phép dùng lại']::text[],
      'preventive_maintenance'
    ),
    (
      'Các giai đoạn DQ, IQ, OQ và PQ chứng minh điều gì trong thẩm định thiết bị?',
      'DQ chứng minh thiết kế đáp ứng yêu cầu người dùng và GMP; IQ xác nhận lắp đặt đúng; OQ xác nhận vận hành trong các dải và chức năng đã định; PQ chứng minh thiết bị hoạt động hiệu quả, lặp lại trong điều kiện sử dụng thực tế.',
      array['DQ', 'IQ', 'OQ', 'PQ', 'URS', 'lắp đặt', 'vận hành', 'hiệu năng']::text[],
      'qualification'
    ),
    (
      'Thẩm định quy trình tiếp tục được duy trì sau các lô thẩm định ban đầu bằng cách nào?',
      'Phải thực hiện continued process verification bằng thu thập và phân tích xu hướng các thông số trọng yếu, thuộc tính chất lượng, sai lệch, OOS, khiếu nại và độ ổn định. Kết quả được xem xét định kỳ để xác nhận trạng thái kiểm soát và khởi tạo CAPA hoặc tái thẩm định khi cần.',
      array['continued process verification', 'xu hướng', 'CPP', 'CQA', 'trạng thái kiểm soát', 'tái thẩm định']::text[],
      'process_validation'
    ),
    (
      'Một hệ thống máy tính GxP cần những kiểm soát vòng đời nào?',
      'Hệ thống cần URS và đánh giá rủi ro, thẩm định phù hợp mục đích sử dụng, quản lý truy cập theo vai trò, audit trail, sao lưu và khôi phục, quản lý thay đổi, sự cố, tính liên tục, rà soát định kỳ và kế hoạch ngừng hệ thống cùng lưu trữ dữ liệu.',
      array['URS', 'đánh giá rủi ro', 'thẩm định', 'quản lý truy cập', 'audit trail', 'sao lưu', 'quản lý thay đổi', 'rà soát định kỳ']::text[],
      'computerized_system'
    ),
    (
      'Nhà cung cấp nguyên liệu dược phải được phê duyệt và tái đánh giá dựa trên những yếu tố nào?',
      'Việc phê duyệt phải dựa trên mức rủi ro, hồ sơ pháp lý và chất lượng, bảng câu hỏi hoặc audit, lịch sử lô, OOS, khiếu nại, thay đổi và năng lực cung ứng. Tần suất tái đánh giá phải được xác định, lập hồ sơ và có hành động khi hiệu suất suy giảm.',
      array['nhà cung cấp', 'đánh giá rủi ro', 'audit', 'lịch sử lô', 'OOS', 'khiếu nại', 'tái đánh giá']::text[],
      'supplier_qualification'
    ),
    (
      'Nguyên liệu mới nhập kho phải được kiểm soát từ tiếp nhận đến khi được phép sử dụng như thế nào?',
      'Phải kiểm tra phương tiện, bao bì, niêm phong và chứng từ; nhận diện từng lô; đưa vào trạng thái biệt trữ; lấy mẫu theo quy trình; kiểm nghiệm hoặc đánh giá phù hợp; chỉ chuyển sang trạng thái đạt và cấp phát sau quyết định phê duyệt có thẩm quyền.',
      array['tiếp nhận', 'nhận diện lô', 'biệt trữ', 'lấy mẫu', 'kiểm nghiệm', 'phê duyệt', 'cấp phát']::text[],
      'material_control'
    ),
    (
      'Lấy mẫu nguyên liệu ban đầu phải phòng ngừa nhiễm và nhầm lẫn bằng cách nào?',
      'Phải dùng kế hoạch và dụng cụ lấy mẫu phù hợp, khu vực được kiểm soát, làm sạch giữa các lần lấy, nhận diện đúng bao và mẫu, ghi người cùng thời gian lấy, bảo quản mẫu phù hợp và niêm phong lại bao nguyên liệu. Dụng cụ vô trùng hoặc chuyên dụng được dùng khi rủi ro yêu cầu.',
      array['kế hoạch lấy mẫu', 'dụng cụ', 'khu vực kiểm soát', 'nhận diện mẫu', 'niêm phong', 'tránh nhiễm', 'tránh nhầm lẫn']::text[],
      'sampling'
    ),
    (
      'Chương trình độ ổn định đang theo dõi cần xử lý thế nào khi có kết quả bất thường hoặc OOT?',
      'Phải xác minh dữ liệu, điều tra OOT hoặc OOS theo quy trình, đánh giá xu hướng, điều kiện buồng ổn định, phương pháp và các lô liên quan. Tác động tới hạn dùng, điều kiện bảo quản và sản phẩm trên thị trường phải được QA đánh giá và báo cáo cơ quan quản lý khi áp dụng.',
      array['độ ổn định', 'OOT', 'OOS', 'đánh giá xu hướng', 'hạn dùng', 'điều kiện bảo quản', 'QA']::text[],
      'stability'
    ),
    (
      'Khiếu nại chất lượng sản phẩm phải được điều tra và liên kết với dữ liệu nào?',
      'Phải ghi nhận, phân loại rủi ro và điều tra lô bị khiếu nại, hồ sơ sản xuất và kiểm nghiệm, mẫu lưu, lô liên quan, sai lệch, OOS, thay đổi và khiếu nại tương tự. Cần đánh giá tác động thị trường, CAPA, báo cáo và khả năng thu hồi.',
      array['khiếu nại', 'phân loại rủi ro', 'hồ sơ lô', 'mẫu lưu', 'lô liên quan', 'CAPA', 'thu hồi']::text[],
      'complaints'
    ),
    (
      'Hệ thống thu hồi thuốc phải bảo đảm những khả năng nào và được thử nghiệm ra sao?',
      'Hệ thống phải nhanh chóng truy xuất phân phối theo lô, xác định khách hàng và số lượng, truyền thông, thu hồi, biệt trữ hàng trả về, đối chiếu số lượng và báo cáo. Mock recall phải được thực hiện định kỳ với tiêu chí thời gian và mức độ thu hồi để chứng minh hiệu lực.',
      array['thu hồi', 'truy xuất phân phối', 'theo lô', 'đối chiếu', 'mock recall', 'thời gian', 'hiệu lực']::text[],
      'recall'
    ),
    (
      'Tự thanh tra GMP cần được lập kế hoạch, thực hiện và theo dõi như thế nào?',
      'Chương trình phải bao phủ định kỳ các hệ thống GMP dựa trên rủi ro, do người đủ năng lực và độc lập thực hiện. Phát hiện phải được phân loại, giao CAPA và thời hạn, theo dõi đến khi đóng và kiểm tra hiệu lực; kết quả quan trọng phải được báo cáo lãnh đạo.',
      array['tự thanh tra', 'dựa trên rủi ro', 'độc lập', 'phân loại phát hiện', 'CAPA', 'theo dõi đóng', 'kiểm tra hiệu lực']::text[],
      'self_inspection'
    )
)
insert into public.golden_questions (
  id,
  question_text,
  expected_answer,
  expected_sources,
  category
)
select
  gen_random_uuid(),
  seed.question,
  seed.expected_answer,
  seed.expected_keywords,
  seed.category
from seed_data seed
where not exists (
  select 1
  from public.golden_questions existing
  where lower(btrim(existing.question_text)) = lower(btrim(seed.question))
)
on conflict (id) do nothing;

commit;
