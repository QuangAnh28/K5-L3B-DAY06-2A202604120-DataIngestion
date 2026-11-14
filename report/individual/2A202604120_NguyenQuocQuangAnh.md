# Báo cáo cá nhân — Data Ingestion Engineering

Họ tên: Nguyễn Quốc Quang Anh. MSSV: 2A202604120. Lớp: L3B.

## Dữ liệu và pipeline

Chủ đề: truy xuất nội dung Luật Thương mại 36/2005/QH11 trong bản PDF năm 2005 do Cục SHTT công bố. Đây là thí nghiệm trên snapshot, không xác nhận nội dung pháp luật hiện hành. File gốc ở `starter/data/luat_thuong_mai_2005.pdf`; URL, SHA256, nguồn/quyền, ngày truy cập và số ký tự từng trang ở `data/manifest.json`. Quyền xử lý căn cứ Điều 15 khoản 2 Luật SHTT: văn bản quy phạm pháp luật không thuộc phạm vi bảo hộ quyền tác giả; không đưa phần biên tập/dịch riêng của bên thứ ba vào corpus.

PDF có 84 trang vật lý. Tính trang 1–83 vì có nội dung điều luật; bỏ trang 84 chỉ chứa 13 ký tự tên người ký. Không có trang hoàn toàn rỗng. Trích xuất pypdf, chuẩn hóa Unicode NFC, khoảng trắng và nối dòng PDF; giữ ranh giới heading/khoản/điểm. Một số từ tiếng Việt bị chèn khoảng trắng do trích xuất font, được giữ nguyên để không đoán nội dung. Không dùng OCR. Lỗi/giới hạn ghi tại `starter/results/processing_log.json`; text theo trang ở `pages.json`.

Mỗi chunk có ID ổn định, document_id, source URL, page vật lý (1-based), year=2005 và chapter lấy từ heading nguồn. Chapter được chuyển tiếp qua trang và tách chung tại ranh giới chương cho cả A/B; không gán chương từ cuối trang cho phần đầu trang. `article`/`section` nếu xuất hiện trong chunk chỉ là nhãn hỗ trợ, không coi là danh sách đầy đủ của mọi điều/mục trong chunk. Filter benchmark chỉ dùng chapter; chuỗi nội bộ `Chương Ii` là kết quả title(), không phải giá trị tự tạo. Schema đầy đủ ở `docs/METADATA_SCHEMA.md` và bảng ở cuối báo cáo.

Từ lượt bổ sung kiểm tra, `event_log.py` ghi tự động `starter/results/runtime_events.jsonl`: UTC timestamp, run ID, stage, loại sự kiện, context nguồn/trang/attempt/status và loại/message lỗi. Có sự kiện bắt đầu/kết thúc, trang ít text, lỗi đọc PDF, HTTP/network, validation và backend vector store; lỗi vẫn được raise, không fallback mock. Không ghi headers, input embedding, vectors hoặc response body lỗi HTTP; key/token/password được che. Các lỗi mô phỏng trong regression tests chỉ ghi vào file tạm, không trộn vào log thực nghiệm. Không tạo ngược log lịch sử cho các lượt chạy trước khi có logger.

Embedding: OpenRouter, `openai/text-embedding-3-small`, 1536 chiều, cùng input text thuần cho query/document, không thêm gold hay prefix, không fallback mock. Dịch vụ không trả revision model cố định; lưu tên model và usage trả về. Vector store: qdrant-client 1.20.0 local persistent, cosine exact; Qdrant quản lý storage nội bộ, không phải SQLite tự viết. Bộ starter pgvector không được sử dụng vì Docker daemon không chạy. Dependencies thực tế ở `starter/requirements-lock.txt`, Python 3.14.10.

## Cấu hình và benchmark

