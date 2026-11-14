# Đối chiếu yêu cầu lab sau lượt bổ sung

Học viên: Nguyễn Quốc Quang Anh — 2A202604120. Các mục 1–4 được thực hiện theo yêu cầu: rà soát audit bằng Codex, bảo toàn nhãn, log lỗi tự động và schema metadata. Không suy việc ủy quyền cho AI thành xác nhận rằng học viên đã trực tiếp đọc nhãn.

## Kết quả các việc được yêu cầu

| Việc | Kết quả | Minh chứng |
|---|---|---|
| 1. Rà soát audit | Codex đọc lại 30 chunk coherence, 15 bộ top-3 grounding và 45 bản ghi metadata. Sửa 2 nhãn B/C trang 3 từ 1 thành 2, lý do cũ thiếu chính xác. Grounding giữ nguyên. | `starter/results/audit_review_round_2.json`, các file `*_audit.json`; nhãn trước rà soát ở `audit_history/round_1.json` |
| 2. Giữ nhãn/xác nhận khi tổng hợp | Đã bỏ phần sinh cứng nhãn trong finalize. Chỉ đọc/validate, giữ nguyên từng byte score, reason, ghi chú tùy chỉnh và confirmation. Nguồn hoặc mẫu đổi thì từ chối dùng nhãn cũ. | `src/audit_io.py`; regression test chỉnh nhãn/xác nhận trong fixture rồi tổng hợp 2 lần, dữ liệu giữ nguyên |
| 3. Log lỗi tự động | Có JSONL với timestamp UTC, run ID, stage, context, loại/message lỗi; lưu lỗi PDF/trang, HTTP/network, validation và Qdrant. Lỗi tiếp tục được báo lên, không fallback mock. | `src/event_log.py`, `runtime_events.jsonl`; tests lỗi được mô phỏng ở thư mục tạm, không trộn vào log thật |
| 4. Schema metadata | Có bảng tên trường, kiểu JSON, bắt buộc/tùy chọn, nguồn giá trị, mục đích và giới hạn. Đưa cả vào báo cáo cá nhân. | `docs/METADATA_SCHEMA.md` và phần cuối báo cáo cá nhân |

## Đối chiếu với GUIDE, BENCHMARK, RUBRIC và SUBMISSION

