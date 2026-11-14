# Day 06 · Data Ingestion Engineering

## Bài triển khai với Luật Thương mại 2005

Pipeline đã chạy với **OpenRouter / openai/text-embedding-3-small (1536 chiều)** và **Qdrant local lưu bền vững**, exact cosine. Docker/pgvector trong starter vẫn là tài liệu khởi động tùy chọn; bài triển khai này dùng Qdrant vì Docker daemon chưa chạy trên máy.

Corpus: `starter/data/luat_thuong_mai_2005.pdf`, 84 trang vật lý; dùng trang 1–83, loại trang 84 chỉ có tên người ký. Nguồn/quyền/SHA256 và thống kê trang: `data/manifest.json`. Đây là snapshot luật năm 2005, không khẳng định hiệu lực cập nhật hiện hành.

Chạy trong Windows PowerShell từ root repo:

```powershell
cd starter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
# Chỉ khi chưa có .env: Copy-Item .env.example .env
# Điền OPENROUTER_API_KEY và EMBEDDING_MODEL=openai/text-embedding-3-small trong .env
python scripts/prepare_lab.py
python -m src.run --split dev
```

Sau dev, đọc `results/metrics_dev.json` và chốt lựa chọn vào `results/selection.json` trước khi chạy test. Bài này đã chốt C theo tiêu chí Hit@3 rồi Hit@1, xem `benchmark/README.md`. Muốn chạy lại đúng thí nghiệm đã cố định:

```powershell
python -m src.run --split test
python scripts/finalize_artifacts.py
python scripts/write_report.py
python scripts/test_contracts.py
python scripts/test_review_and_logging.py
python scripts/verify_outputs.py
python scripts/review_source_checks.py
# Hoặc chạy các kiểm tra offline và lưu kết quả vào verification_results.json:
python scripts/run_verification.py --source
```

`python -m src.run` mặc định chỉ chạy dev. Mỗi lượt thay toàn bộ snapshot của từng collection A/B/C, xóa chunk cũ, nạp hai lần kiểm tra số lượng rồi đóng/mở lại store trước retrieval. Thay snapshot không có transaction toàn collection; nếu ngắt giữa chừng cần chạy lại.

`starter/results/qdrant/` chứa DB local, `embedding_cache.json` cache vector theo model/số chiều/text; cả hai được gitignore. Chạy lại cùng đầu vào dùng cache nên không gọi API lần nữa. Bản clone mới tái tạo DB và sẽ phát sinh chi phí API. Cache bị hỏng cần xử lý rõ, không có mock fallback. Không mở hai pipeline đồng thời trên cùng DB.

Kết quả thật: dev Hit@3 A=7/15, B=C=10/15; test Hit@3 cả ba=3/5. Trace đầy đủ và nhãn xem `starter/results/`, báo cáo xem `report/individual/2A202604120_NguyenQuocQuangAnh.md`. Nhãn ngữ nghĩa do Codex hỗ trợ đọc/chấm; học viên đã xác nhận kiểm tra và đồng ý trong chat. Đã ghi `student_confirmed=true`, `confirmed_by` và `confirmed_at` cho 90 bản ghi; xem `starter/results/audit_student_confirmation.json`. Giữ nguyên nguồn gốc AI của nhãn và giới hạn không chấm mù/độc lập. Học viên: Nguyễn Quốc Quang Anh — MSSV 2A202604120 — lớp L3B. Repo bài nộp đã được ghi trong STUDENT.md; commit chốt điền sau khi tạo commit bài làm.

API usage ghi nhận tổng chi phí USD trong `cost_summary.json`; đây là chi phí các request thành công được lưu, chia sẻ cache giữa các chiến lược. Lệnh kiểm thử không gọi API. Key chỉ ở `.env`, không commit. Phiên bản môi trường ở `starter/requirements-lock.txt`.

Lượt rà soát bổ sung: Codex đã đọc lại đủ 30 mẫu coherence, 15 bộ top-3 và 45 bản ghi metadata. Phương pháp, timestamp và thay đổi nhãn ở `starter/results/audit_review_round_2.json`; nhãn cũ được lưu tại `audit_history/round_1.json`. B/C trang 3 sửa coherence từ 1 lên 2, trung bình thành 1.20/2; A vẫn 1.00/2. Nhãn AI có `review_status=reviewed`, `reviewer_kind=AI`; `student_confirmed` không tự đổi thành true. Không chỉnh benchmark/model/chunking hoặc chọn lại chiến lược bằng test.

Các file `coherence_audit.json`, `grounding_audit.json`, `metadata_audit.json` là dữ liệu rà soát được giữ nguyên khi tổng hợp. Muốn sửa score/reason/ghi chú thì chỉnh chính các file đó. Chỉ ghi `student_confirmed=true` và `confirmed_by` sau khi người đó thực sự đọc và xác nhận. `finalize_artifacts.py` kiểm tra hash nguồn/mẫu và tính đầy đủ, rồi cập nhật thống kê; không ghi đè nhãn. Nếu trace/chunk/text nguồn thay đổi, phải chấm lại và lập reference mới, không chỉ thay hash để vượt kiểm tra. Sau chỉnh nhãn chạy finalize rồi write_report; báo cáo lấy điểm từ JSON hiện tại.

Schema metadata, kiểu dữ liệu, nguồn giá trị và giới hạn từng trường có ở [docs/METADATA_SCHEMA.md](docs/METADATA_SCHEMA.md) và trong báo cáo. Log thực `starter/results/runtime_events.jsonl` tự ghi timestamp/run ID/stage/context và lỗi PDF, embedding HTTP/network hoặc vector store. Không lưu input embedding/headers/vectors/body lỗi HTTP, các secret được che. Regression tests mô phỏng lỗi trong thư mục tạm, không ghi chúng thành lỗi provider thật. Không tạo lại log lịch sử cho thời gian trước khi bổ sung logger. Kiểm tra offline không cập nhật benchmark/trace hoặc phát sinh phí API; `review_source_checks.py` cần cache và DB local từ lượt chạy pipeline trước đó.

Phần dưới là hướng dẫn đề bài gốc.

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.