A: fixed-size 800 ký tự, overlap 100. B: ghép đoạn/khoản tối đa 1000 ký tự, đoạn quá dài cắt liên tiếp, không overlap. C: cùng chunk/vector và tham số B, thêm chapter filter khi câu hỏi cung cấp phạm vi. Với câu không filter C giống B. Metadata được giữ cùng schema giữa ba cấu hình. A–B thay cách chia (bao gồm kích thước và overlap), nên đây là so sánh hai cấu hình chunking, không quy toàn bộ khác biệt cho riêng ranh giới đoạn. B–C chỉ thay một yếu tố là filter.

Benchmark cố định tại `benchmark/questions.json`, SHA256 và thời điểm chạy trong run_dev/run_test.json: 15 dev, 5 test; q05/q13/q18 có filter, q18 thuộc test. Gold có đáp án, nguồn, trang và quote tồn tại đúng text nguồn; kiểm tra trước retrieval và kiểm tra lại bằng script. Không có gold thay thế đã biết. Chia theo điều, có trang/chương dùng chung nên không hoàn toàn độc lập. Người thiết kế đã đọc gold test để viết benchmark; không sửa cấu hình bằng điểm test.

Tiêu chí chọn được ghi trước test: ưu tiên dev Hit@3, sau đó Hit@1, số chunk ít hơn, cuối cùng B nếu hòa. C được chốt ở `selection.json` với Hit@3=10/15 và Hit@1=7/15. Test chỉ đánh giá cấu hình đã chốt, không dùng để đổi lựa chọn.

## Kết quả retrieval thực tế

Hit đúng khi một chunk thuộc gold source/trang và chứa đủ quote sau chuẩn hóa khoảng trắng. Hit@3 không dùng hợp nhiều chunk. Đây là metric containment bảo thủ; có thể bỏ sót evidence tương đương trên trang khác. Điểm cosine không phải xác suất.

| Strategy | Split | Hit@1 | Evidence Hit@3 |
|---|---|---|---|
| A | dev | 3/15 | 7/15 |
| B | dev | 6/15 | 10/15 |
| C | dev | 7/15 | 10/15 |
| A | test | 3/5 | 3/5 |
| B | test | 2/5 | 3/5 |
| C | test | 2/5 | 3/5 |

## Tài nguyên và lưu trữ

| Strategy | Chunk count | Tổng ký tự chunk | Min / median / max | Thời gian ingest giây |
|---|---:|---:|---|---:|
| A | 295 | 203008 | 27 / 799 / 800 | 8.932 |
| B | 245 | 182492 | 27 / 848 / 1000 | 8.378 |
| C | 245 | 182492 | 27 / 848 / 1000 | 7.457 |

Thời gian trong bảng lấy lượt test có cache ấm, gồm chunking, lookup cache và hai lần ghi snapshot; không bao gồm trích xuất PDF và không dùng để so sánh tốc độ API lạnh. B/C có ít chunk hơn A: 245 so với 295; A tăng tổng ký tự do overlap. Mỗi lần nạp kiểm tra lại count bằng đúng số chunk; store được đóng/mở lại trước search. Test contract còn kiểm tra đổi corpus loại chunk cũ, filter và persistence. Thay snapshot là clear + upsert, không có transaction toàn bộ; có thể khôi phục bằng chạy lại nếu bị ngắt.

Provider ghi nhận 29 request thành công, 189726 prompt/total tokens và **0.00379452 USD**. Nguồn: `api_usage_dev.json`, `api_usage_test.json`, `cost_summary.json`; không suy giá từ giá niêm yết. Tổng này gồm document và query, dùng cache chung nên không phân bổ chi phí giả cho riêng A/B/C. Tổng token document riêng từng chiến lược không có số đo độc lập vì cache và request batching, chỉ báo tổng usage thực tế. Run lại cùng đầu vào dùng cache; clone mới cần API và phát sinh phí.

## Coherence, metadata và grounding