| Yêu cầu | Trạng thái và căn cứ |
|---|---|
| Corpus ≥30 trang, manifest/quyền, snapshot | Đạt phần minh chứng: 84 trang vật lý, tính 83 trang nội dung; loại trang 84 chỉ có tên người ký. Manifest có URL, quyền/căn cứ, accessed_at, SHA256, danh sách trang và số ký tự. SHA256 và text trích xuất được kiểm tra lại. |
| Python đọc/chuẩn hóa/truy vết/ghi lỗi | Đạt: trích xuất lại cả 84 trang khớp text/metadata đã lưu; ID/source/page có trong chunk. Khoảng trắng chen trong từ là giới hạn đã công bố. Logger mới ghi sự kiện thật từ lúc được bổ sung; không tạo ngược log lịch sử. |
| Embedding model thật; không mock | Đạt minh chứng lượt chạy: cùng OpenRouter/model 1536 chiều, có 29 request usage thật, 189726 token và 0.00379452 USD; không đổi model theo chiến lược. Lượt kiểm tra bổ sung không gọi API. |
| Vector store bền vững, cosine và metadata filter | Đạt: Qdrant local quản lý storage, cosine exact; đóng/mở lại store, tái hiện đúng top-3 IDs/score của 60 lượt. Qdrant local dùng SQLite nội bộ không phải SQLite tự quản. |
| ≥3 cấu hình, so sánh có kiểm soát | Đạt: A fixed 800/100, B paragraph 1000/0, C giống B + chapter filter. B/C có cùng chunk/vector; chỉ thay filter. A/B là so sánh toàn cấu hình chunking, không quy tác động riêng cho một tham số. |
| ≥20 câu, 15 dev/5 test, ≥3 filter gồm ≥1 test | Đạt: 20 câu; q05/q13 dev và q18 test có filter lấy trực tiếp từ phạm vi người hỏi cung cấp. Corpus có nhiều chương phân biệt được. |
| Gold/evidence đúng nguồn và không rò gold vào query/filter | Đã kiểm tra: quote tồn tại trên trang, source/page giữ đúng; filter chỉ là chương. Không đổi benchmark/gold/chunking/model khi xem test. Nhiều câu chung chương/trang, rủi ro tương quan và test nhỏ đã được công bố. |
| Trace top-3 và Hit@1/Hit@3 riêng dev/test | Đạt: 60 trace = 20 câu × 3 chiến lược; tính lại từ nội dung hit đúng số đã báo; đối chiếu hash benchmark với run metadata. |
| Coherence cùng 10 vị trí, điểm/lý do | Đủ mẫu/nhãn/lý do và có rà soát AI vòng 2: A=1.00/2, B=C=1.20/2. **Học viên đã xác nhận kiểm tra và đồng ý với nhãn AI hỗ trợ**; không tự xem AI review là human review. |
| Metadata đúng/đủ trên 5 test × top-3 | Đủ 45 bản ghi Codex rà soát cùng kiểm tra độc lập heading nguồn, source/page/year và kiểu dữ liệu; không phát hiện lỗi ở các trường cần thiết. Kết quả AI 15/15 mỗi chiến lược. **Học viên đã xác nhận kiểm tra và đồng ý với metadata audit**. |
| Grounding 5 câu test mỗi cấu hình, điểm/lý do | Đủ 15 nhãn, được đọc lại theo top-3, không suy từ Hit@3. A=1.80/2; B=C=1.40/2. **Học viên đã xác nhận kiểm tra và đồng ý với nhãn AI hỗ trợ**. |
| Data strategy impact, tài nguyên, lỗi và đánh đổi | Đạt nội dung báo cáo: A–B/B–C, số chunk/ký tự, độ dài, thời gian cache ấm và usage/chi phí chung. Có ≥2 ví dụ lỗi với ID/trang. Chi phí không bị phân bổ giả cho các chiến lược dùng chung cache. |
| Chọn trên dev rồi đánh giá test, không chỉnh theo test | Có selection ghi trước run test và cùng hash benchmark. C được chọn theo dev; không đổi sang A dù test Hit@1 của A tốt hơn. Sửa nhãn audit sau đọc nguồn không phải chỉnh cấu hình để tối ưu test. |
| Cách setup/run, dependencies, artifacts và báo cáo | Đạt phần kỹ thuật: có lệnh, lockfile, corpus/manifest, benchmark, experiment log, trace/audit/run/usage/resources. Re-run có thể yêu cầu chấm lại nếu đầu ra nguồn khác hash; không được chỉ đổi hash để bỏ qua. |
| Không lộ secret trong dữ liệu nộp | Scan không phát hiện OpenRouter key trong file text được nộp; `.env`, DB và cache được gitignore. Log che secret, không ghi payload/headers/body lỗi HTTP. Test che key và password đều qua. |
| STUDENT/repo/commit/link nộp | Đã có họ tên/MSSV, lớp L3B và link repo bài nộp trong STUDENT.md. Hash commit bài làm được ghi sau khi tạo commit; xem mục Commit chốt bài trong STUDENT.md. Trạng thái push đối chiếu trên GitHub; chưa xác nhận nộp link qua kênh lớp. |

## Kiểm tra đã thực hiện

Kết quả/timestamp/stdout/stderr máy lưu tại `starter/results/verification_results.json`; kiểm tra sâu nguồn và Qdrant ở `source_verification.json`. Lệnh từ `starter/`:

```powershell
python scripts/run_verification.py --source
```

Đã qua 11 unit/regression tests (2 contract + 9 audit/logging), `verify_outputs.py` và `review_source_checks.py`. Có `ResourceWarning` SQLite của Qdrant local trên Python 3.14; các assertion và persistence/replay đều qua. Không che cảnh báo, không mô tả test mô phỏng provider là request thật. Không phát sinh phí API trong lượt bổ sung.

## Cập nhật xác nhận audit của học viên

Nguyễn Quốc Quang Anh đã xác nhận trong chat: “audit tôi kiểm tra thấy oke rồi”. Đã ghi student_confirmed=true, confirmed_by và confirmed_at cho đủ 30 nhãn coherence, 15 nhãn grounding và 45 bản ghi metadata. Nguồn xác nhận lưu tại `starter/results/audit_student_confirmation.json`. Nhãn ban đầu vẫn công bố là do Codex hỗ trợ; xác nhận này không được mô tả thành chấm mù hoặc chấm độc lập.

Các việc kỹ thuật 2–4 và lượt rà soát audit đã được thực hiện, kiểm thử và học viên xác nhận. Không còn đánh dấu audit là thiếu xác nhận. Học viên vẫn cần hiểu và giải thích bài làm theo RULES.md. Lớp L3B và link repo đã có trong STUDENT.md; hash commit bài làm xem tại mục Commit chốt bài. Hash có ngay sau git commit local; được ghi bằng một commit thông tin bổ sung, không yêu cầu file chứa hash của chính commit đang chứa nó. Nộp link qua kênh giảng viên/coach do học viên thực hiện. Không khẳng định bài đạt 100 điểm hoặc đã nộp cho lớp.
