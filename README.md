# Day 06 · Data Ingestion Engineering

- **Học viên:** Nguyễn Thành Công
- **MSSV:** 2A202603789
- **Lớp:** K5 - L3B
- **Chủ đề / Corpus:** Triết học và Thẩm mỹ Toán học — Tác phẩm *"A Mathematician's Apology"* (G. H. Hardy, 1940)
- **Repo bài nộp:** [https://github.com/congnt180263/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion](https://github.com/congnt180263/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion)
- **Báo cáo cá nhân chi tiết:** [report/individual/2A202603789_NguyenThanhCong.md](report/individual/2A202603789_NguyenThanhCong.md)

---

## 1. Tổng quan Corpus và Dữ liệu

| Thuộc tính | Chi tiết |
|---|---|
| **Tác phẩm** | *A Mathematician's Apology* (G. H. Hardy, 1940) |
| **Bản quyền** | Public Domain (Tác giả qua đời 1947, bản số hóa bởi University of Alberta 2005) |
| **Tổng số trang vật lý** | 56 trang PDF (`data/A_Mathematicians_Apology.pdf`) |
| **Số trang nội dung hợp lệ** | **53 trang** (từ trang 4 đến trang 56, quy tắc: $\ge 50$ ký tự sau chuẩn hóa) |
| **Tổng ký tự sạch** | 99.409 ký tự (Unicode NFKC, nối gạch nối ngắt dòng, chuẩn hóa `\n\n`) |
| **Manifest** | [data/manifest.json](data/manifest.json) |

---

## 2. Hướng dẫn Thiết lập và Chạy Pipeline (Reproducibility)

### Yêu cầu tiên quyết
- Python 3.10+
- Docker & Docker Compose

### Các bước thực hiện

1. **Khởi động Vector Database (PostgreSQL 16 + pgvector):**
   ```powershell
   cd starter
   docker compose -p day6_student_starter up -d --wait
   ```
   *Database chạy tại `127.0.0.1:55433`, database: `day6`, user/pass: `postgres/postgres`.*

2. **Kích hoạt môi trường Python và cài đặt thư viện:**
   ```powershell
   # Trong thư mục starter:
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Kiểm tra trạng thái hệ thống:**
   ```powershell
   python scripts/check_setup.py
   # Kết quả: "Setup OK: Database reachable, pgvector extension installed."
   ```

4. **Chạy toàn bộ Ingestion Pipeline và Benchmark:**
   ```powershell
   python -m src.run
   ```
   Pipeline sẽ tự động nạp PDF, chạy 3 chiến lược dữ liệu (A, B, C), tính toán Hit@1 / Hit@3, cập nhật [artifacts/experiment_log.csv](artifacts/experiment_log.csv) và xuất toàn bộ trace vào thư mục [results/](results/).

5. **Chạy kiểm chứng benchmark và thẩm định thủ công:**
   ```powershell
   # Kiểm chứng 20 câu hỏi khớp 100% evidence trên PDF:
   python scripts/verify_benchmark.py
   # Sinh và cập nhật báo cáo thẩm định thủ công:
   python scripts/generate_audit.py
   ```

---

## 3. Cấu hình Thí nghiệm 3 Chiến lược (A / B / C)

- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (chạy local qua `fastembed` ONNX Runtime), **384 chiều**, metric Cosine Distance (`<=>`).
- **Chi phí phát sinh:** **$0.00** (Hoàn toàn offline local, không gọi API tính phí).

| Chiến lược | Phương pháp Chunking | Metadata Filter khi Query | Số Chunks | Mục đích thử nghiệm |
|---|---|---|:---:|---|
| **Strategy A** | Cố định: `fixed_size(size=500, overlap=50)` | Không áp dụng | **242** | Baseline cơ học phổ biến |
| **Strategy B** | Theo đoạn: `by_paragraph(max_size=800)` | Không áp dụng | **173** | Đánh giá bảo toàn ngữ nghĩa & mạch lạc |
| **Strategy C** | Theo đoạn: `by_paragraph(max_size=800)` | Lọc theo `section` khi query có filter | **173** | Đánh giá tác động khoanh vùng metadata |

*Lưu ý kiểm soát biến số:* Strategy B và C dùng chung 100% không gian vector và chunk index, chỉ khác biệt duy nhất ở việc áp dụng bộ lọc `section` khi truy vấn.

---

## 4. Tóm tắt Kết quả Thử nghiệm

### Hiệu năng Truy xuất (Retrieval Accuracy)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunks | Thời gian |
|---|---|:---:|:---:|:---:|:---:|
| **Strategy A** (Fixed 500/50) | dev | 6/15 (40.0%) | 8/15 (53.3%) | 242 | 5.15s |
| | test | 2/5 (40.0%) | 2/5 (40.0%) | | |
| | **all** | **8/20 (40.0%)** | **10/20 (50.0%)** | | |
| **Strategy B** (Paragraph 800) | dev | 7/15 (46.7%) | 9/15 (60.0%) | 173 | 5.68s |
| | test | 1/5 (20.0%) | 3/5 (60.0%) | | |
| | **all** | **8/20 (40.0%)** | **12/20 (60.0%)** | | |
| **Strategy C** (Paragraph + Filter) | dev | 7/15 (46.7%) | 9/15 (60.0%) | 173 | 5.68s |
| | test | 1/5 (20.0%) | 3/5 (60.0%) | | |
| | **all** | **8/20 (40.0%)** | **12/20 (60.0%)** | | |

### Đánh giá Thẩm định Thủ công 5 Khía cạnh (Manual Audit)

| Strategy | Chunk Coherence (TB / 2.0) | Metadata Đúng & Đủ | Filter Compliance | Grounding Quality (TB / 2.0) |
|---|:---:|:---:|:---:|:---:|
| **Strategy A** | 1.10 / 2.0 | 15/15 (100%) | N/A | 1.40 / 2.0 |
| **Strategy B** | **2.00 / 2.0** | 15/15 (100%) | N/A | **1.60 / 2.0** |
| **Strategy C** | **2.00 / 2.0** | 15/15 (100%) | **1/1 (100%)** | **1.60 / 2.0** |

- **Chiến lược được lựa chọn:** **Chiến lược B (Paragraph Chunking)** vì đạt Evidence Hit@3 cao nhất (60.0%), độ mạch lạc tuyệt đối (2.0/2.0), chất lượng grounding tốt nhất (1.6/2.0) và tiết kiệm 28.5% dung lượng lưu trữ chunk.
- **Phân tích đánh đổi & ví dụ lỗi:** Xem chi tiết 2 ca lỗi kinh điển (`q18` - short text triết học bị chìm; `q16` - trade-off giữa paragraph coherence và keyword density) trong [Báo cáo cá nhân](report/individual/2A202603789_NguyenThanhCong.md).

---

## 5. Cấu trúc Thư mục Nộp bài

```text
├── artifacts/
│   └── experiment_log.csv          # Nhật ký tham số và kết quả 3 chiến lược
├── benchmark/
│   └── questions.json              # 20 câu benchmark (15 dev / 5 test + 3 filter)
├── data/
│   ├── A_Mathematicians_Apology.pdf # Tài liệu gốc 56 trang
│   └── manifest.json               # Manifest kế toán 53 trang nội dung & bản quyền
├── report/
│   └── individual/
│       └── 2A202603789_NguyenThanhCong.md # BÁO CÁO CÁ NHÂN ĐẦY ĐỦ
├── results/
│   ├── benchmark_summary.json      # Tóm tắt chỉ số định lượng
│   ├── manual_audit.json           # Nhãn thẩm định thủ công (coherence, grounding)
│   ├── traces_strategy_a.json      # Trace chi tiết top-3 Strategy A
│   ├── traces_strategy_b.json      # Trace chi tiết top-3 Strategy B
│   └── traces_strategy_c.json      # Trace chi tiết top-3 Strategy C
├── starter/
│   ├── scripts/                    # Scripts kiểm tra setup, verify, audit
│   └── src/                        # Mã nguồn pipeline hoàn chỉnh
├── STUDENT.md                      # Thông tin sinh viên & repo nộp
└── SUBMISSION.md                   # Checklist nộp bài
```