Nhãn ngữ nghĩa dưới đây do **Codex đọc top-3/chunk rồi chấm và rà soát lần hai theo yêu cầu học viên**, không phải nhãn thủ công của học viên. Không gọi thêm LLM judge API. Lượt hai đọc đủ 30 mẫu coherence, 15 bộ top-3 và 45 bản ghi metadata, đối chiếu text nguồn; kiểm tra trực quan thêm các trang PDF 1, 10, 24, 74, 78, 82. Phương pháp, timestamp, reviewer_kind=AI, review_status=reviewed và lý do từng dòng ở audit JSON cùng `audit_review_round_2.json`; bản chấm cũ lưu ở `audit_history/round_1.json`. Hai nhãn B/C trang 3 được sửa 1→2 vì chunk giữ các câu trọn ý; grounding không đổi. Chỉ sửa nhãn audit, không đổi benchmark/model/chunking dựa vào test. Reviewer đồng thời xây pipeline, biết điểm retrieval nên có nguy cơ thiên lệch, không chấm mù/độc lập.

`student_confirmed` chỉ phản ánh học viên đã trực tiếp đọc/xác nhận, không tự chuyển thành true do ủy quyền cho AI. Trạng thái hiện tại theo bảng dưới: học viên đã kiểm tra và đồng ý với nhãn nào thì bản ghi đó giữ confirmed_by/confirmed_at và nguồn xác nhận. Lượt xác nhận trong chat được lưu riêng trong `audit_student_confirmation.json` nếu có. Vẫn công bố nhãn ban đầu do AI hỗ trợ, không gọi đây là chấm mù hay độc lập. `finalize_artifacts.py` hiện chỉ đọc và kiểm tra audit; không tạo lại score, reason hay confirmation. Nó từ chối dữ liệu nguồn đã đổi hash/mẫu thiếu/trùng, yêu cầu rà soát lại; chỉnh nhãn và custom notes được giữ nguyên từng byte khi tổng hợp lại.

Mẫu coherence chọn trước theo 10 trang đầu: vị trí điều đầu tiên hoặc đầu text nếu không có điều, cùng vị trí cho mọi cấu hình; chọn chunk đầu bao phủ anchor. Mẫu thiên về đầu trang và ít đại diện cho phần cuối corpus. B/C có cùng chunk, vì vậy cùng coherence. Không suy nhãn từ Hit@3.

| Strategy | Coherence trung bình /2 (n) | Metadata đủ/đúng theo Codex | Grounding số mức 0/1/2; trung bình /2 |
|---|---|---|---|
| A | 1.00 (10) | 15/15 | 0/1/4; 1.80 |
| B | 1.20 (10) | 15/15 | 1/1/3; 1.40 |
| C | 1.20 (10) | 15/15 | 1/1/3; 1.40 |

| Audit | Codex đã rà soát | Học viên đã xác nhận |
|---|---|---|
| Coherence | 30/30 | 30/30 |
| Grounding | 15/15 | 15/15 |
| Metadata | 45/45 | 45/45 |

Metadata được Codex đọc lại từng dòng theo source/page/chapter/year, kèm kiểm tra tự động riêng trong `metadata_checks.json`. Chapter được đối chiếu với heading gần nhất qua toàn văn; mỗi bản ghi giữ offset, hash text trang, số trang heading chương và kết quả từng trường. Không phát hiện lỗi trong 45 bản ghi cần kiểm tra; điều này không khẳng định mọi metadata tùy chọn ở toàn corpus là nhãn phạm vi hoàn chỉnh. Source/page giúp mở đúng vị trí đối chiếu; chapter giúp giới hạn chương trước truy xuất. Hạn chế: một chương vẫn rất rộng, page boundary cắt câu và article metadata không bao phủ đầy đủ các điều. Xác nhận của học viên chỉ được ghi theo lời xác nhận thực tế của học viên, không suy ra từ kết quả tự động hay AI.

| Strategy | Filter dev (câu tuân thủ/tổng) | Filter test |
|---|---|---|
| A | 0/2 | 1/1 |
| B | 0/2 | 1/1 |
| C | 2/2 | 1/1 |

