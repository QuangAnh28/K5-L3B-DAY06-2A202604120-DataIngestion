# Schema metadata của bài triển khai

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
