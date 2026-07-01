INSERT INTO public.golden_questions (
  question_text,
  expected_answer,
  expected_sources,
  expected_confidence,
  question_language,
  category,
  difficulty
)
VALUES
  (
    'Việc đánh giá ban đầu một nhà cung cấp nguyên liệu dược phải dựa trên những tiêu chí nào?',
    'Việc đánh giá phải dựa trên mức độ rủi ro của nguyên liệu, năng lực pháp lý, hệ thống chất lượng, lịch sử tuân thủ, năng lực kỹ thuật và độ tin cậy của chuỗi cung ứng. Với nguyên liệu hoặc dịch vụ có rủi ro cao, doanh nghiệp phải bổ sung audit phù hợp và phê duyệt của đơn vị chất lượng trước khi mua thường quy.',
    ARRAY['supplier qualification', 'đánh giá rủi ro', 'hệ thống chất lượng', 'audit nhà cung cấp']::text[],
    'HIGH',
    'vi',
    'supplier_qualification',
    'easy'
  ),
  (
    'Danh sách nhà cung cấp được phê duyệt phải được thiết lập và kiểm soát như thế nào?',
    'Danh sách phải nhận diện rõ nhà cung cấp, địa điểm sản xuất, vật tư hoặc dịch vụ được phê duyệt, phạm vi chấp thuận và tình trạng hiện tại. Mọi bổ sung, đình chỉ hoặc loại bỏ phải do người có thẩm quyền phê duyệt, được kiểm soát phiên bản và truyền đạt đến bộ phận mua hàng, kho và chất lượng.',
    ARRAY['approved vendor list', 'nhà cung cấp được phê duyệt', 'kiểm soát phiên bản', 'phạm vi chấp thuận']::text[],
    'HIGH',
    'vi',
    'supplier_qualification',
    'medium'
  ),
  (
    'Khi nhà cung cấp API thông báo thay đổi địa điểm sản xuất, doanh nghiệp dược phải đánh giá và xử lý ra sao?',
    'Thay đổi phải được đưa vào change control để đánh giá tác động đến hồ sơ đăng ký, đặc tính nguyên liệu, tạp chất, phương pháp kiểm nghiệm, thẩm định quy trình và chất lượng thành phẩm. Mức độ đánh giá lại, audit, thử nghiệm so sánh và nhu cầu phê duyệt cơ quan quản lý phải dựa trên rủi ro trước khi chấp nhận lô từ địa điểm mới.',
    ARRAY['supplier change', 'API', 'change control', 'đánh giá tác động', 'địa điểm sản xuất']::text[],
    'MEDIUM',
    'vi',
    'supplier_qualification',
    'hard'
  ),
  (
    'What information should be reviewed during the periodic requalification of a critical supplier?',
    'Periodic requalification should review audit outcomes, incoming-test performance, deviations, complaints, recalls, change notifications, delivery reliability, and regulatory compliance. The review frequency and depth should be risk based, documented, and approved by the quality unit.',
    ARRAY['supplier requalification', 'supplier performance', 'audit findings', 'risk based review']::text[],
    'HIGH',
    'en',
    'supplier_qualification',
    'easy'
  ),
  (
    'When is an on-site supplier audit preferable to a questionnaire or remote assessment?',
    'An on-site audit is preferable when the supplied material is critical, the process is complex, significant quality signals exist, or remote evidence cannot demonstrate adequate control. The documented risk assessment should define the audit scope, auditor competence, follow-up actions, and closure of critical findings.',
    ARRAY['on-site audit', 'remote assessment', 'critical supplier', 'audit scope', 'supplier risk']::text[],
    'MEDIUM',
    'en',
    'supplier_qualification',
    'medium'
  ),
  (
    'Mục đích chính của Báo cáo chất lượng sản phẩm hằng năm hoặc PQR là gì?',
    'APR/PQR xác nhận tính nhất quán của quy trình hiện hành, sự phù hợp của tiêu chuẩn và khả năng duy trì trạng thái kiểm soát của sản phẩm. Báo cáo cũng phải nhận diện xu hướng bất lợi, cơ hội cải tiến và nhu cầu CAPA, thay đổi hoặc tái thẩm định.',
    ARRAY['APR', 'PQR', 'trạng thái kiểm soát', 'xu hướng sản phẩm', 'cải tiến liên tục']::text[],
    'HIGH',
    'vi',
    'annual_product_review',
    'easy'
  ),
  (
    'APR/PQR cần tổng hợp và đánh giá tối thiểu những nhóm dữ liệu nào?',
    'Báo cáo phải xem xét các lô sản xuất và loại bỏ, kết quả IPC và thành phẩm, OOS/OOT, sai lệch, CAPA, thay đổi, độ ổn định, khiếu nại, thu hồi và tình trạng thẩm định. Dữ liệu phải được phân tích theo xu hướng, so sánh với kỳ trước và dẫn đến kết luận hoặc hành động có trách nhiệm, thời hạn rõ ràng.',
    ARRAY['APR', 'PQR', 'OOS', 'OOT', 'sai lệch', 'độ ổn định', 'phân tích xu hướng']::text[],
    'HIGH',
    'vi',
    'annual_product_review',
    'medium'
  ),
  (
    'Nếu PQR cho thấy nhiều lô vẫn đạt tiêu chuẩn nhưng Cpk giảm liên tục, đơn vị chất lượng phải phản ứng thế nào?',
    'Xu hướng giảm năng lực phải được đánh giá như một tín hiệu suy giảm trạng thái kiểm soát dù chưa có lô OOS. Doanh nghiệp cần điều tra nguyên nhân, đánh giá rủi ro đối với lô đã phân phối, xác định CAPA và tăng cường continued process verification hoặc tái thẩm định khi có căn cứ.',
    ARRAY['PQR', 'Cpk', 'xu hướng bất lợi', 'CAPA', 'continued process verification']::text[],
    'MEDIUM',
    'vi',
    'annual_product_review',
    'hard'
  ),
  (
    'How often should an Annual Product Review or Product Quality Review be performed?',
    'An APR or PQR is normally prepared at least annually for each marketed product, with grouping allowed only when scientifically justified and permitted by the applicable system. The review period, included batches, missing data, conclusions, and follow-up actions should be clearly documented.',
    ARRAY['Annual Product Review', 'Product Quality Review', 'annual review', 'product quality']::text[],
    'HIGH',
    'en',
    'annual_product_review',
    'easy'
  ),
  (
    'How should PQR findings be linked to continued process verification?',
    'PQR should aggregate CPV signals and determine whether critical process parameters and quality attributes remain stable and capable over time. Adverse trends or recurring events should generate documented investigation, CAPA, control-strategy updates, or revalidation decisions.',
    ARRAY['PQR', 'continued process verification', 'CPP', 'CQA', 'control strategy']::text[],
    'HIGH',
    'en',
    'annual_product_review',
    'medium'
  ),
  (
    'Stage 1 của vòng đời thẩm định quy trình bao gồm những hoạt động cốt lõi nào?',
    'Stage 1, Process Design, xây dựng hiểu biết về sản phẩm và quy trình từ phát triển đến quy mô thương mại, đồng thời xác định CPP, CQA và chiến lược kiểm soát. Thiết kế phải dựa trên kiến thức khoa học, quản lý rủi ro chất lượng và dữ liệu phát triển có thể truy xuất.',
    ARRAY['FDA Process Validation 2011', 'Stage 1', 'Process Design', 'CPP', 'CQA', 'control strategy']::text[],
    'HIGH',
    'vi',
    'process_validation_lifecycle',
    'easy'
  ),
  (
    'Stage 2 Process Performance Qualification phải chứng minh điều gì trước sản xuất thường quy?',
    'PPQ phải chứng minh quy trình thương mại, khi vận hành bởi nhân sự được đào tạo với cơ sở vật chất và thiết bị đã thẩm định, có thể tạo sản phẩm đạt chất lượng một cách lặp lại. Protocol phải định trước số lô có căn cứ khoa học, kế hoạch lấy mẫu tăng cường, tiêu chí chấp nhận, xử lý sai lệch và phê duyệt báo cáo.',
    ARRAY['Stage 2', 'PPQ', 'Process Performance Qualification', 'protocol', 'acceptance criteria']::text[],
    'HIGH',
    'vi',
    'process_validation_lifecycle',
    'medium'
  ),
  (
    'Dữ liệu Stage 3 cho thấy một CPP dần tiến sát giới hạn hành động qua nhiều lô thì cần quyết định gì?',
    'Xu hướng phải được điều tra trước khi quy trình mất kiểm soát, bao gồm đánh giá nguyên nhân chung và đặc biệt, tác động đến CQA và mức độ phù hợp của chiến lược kiểm soát. Kết quả có thể yêu cầu CAPA, điều chỉnh kiểm soát đã phê duyệt, tăng tần suất lấy mẫu hoặc tái thẩm định theo change control.',
    ARRAY['Stage 3', 'continued process verification', 'CPP trend', 'state of control', 'revalidation']::text[],
    'MEDIUM',
    'vi',
    'process_validation_lifecycle',
    'hard'
  ),
  (
    'What are the three lifecycle stages described in the FDA 2011 Process Validation guidance?',
    'The lifecycle consists of Stage 1 Process Design, Stage 2 Process Qualification, and Stage 3 Continued Process Verification. Together they establish the commercial process, confirm reproducible performance, and maintain an ongoing state of control.',
    ARRAY['FDA Process Validation 2011', 'Process Design', 'Process Qualification', 'Continued Process Verification']::text[],
    'HIGH',
    'en',
    'process_validation_lifecycle',
    'easy'
  ),
  (
    'How should a significant deviation during a PPQ batch be handled?',
    'The deviation should be documented, scientifically investigated, and assessed for impact on the protocol objectives, product quality, and validity of the PPQ conclusion. A batch that meets release specifications does not automatically qualify as an acceptable PPQ batch, and any replacement batch or protocol change requires documented justification and approval.',
    ARRAY['PPQ deviation', 'Stage 2', 'protocol deviation', 'quality risk assessment', 'PPQ conclusion']::text[],
    'HIGH',
    'en',
    'process_validation_lifecycle',
    'medium'
  ),
  (
    'Biểu đồ kiểm soát được sử dụng như thế nào trong giám sát quy trình dược phẩm?',
    'Biểu đồ kiểm soát biểu diễn dữ liệu theo thời gian cùng đường trung tâm và các giới hạn kiểm soát được tính từ biến thiên của quy trình. Nó giúp nhận biết tín hiệu nguyên nhân đặc biệt và xu hướng cần điều tra, nhưng giới hạn kiểm soát không thay thế giới hạn tiêu chuẩn sản phẩm.',
    ARRAY['SPC', 'control chart', 'giới hạn kiểm soát', 'nguyên nhân đặc biệt']::text[],
    'HIGH',
    'vi',
    'statistical_process_control',
    'easy'
  ),
  (
    'Chỉ số Cpk cao có đủ để kết luận quy trình đang ở trạng thái kiểm soát không?',
    'Không, Cpk chỉ có ý nghĩa đáng tin cậy khi quy trình ổn định về thống kê và dữ liệu đại diện cho điều kiện vận hành dự kiến. Phải đánh giá biểu đồ kiểm soát, cách lấy mẫu, phân bố dữ liệu và các nguyên nhân đặc biệt trước khi dùng Cpk để kết luận năng lực quy trình.',
    ARRAY['Cpk', 'process capability', 'statistical control', 'control chart', 'sampling']::text[],
    'HIGH',
    'vi',
    'statistical_process_control',
    'medium'
  ),
  (
    'Một chuỗi kết quả độ hòa tan vẫn trong tiêu chuẩn nhưng tăng đều về phía giới hạn trên phải được xử lý ra sao?',
    'Chuỗi dữ liệu là tín hiệu OOT tiềm tàng và cần được đánh giá bằng quy tắc xu hướng đã định trước thay vì chờ xuất hiện OOS. Điều tra phải xem xét thay đổi nguyên liệu, thiết bị, phương pháp, điều kiện môi trường và biến thiên quy trình, sau đó xác định CAPA hoặc giám sát tăng cường.',
    ARRAY['OOT trend', 'dissolution', 'SPC', 'trend rule', 'CAPA']::text[],
    'MEDIUM',
    'vi',
    'statistical_process_control',
    'hard'
  ),
  (
    'What is the difference between common-cause and special-cause variation in SPC?',
    'Common-cause variation is inherent in a stable process and usually requires improvement of the overall system. Special-cause variation arises from an identifiable unusual condition and requires timely investigation and removal of that cause before capability is reassessed.',
    ARRAY['common cause variation', 'special cause variation', 'SPC', 'process stability']::text[],
    'HIGH',
    'en',
    'statistical_process_control',
    'easy'
  ),
  (
    'What controls are needed before using Cpk as a continued process verification metric?',
    'The measurement system, sampling plan, subgroup rationale, data integrity, distribution assumptions, and statistical stability should be verified before interpreting Cpk. Alert and action rules should be predefined so that adverse trends initiate investigation rather than retrospective adjustment of limits.',
    ARRAY['Cpk', 'continued process verification', 'measurement system', 'sampling plan', 'statistical stability']::text[],
    'HIGH',
    'en',
    'statistical_process_control',
    'medium'
  ),
  (
    'Thử nghiệm độ kín hệ bao bì nhằm chứng minh điều gì đối với thuốc vô trùng?',
    'Thử nghiệm CCI chứng minh hệ bao bì duy trì hàng rào ngăn vi sinh, khí hoặc ẩm xâm nhập và bảo vệ chất lượng sản phẩm trong suốt vòng đời. Phương pháp và tiêu chí chấp nhận phải phù hợp với loại bao bì, đường rò tới hạn, điều kiện vận chuyển và hạn dùng.',
    ARRAY['container closure integrity', 'CCI', 'sterile product', 'microbial barrier', 'package integrity']::text[],
    'HIGH',
    'vi',
    'container_closure_integrity',
    'easy'
  ),
  (
    'Vì sao phương pháp CCI định lượng thường được ưu tiên hơn microbial ingress test?',
    'Phương pháp xác định như vacuum decay, pressure decay hoặc high-voltage leak detection thường cho kết quả khách quan, nhạy và có thể xác lập giới hạn rò định lượng. Microbial ingress có độ biến thiên sinh học cao hơn nên cần biện minh khoa học nếu được dùng làm phương pháp chính.',
    ARRAY['deterministic CCI', 'vacuum decay', 'pressure decay', 'microbial ingress', 'leak detection']::text[],
    'HIGH',
    'vi',
    'container_closure_integrity',
    'medium'
  ),
  (
    'Headspace analysis cho lọ đông khô có thể hỗ trợ chiến lược CCI trong vòng đời như thế nào?',
    'Phân tích headspace có thể phát hiện thay đổi áp suất hoặc thành phần khí liên quan đến rò rỉ và được liên kết với kích thước khuyết tật đã hiệu chuẩn. Chương trình phải xác lập khả năng phát hiện, tương quan với rò tới hạn và áp dụng tại thời điểm phù hợp sau đóng gói, vận chuyển mô phỏng và nghiên cứu độ ổn định.',
    ARRAY['headspace analysis', 'lyophilized vial', 'CCI lifecycle', 'calibrated leak', 'stability']::text[],
    'MEDIUM',
    'vi',
    'container_closure_integrity',
    'hard'
  ),
  (
    'What should be included in validation of a deterministic container closure integrity method?',
    'Validation should demonstrate specificity, detection capability, precision, robustness, range where applicable, and suitability for the actual package configuration. Positive controls or calibrated defects, equipment qualification, acceptance criteria, and sample handling should be scientifically justified.',
    ARRAY['CCI method validation', 'deterministic method', 'calibrated defect', 'detection limit', 'USP-1207']::text[],
    'HIGH',
    'en',
    'container_closure_integrity',
    'easy'
  ),
  (
    'How should a change in stopper formulation be assessed for container closure integrity?',
    'The change should enter formal change control and be assessed for material compatibility, dimensions, machinability, extractables or leachables, sterilization effects, and seal performance. Comparative CCI studies, stability data, transport simulation, process requalification, and regulatory impact should be addressed before implementation.',
    ARRAY['stopper change', 'container closure integrity', 'change control', 'seal performance', 'extractables leachables']::text[],
    'HIGH',
    'en',
    'container_closure_integrity',
    'medium'
  ),
  (
    'Mức bảo đảm vô trùng SAL 10^-6 có ý nghĩa gì?',
    'SAL 10^-6 biểu thị xác suất lý thuyết không lớn hơn một đơn vị không vô trùng trên một triệu đơn vị sau quy trình tiệt trùng đã thẩm định. Đây là khái niệm xác suất của quá trình và không có nghĩa rằng có thể chứng minh độ vô trùng của từng đơn vị chỉ bằng thử nghiệm thành phẩm.',
    ARRAY['sterility assurance level', 'SAL 10^-6', 'sterilization validation', 'sterility test']::text[],
    'HIGH',
    'vi',
    'sterility_assurance',
    'easy'
  ),
  (
    'Một chương trình media fill cho dây chuyền chiết rót vô trùng phải mô phỏng những điều kiện nào?',
    'APS phải mô phỏng sát quy trình thường quy, bao gồm thời lượng, số ca, tốc độ dây chuyền, kích thước bao bì, số người, thời gian giữ và các can thiệp thường quy lẫn can thiệp khắc phục. Thiết kế phải bao quát điều kiện worst case có căn cứ và môi trường nuôi cấy phải được chứng minh khả năng phát hiện vi sinh.',
    ARRAY['media fill', 'APS', 'aseptic process simulation', 'worst case', 'interventions']::text[],
    'HIGH',
    'vi',
    'sterility_assurance',
    'medium'
  ),
  (
    'Khi một lần media fill xuất hiện đơn vị nhiễm, doanh nghiệp phải xử lý kết quả và sản xuất liên quan thế nào?',
    'Kết quả phải được coi là thất bại hoặc tín hiệu nghiêm trọng theo tiêu chí đã phê duyệt, với điều tra toàn diện về vi sinh vật, can thiệp, nhân sự, môi trường, thiết bị và thao tác. Phải đánh giá tác động đến các lô sản xuất từ lần APS đạt gần nhất, triển khai CAPA và hoàn thành tái xác nhận phù hợp trước khi khôi phục trạng thái kiểm soát.',
    ARRAY['media fill failure', 'contaminated unit', 'APS investigation', 'CAPA', 'aseptic processing']::text[],
    'MEDIUM',
    'vi',
    'sterility_assurance',
    'hard'
  ),
  (
    'How should routine and non-routine interventions be represented in an aseptic process simulation?',
    'The simulation should include qualified routine interventions at representative frequencies and justified non-routine interventions that may occur during operations. Each intervention should be documented, traceable to exposed units, and assessed for its effect on contamination risk.',
    ARRAY['aseptic process simulation', 'routine intervention', 'non-routine intervention', 'contamination risk']::text[],
    'HIGH',
    'en',
    'sterility_assurance',
    'medium'
  ),
  (
    'What factors determine the frequency and number of media fill runs?',
    'The program should consider regulatory expectations, process design, shift patterns, operator participation, line configuration, campaign duration, changes, and prior APS performance. Initial qualification and periodic requalification should provide enough successful runs to demonstrate continued control for each relevant aseptic process.',
    ARRAY['media fill frequency', 'initial qualification', 'periodic requalification', 'APS', 'aseptic process']::text[],
    'HIGH',
    'en',
    'sterility_assurance',
    'medium'
  ),
  (
    'GDP yêu cầu kiểm soát điều kiện bảo quản và vận chuyển thuốc như thế nào?',
    'Thuốc phải được bảo quản và vận chuyển trong các điều kiện do nhà sản xuất hoặc hồ sơ đăng ký quy định, với phương tiện, thiết bị giám sát và tuyến đường đã đánh giá phù hợp. Hồ sơ nhiệt độ, bàn giao, an ninh và mọi excursion phải được lưu giữ để bảo đảm truy xuất và đánh giá chất lượng.',
    ARRAY['GDP', 'Good Distribution Practice', 'vận chuyển thuốc', 'nhiệt độ', 'temperature excursion']::text[],
    'HIGH',
    'vi',
    'good_distribution_practice',
    'easy'
  ),
  (
    'Việc lập bản đồ nhiệt độ kho GDP phải được thiết kế và duy trì ra sao?',
    'Temperature mapping phải khảo sát các mùa hoặc điều kiện đại diện, vị trí nóng lạnh, ảnh hưởng của tải, cửa, HVAC và mất điện để xác định vị trí đặt cảm biến thường quy. Mapping phải được đánh giá lại sau thay đổi đáng kể và thiết bị giám sát phải được hiệu chuẩn, có cảnh báo cùng quy trình phản ứng.',
    ARRAY['GDP warehouse', 'temperature mapping', 'hot spot', 'cold spot', 'calibrated sensor']::text[],
    'HIGH',
    'vi',
    'good_distribution_practice',
    'medium'
  ),
  (
    'Một lô vaccine có excursion nhiệt độ trong vận chuyển nhưng chỉ thị hóa học vẫn đạt thì có thể phóng thích ngay không?',
    'Không thể phóng thích chỉ dựa trên chỉ thị; lô phải được cách ly và đánh giá toàn bộ hồ sơ thời gian-nhiệt độ, độ chính xác thiết bị, dữ liệu ổn định và điều kiện vận chuyển thực tế. Quyết định phải do đơn vị chất lượng có thẩm quyền đưa ra với căn cứ khoa học, đồng thời điều tra nguyên nhân và CAPA đối với hệ thống phân phối.',
    ARRAY['vaccine excursion', 'cold chain', 'stability data', 'quarantine', 'quality decision']::text[],
    'MEDIUM',
    'vi',
    'good_distribution_practice',
    'hard'
  ),
  (
    'What records are necessary to demonstrate traceability in pharmaceutical distribution?',
    'Records should identify the product, batch, quantity, supplier, consignee, dispatch and receipt dates, transport conditions, and responsible parties throughout the distribution chain. The system should support rapid reconciliation, investigation, and targeted recall while protecting records from unauthorized alteration.',
    ARRAY['GDP traceability', 'distribution records', 'batch traceability', 'recall', 'ALCOA+']::text[],
    'HIGH',
    'en',
    'good_distribution_practice',
    'medium'
  ),
  (
    'How should a company qualify a third-party logistics provider handling medicinal products?',
    'Qualification should assess licenses, quality systems, facilities, temperature controls, security, subcontracting, deviation handling, data integrity, and recall capability based on risk. Responsibilities, performance indicators, audit rights, change notification, and record access should be defined in a written quality agreement.',
    ARRAY['3PL qualification', 'GDP', 'quality agreement', 'transport provider', 'supplier audit']::text[],
    'HIGH',
    'en',
    'good_distribution_practice',
    'medium'
  ),
  (
    'Trước khi phóng thích lô thành phẩm, đơn vị chất lượng phải xác minh tối thiểu những nội dung nào?',
    'Phải xác minh hồ sơ sản xuất và đóng gói hoàn chỉnh, kết quả kiểm nghiệm đạt, đối chiếu sản lượng, tình trạng sai lệch, OOS, thay đổi, IPC và điều kiện bảo quản. Chỉ người được ủy quyền mới được quyết định phóng thích sau khi mọi vấn đề ảnh hưởng chất lượng đã được đánh giá và hồ sơ có thể truy xuất.',
    ARRAY['batch release', 'hồ sơ lô', 'OOS', 'sai lệch', 'quality unit']::text[],
    'HIGH',
    'vi',
    'batch_release',
    'easy'
  ),
  (
    'Certificate of Analysis phải được đối chiếu với hồ sơ lô như thế nào trước khi phóng thích?',
    'CoA phải nhận diện đúng sản phẩm, số lô, tiêu chuẩn áp dụng, từng phép thử, giới hạn và kết quả được phê duyệt từ dữ liệu gốc. Việc rà soát phải xác nhận phương pháp còn hiệu lực, không có kết quả bị loại bỏ không có căn cứ và mọi OOS hoặc OOT liên quan đã được đóng phù hợp.',
    ARRAY['Certificate of Analysis', 'CoA', 'batch release', 'raw data', 'specification']::text[],
    'HIGH',
    'vi',
    'batch_release',
    'medium'
  ),
  (
    'Có thể phóng thích lô khi một CAPA liên quan sai lệch của chính lô đó chưa hoàn thành không?',
    'Quyết định phụ thuộc vào việc điều tra đã xác định đầy đủ nguyên nhân, đánh giá tác động và triển khai các hành động ngăn chặn cần thiết trước phóng thích; không được dùng kế hoạch CAPA tương lai để che lấp rủi ro chưa được kiểm soát. Đơn vị chất lượng phải lập luận bằng văn bản rằng lô đáp ứng yêu cầu và phần CAPA còn mở không ảnh hưởng đến an toàn, chất lượng hoặc hiệu lực.',
    ARRAY['batch release decision', 'open CAPA', 'deviation investigation', 'risk assessment', 'quality unit']::text[],
    'MEDIUM',
    'vi',
    'batch_release',
    'hard'
  ),
  (
    'What is the role of a Qualified Person in EU batch certification and release?',
    'The Qualified Person certifies that each batch was manufactured and checked in accordance with GMP, the marketing authorization, and applicable legal requirements. Certification must be documented before release for sale or supply, with deviations and supply-chain responsibilities adequately assessed.',
    ARRAY['Qualified Person', 'QP certification', 'EU GMP', 'batch release', 'marketing authorization']::text[],
    'HIGH',
    'en',
    'batch_release',
    'medium'
  ),
  (
    'Can a batch be released solely because all finished-product test results meet specification?',
    'No, release requires review of the complete manufacturing and packaging history, in-process controls, deviations, investigations, data integrity, and compliance with the authorized process. Finished-product testing is one element of assurance and cannot compensate for an uncontrolled or undocumented process.',
    ARRAY['batch release', 'finished product testing', 'batch record review', 'data integrity', 'GMP compliance']::text[],
    'HIGH',
    'en',
    'batch_release',
    'medium'
  ),
  (
    'Lịch vệ sinh nhà xưởng GMP phải quy định những thông tin cơ bản nào?',
    'Lịch phải xác định khu vực, bề mặt hoặc thiết bị cần vệ sinh, tần suất, phương pháp, hóa chất, nồng độ, thời gian tiếp xúc và người chịu trách nhiệm. Việc thực hiện phải được ghi nhận, kiểm tra và xử lý sai lệch khi bỏ sót hoặc không đáp ứng tiêu chí sạch.',
    ARRAY['cleaning schedule', 'vệ sinh nhà xưởng', 'chất tẩy rửa', 'tần suất vệ sinh']::text[],
    'HIGH',
    'vi',
    'facility_cleaning',
    'easy'
  ),
  (
    'Chương trình pest control trong cơ sở GMP phải được kiểm soát để tránh ảnh hưởng sản phẩm như thế nào?',
    'Chương trình phải dựa trên đánh giá rủi ro, bố trí điểm kiểm soát phù hợp, kiểm tra định kỳ, nhận diện xu hướng và quy định hành động khi phát hiện côn trùng hoặc động vật gây hại. Hóa chất diệt côn trùng phải được phê duyệt, sử dụng bởi người có năng lực và không được gây nguy cơ nhiễm cho nguyên liệu, sản phẩm hoặc khu vực sạch.',
    ARRAY['pest control', 'facility hygiene', 'trend analysis', 'contamination prevention']::text[],
    'HIGH',
    'vi',
    'facility_cleaning',
    'medium'
  ),
  (
    'Khi nào cơ sở sản xuất cần khu vực chuyên biệt hoặc dedicated area thay vì chỉ dựa vào vệ sinh đã thẩm định?',
    'Quyết định phải dựa trên đánh giá độc tính, khả năng gây mẫn cảm, hoạt lực, khả năng phát tán, đặc tính sinh học và khả năng kiểm soát bằng biện pháp kỹ thuật hoặc vệ sinh. Nếu rủi ro không thể kiểm soát đầy đủ bằng giới hạn phơi nhiễm dựa trên sức khỏe và các biện pháp đã thẩm định, phải sử dụng khu vực hoặc thiết bị chuyên biệt theo yêu cầu áp dụng.',
    ARRAY['dedicated area', 'cross contamination', 'HBEL', 'cleaning validation', 'risk assessment']::text[],
    'MEDIUM',
    'vi',
    'facility_cleaning',
    'hard'
  ),
  (
    'How should rotation of disinfectants in a cleanroom be scientifically justified?',
    'The program should be based on facility flora, disinfectant spectrum, sporicidal needs, surface compatibility, contact time, and validated application practices rather than rotation by habit alone. Environmental monitoring trends and efficacy studies should support the selected agents and frequency of sporicide use.',
    ARRAY['disinfectant rotation', 'cleanroom cleaning', 'sporicidal agent', 'environmental monitoring', 'efficacy study']::text[],
    'HIGH',
    'en',
    'facility_cleaning',
    'medium'
  ),
  (
    'What controls are required when cleaning contractors work in a GMP manufacturing facility?',
    'Contract personnel should be qualified, trained in applicable hygiene and contamination controls, supervised, and restricted to authorized areas and materials. Responsibilities, approved procedures, chemicals, records, deviation reporting, and performance monitoring should be defined and periodically reviewed.',
    ARRAY['cleaning contractor', 'GMP training', 'contractor qualification', 'facility cleaning', 'quality agreement']::text[],
    'HIGH',
    'en',
    'facility_cleaning',
    'medium'
  ),
  (
    'Khi tiếp nhận khiếu nại chất lượng từ khách hàng, doanh nghiệp phải thực hiện bước đầu nào?',
    'Khiếu nại phải được ghi nhận kịp thời với thông tin sản phẩm, số lô, người báo cáo, mô tả sự cố, mức độ nghiêm trọng và mẫu hoặc bằng chứng liên quan. Đơn vị chất lượng phải phân loại rủi ro, xác định hành động tức thời và bảo đảm điều tra được khởi tạo trong thời hạn quy định.',
    ARRAY['complaint handling', 'khiếu nại khách hàng', 'phân loại rủi ro', 'product complaint']::text[],
    'HIGH',
    'vi',
    'customer_complaints',
    'easy'
  ),
  (
    'Phân tích xu hướng khiếu nại phải được thực hiện theo những chiều dữ liệu nào?',
    'Xu hướng nên được phân tích theo sản phẩm, dạng lỗi, mức nghiêm trọng, số lô, thị trường, nhà phân phối, thời gian và nguyên nhân gốc, đồng thời chuẩn hóa theo lượng sản phẩm phân phối khi phù hợp. Tín hiệu gia tăng hoặc lặp lại phải được liên kết với PQR, CAPA, quản lý rủi ro và đánh giá khả năng thu hồi.',
    ARRAY['complaint trend', 'trend analysis', 'PQR', 'CAPA', 'recall assessment']::text[],
    'HIGH',
    'vi',
    'customer_complaints',
    'medium'
  ),
  (
    'Ba khiếu nại ở các thị trường khác nhau cùng mô tả lọ thuốc bị nứt nhưng mẫu lưu đạt thì phải đánh giá ra sao?',
    'Mẫu lưu đạt không loại trừ lỗi phát sinh trong phân phối hoặc lỗi không đồng nhất, vì vậy phải mở điều tra liên lô và liên thị trường đối với bao bì, đóng gói, vận chuyển, nhiệt độ và xử lý tại khách hàng. Tín hiệu lặp lại phải kích hoạt đánh giá sức khỏe, phạm vi sản phẩm bị ảnh hưởng, nhu cầu thông báo cơ quan quản lý hoặc thu hồi và CAPA hệ thống.',
    ARRAY['recurring complaint', 'cracked vial', 'retention sample', 'recall trigger', 'cross-market investigation']::text[],
    'MEDIUM',
    'vi',
    'customer_complaints',
    'hard'
  ),
  (
    'What complaint signals should trigger an immediate product recall assessment?',
    'Signals involving potential patient harm, contamination, mix-up, falsification, critical labeling error, loss of sterility, or repeated serious defects should trigger immediate escalation and health-hazard assessment. The company should promptly evaluate affected batches and distribution, notify authorities when required, and document the recall decision even when a recall is not initiated.',
    ARRAY['recall trigger', 'health hazard assessment', 'critical complaint', 'loss of sterility', 'product recall']::text[],
    'HIGH',
    'en',
    'customer_complaints',
    'medium'
  ),
  (
    'How should complaint investigations be connected to CAPA effectiveness checks?',
    'The investigation should identify root cause and define corrections and CAPA proportional to product and patient risk. Effectiveness criteria should include subsequent complaint recurrence, relevant process trends, audit findings, and completion within a predefined monitoring period before final closure.',
    ARRAY['complaint investigation', 'CAPA effectiveness', 'root cause', 'recurrence monitoring', 'complaint closure']::text[],
    'HIGH',
    'en',
    'customer_complaints',
    'medium'
  )
ON CONFLICT DO NOTHING;