Đánh giá filter so top-3 với filter yêu cầu kể cả A/B không áp dụng; tuân thủ tình cờ ở A/B không chứng minh khả năng lọc. Câu không có filter là N/A, không gán 100%. Grounding đọc toàn top-3 theo thang 0 thiếu bằng chứng, 1 có nhưng thiếu ngữ cảnh/điều kiện, 2 đủ trả lời và truy nguồn; không đánh giá câu trả lời LLM.

## Phân tích và kết luận

A–B: B tăng dev Hit@3 từ 7/15 lên 10/15, giảm số chunk từ 295 xuống 245. Giữ đoạn giúp một số quote không bị xé, nhưng không đảm bảo tìm đúng điều. Test cả hai đạt 3/5; A có Hit@1 3/5 cao hơn B 2/5. Coherence vẫn thấp do trang PDF cắt câu và chunk ghép nhiều điều/đầu mục thiếu ngữ cảnh. Không kết luận B luôn tốt hơn A.

B–C: trên dev C tăng Hit@1 từ 6/15 lên 7/15, giữ Hit@3 10/15; trên test không tăng điểm. C chỉ thay phạm vi chương, không giúp phân biệt các điều gần nhau trong cùng chương. Các câu không filter có trace B/C giống nhau đã kiểm tra. C vẫn được chọn theo dev, không đổi sang A dù test Hit@1 của A cao hơn.

Ví dụ lỗi 1 — q18, nguồn trang 78/Điều 301: A lấy một chunk chứa đầu điều và chunk kế tiếp chứa 8% cùng ngoại lệ Điều 266. Không chunk đơn nào chứa toàn quote nên Evidence Hit@3=0, nhưng top-3 hợp lại đủ grounding=2. B/C giữ đủ quote trong một chunk, Hit@3=1. Cần phân biệt metric một chunk và khả năng dùng nhiều bằng chứng.

Ví dụ lỗi 2 — q17, nguồn trang 74/Điều 285: A top-1 chứa hình thức hợp đồng văn bản/tương đương. B/C top-3 ở trang 74–75 chỉ có định nghĩa và quyền/nghĩa vụ nhượng quyền, thiếu hình thức hợp đồng; grounding=0. Chunk dài có thể làm mờ tín hiệu cụ thể.

Ví dụ lỗi 3 — q16, nguồn trang 24/Điều 88: cả ba lấy quy định/biểu hiện khuyến mại ở trang 25, 27, 28, bỏ định nghĩa gold. Có bằng chứng liên quan tới lợi ích khách hàng nhưng thiếu ngữ cảnh định nghĩa nên grounding=1, không sửa gold để tăng điểm.

Nếu mở rộng: cải thiện extraction tiếng Việt dựa trên đối chiếu PDF; chunk theo điều/khoản và liên kết câu qua trang; thêm câu và người chấm độc lập; thử hybrid retrieval trên dev mới. Không áp dụng các đề xuất này để chỉnh tập test đã xem. Không suy rộng chiến lược tốt nhất ra ngoài corpus nhỏ này.

## Tái lập, artifacts và phần học viên cần hoàn tất

Lệnh setup/run/test xem README root. Dữ liệu câu hỏi ở `benchmark/`; cấu hình/giả thuyết/điểm ở `artifacts/experiment_log.csv`. Các trace đầy đủ `starter/results/traces_dev.json`, `traces_test.json`; chunk/text nguồn, nhãn coherence/grounding/metadata, filter audit, usage, resources, run metadata và selection đều ở cùng thư mục results. Database/cache được gitignore; đầu vào và code đủ để tái tạo, cần key API hợp lệ.

Đã chạy contract tests, regression tests về giữ nhãn và ghi lỗi, cùng `verify_outputs.py` và `review_source_checks.py`. Các kiểm tra bảo toàn score/reason/confirmation khi tổng hợp hai lần, từ chối nguồn/mẫu thay đổi, lỗi PDF/provider/store có log và không lộ key đều được thực hiện offline. Kết quả máy và timestamp lưu trong `verification_results.json`. 60 trace, 20 gold evidence, B=C chunks, metadata source/page/chapter/year, filter, hash nguồn và số mẫu audit đều qua. Library Qdrant local phát ResourceWarning sqlite trên Python 3.14 trong unit tests, các assertion và đóng/mở lại store vẫn qua; không che cảnh báo này.

