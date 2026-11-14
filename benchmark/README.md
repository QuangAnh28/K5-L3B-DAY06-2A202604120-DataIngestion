# Benchmark cố định trước retrieval

20 câu: q01–q15 dev, q16–q20 test. Tạo từ PDF năm 2005, không khẳng định pháp luật hiện hành. Evidence giữ nguyên text trích xuất (có khoảng trắng chen trong từ). Mỗi gold đã kiểm tra tồn tại đúng trang. Không có nguồn thay thế đã biết trong corpus; metric containment bảo thủ có thể bỏ sót bằng chứng tương đương, cần đọc trace.

Filter là phạm vi chương được ghi trực tiếp trong câu hỏi: q05 Chương II, q13 Chương III, q18 Chương VII. Giá trị nội bộ được chuẩn hóa bằng Python title(): `Chương Ii`, `Chương Iii`, `Chương Vii`. Không lọc bằng trang, ID tài liệu hay đáp án gold. A/B bỏ filter; C chỉ áp dụng filter nếu câu có yêu cầu.

Chia theo điều: dev và test không trùng điều nhưng có trang/chương chung (q14–q16 trang 24), do đó có rủi ro tương quan cao và tập test nhỏ. Tác giả benchmark là Codex, đã xem gold test khi xây câu hỏi; không dùng kết quả retrieval test để sửa cấu hình. Đây không phải tập test mù với người thiết kế.

Chọn chiến lược trên dev theo Hit@3, sau đó Hit@1, sau đó số chunk ít hơn; nếu vẫn hòa ưu tiên B vì không cần người dùng cung cấp phạm vi filter. Cấu hình cố định A=800 ký tự/overlap100; B=đoạn tối đa1000; C=giống B+filter. Không tối ưu sau khi xem test.

Mẫu coherence: cùng 10 trang đầu (1–10), chọn vị trí bắt đầu điều đầu tiên nếu có, nếu không chọn đầu text trang; chọn chunk đầu tiên bao phủ vị trí. Không chọn theo điểm retrieval. B/C có cùng chunk nên coherence phải giống nhau. Nhãn do Codex đọc và chấm, cần học viên rà soát/xác nhận để đáp ứng phần chấm thủ công của lab.