Đã điền họ tên/MSSV và đặt tên báo cáo theo quy ước. Lớp/repo/commit chốt được ghi trong STUDENT.md; xác nhận đọc nhãn được ghi bởi người thực sự rà soát, không suy từ việc giao nhiệm vụ cho AI. Học viên cần hoàn thiện thông tin còn trống và nộp link theo kênh lớp. Key API không được ghi trong report hoặc commit. Công cụ AI đã hỗ trợ viết code, xây benchmark và đọc audit; học viên cần hiểu và giải thích được bài làm theo RULES.md.

## Bảng schema metadata

Nguồn giá trị: PDF Luật Thương mại 36/2005/QH11, manifest và text đã chuẩn hóa. Số trang luôn là số trang vật lý PDF, bắt đầu từ 1. Không lấy gold answer/source làm filter.

| Trường | Kiểu JSON | Bắt buộc | Nguồn giá trị / quy tắc | Mục đích và giới hạn |
|---|---|---|---|---|
| `chunk_id` | string | Có | document_id + page + tham số chunking + SHA1 của nội dung/ordinal | ID ổn định; là thuộc tính chunk, không phải giá trị filter |
| `document_id` | string | Có | `source_id` trong manifest | Truy vết đúng tài liệu; không đưa vào filter benchmark |
| `source` | string (URL) | Có | URL PDF Cục SHTT trong manifest | Truy nguồn tải; nội dung snapshot được xác minh bằng SHA256 |
| `page` | integer >= 1 | Có | Vị trí trang trong `PdfReader.pages` + 1 | Mở đúng trang; không thay bằng số điều |
| `text` | string | Có | Nội dung chuẩn hóa và chia chunk | Payload bằng chứng; khoảng trắng thừa trong từ còn tồn tại |
| `year` | integer | Có với corpus này | 2005, từ số luật 36/2005/QH11 ở trang 1 | Năm văn bản; không phải ngày hiệu lực, không giúp phân biệt khi corpus chỉ có một năm |
| `chapter` | string | Có khi vị trí thuộc một chương | Heading chương gần nhất trước vị trí chunk, chuyển tiếp qua trang; `title()` thành `Chương Ii`… | Filter hữu dụng có nhiều phạm vi; phần mở đầu trước Chương I không có trường này |
| `section` | string | Không | Heading Mục đầu tiên xuất hiện trong text chunk | Chỉ gợi ý heading được chứa trong chunk, không khẳng định toàn bộ chunk thuộc Mục đó; không dùng trong benchmark |
| `article` | string | Không | Heading Điều đầu tiên xuất hiện trong text chunk | Có thể có nhiều điều hoặc đoạn tiếp nối trong một chunk; không phải danh sách đầy đủ, không dùng để lọc benchmark |
| `score` | number | Chỉ ở hit truy xuất | Qdrant cosine similarity, lớn hơn là gần hơn | Dùng xếp hạng; không phải xác suất đúng và không thuộc metadata nguồn |

`DocumentPage.metadata.chapter_before` là giá trị nội bộ trước trang (string hoặc null), được bỏ trước khi lưu chunk. Nó giúp xử lý trang có nhiều chương. Metadata cấp trang như `section` không dùng để suy phạm vi mọi chunk trên trang.

Metadata `chapter` của mỗi hit test được đối chiếu với heading nguồn qua toàn văn, không chỉ kiểm tra có trường. Bộ kiểm tra tự động và kết quả Codex đọc lại được lưu riêng (`metadata_checks.json` và `metadata_audit.json`). Năm/source/ID không được tự tạo ngoài căn cứ manifest và số luật. Xem `audit_review_round_2.json` để biết phương pháp và giới hạn: rà soát AI không thay xác nhận đã đọc của học viên.
