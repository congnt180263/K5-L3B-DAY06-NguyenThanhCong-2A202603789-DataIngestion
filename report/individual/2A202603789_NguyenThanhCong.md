# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

- Họ và tên: **Nguyễn Thành Công**
- Mã số sinh viên: **2A202603789**
- Lớp: **L3B**
- Đề tài / Corpus: **Triết học và Thẩm mỹ Toán học — Tác phẩm "A Mathematician's Apology" (G. H. Hardy, 1940)**
- Repo bài nộp: [https://github.com/congnt180263/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion](https://github.com/congnt180263/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion)

---

## Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - *Chủ đề:* Triết học toán học, vẻ đẹp thẩm mỹ của toán học thuần túy và tranh biện về tính hữu dụng trong thực tiễn/chiến tranh.
  - *Nguồn và bản quyền:* Cuốn sách danh tiếng *"A Mathematician's Apology"* của nhà toán học Godfrey Harold Hardy (Cambridge University Press, 1940). Bản điện tử PDF được hiệu đính bởi Mathematical Sciences Society, University of Alberta (2005). Tác phẩm thuộc phạm vi công cộng (**Public Domain**) do tác giả qua đời năm 1947 (hơn 70 năm), hoàn toàn được phép tái phân phối và nghiên cứu học thuật.
  - *Số trang vật lý:* 56 trang PDF (`data/A_Mathematicians_Apology.pdf`).
  - *Quy tắc tính trang:* Trang nội dung hợp lệ được định nghĩa là trang chứa $\ge 50$ ký tự văn bản sau chuẩn hóa và chứa văn bản lập luận của tác phẩm. Hệ thống tự động loại trừ 3 trang đầu không thuộc nội dung chính: trang 1 (bìa và tên tác phẩm), trang 2 (thông tin xuất bản và bản quyền số hóa), trang 3 (trang đề tặng "To J. M. L."). Tổng số trang nội dung hữu ích là **53 trang** (từ trang 4 đến trang 56), vượt xa yêu cầu tối thiểu $\ge 30$ trang của đề bài. Toàn bộ thông tin được ghi nhận chi tiết tại [data/manifest.json](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/data/manifest.json).
- **Chuẩn hóa, lỗi và giới hạn:**
  - *Chuẩn hóa văn bản:* Thực hiện qua hàm `normalize_text()` trong [starter/src/ingestion.py](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/starter/src/ingestion.py): chuẩn hóa Unicode dạng `NFKC`, dùng biểu thức chính quy `(\w+)-\s*\n\s*(\w+)` để hàn gắn các từ bị ngắt dòng có dấu gạch nối, chuẩn hóa khoảng trắng thừa nhưng bảo tồn ranh giới đoạn văn hai dấu ngắt dòng `\n\n`, loại bỏ số trang xuất hiện độc lập ở dòng đầu mỗi trang. Tổng dung lượng văn bản sạch sau chuẩn hóa đạt **99.409 ký tự**.
  - *Lỗi và giới hạn trích xuất:* Thư viện `pypdf` hiển thị cảnh báo `fontTools is required to fully parse the encoding of a CFF Type1 font` liên quan đến phông chữ Courier được sử dụng trong một số đoạn chú thích. Cảnh báo này không làm gián đoạn luồng dữ liệu; 100% nội dung chữ được trích xuất chính xác mà không cần OCR.
- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  - *Embedding model:* Sử dụng `sentence-transformers/all-MiniLM-L6-v2` thông qua thư viện `fastembed` (chạy ONNX runtime trên CPU máy cục bộ), vector có số chiều cố định **384 dimensions**. Model được giữ nguyên vẹn xuyên suốt cả ba chiến lược.
  - *Vector store:* **PostgreSQL 16.16** tích hợp extension **pgvector v0.8.7**, triển khai trên Docker container `day6_student_starter-postgres-1` (ánh xạ cổng 55433).
  - *Metric tìm kiếm:* Cosine Distance (`<=>`), điểm tương đồng ngữ nghĩa: $\text{similarity} = 1 - \text{cosine\_distance}$.
  - *Lệnh chạy tái lập pipeline:*
    ```powershell
    cd starter
    docker compose -p day6_student_starter up -d --wait
    py -m src.run
    ```
  - *Chi phí:* **0.00 USD** (Chạy hoàn toàn local, không phát sinh chi phí gọi cloud API).
- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - *Metadata bắt buộc:* `document_id` (`hardy-1940`), `source` (`data/A_Mathematicians_Apology.pdf`), `page` (số nguyên từ 4 đến 56).
  - *Trường lọc bổ sung:* `section` (kiểu chuỗi, nhận giá trị: `Preface`, `Section 1` đến `Section 29`, và `Note`).
  - *Nguồn giá trị và lý do chọn:* Giá trị `section` được trích xuất tự động từ tiêu đề số mục La Mã/Ả Rập xuất hiện độc lập trên từng trang sách. Tác phẩm của Hardy gồm 29 phần ngắn với các chủ đề triết lý tách biệt rõ rệt (ví dụ: Section 11 bàn về cờ vua, Section 28 bàn về toán học trong chiến tranh, Note ở cuối sách trả lời các nhà phê bình). Trường `section` đóng vai trò siêu dữ liệu có cấu trúc tự nhiên, cho phép người dùng khoanh vùng chính xác phạm vi lập luận trước khi tìm kiếm vector.

---

## Cấu hình và benchmark

- **A / B / C (tham số cụ thể, khác biệt duy nhất B–C):**
  - *Chiến lược A (Fixed Size Chunking):* Sử dụng hàm `fixed_size(chunk_size=500, overlap=50)`. Cắt chuỗi cố định 500 ký tự với độ chồng lấp 50 ký tự; không lọc metadata khi truy xuất. Tổng số sinh ra: **242 chunks**.
  - *Chiến lược B (Paragraph Chunking):* Sử dụng hàm `by_paragraph(max_size=800)`. Tách văn bản theo ranh giới đoạn văn (`\n\n`), bảo toàn tính toàn vẹn của câu và ý tứ; không lọc metadata khi truy xuất. Tổng số sinh ra: **173 chunks**.
  - *Chiến lược C (Paragraph Chunking + Metadata Filter):* Dùng chung bộ chunk và chỉ mục vector với Chiến lược B (**173 chunks**). **Khác biệt duy nhất giữa B và C:** Khi câu truy vấn có chỉ định filter (`filter = {"section": "..."}`), Chiến lược C áp dụng mệnh đề lọc cứng `WHERE metadata->>'section' = %s` trên pgvector để giới hạn phạm vi trước khi xếp hạng cosine. Với các câu không có filter, Chiến lược C truy xuất toàn cục giống hệt Chiến lược B.
- **≥20 câu: phân chia ≥15 dev / ≥5 test, câu metadata filter và cách kiểm chứng evidence:**
  - Bộ benchmark gồm đúng **20 câu hỏi** được định nghĩa tại [benchmark/questions.json](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/benchmark/questions.json).
  - *Phân chia:* **15 câu tập dev** (`q01`–`q15`) và **5 câu tập test độc lập** (`q16`–`q20`).
  - *Phân loại câu hỏi:* Gồm câu trực tiếp (9 câu), câu diễn đạt lại/paraphrase (4 câu), câu điều kiện/ngoại lệ (4 câu), và **3 câu kiểm tra metadata filter** (`q05`, `q11` ở tập dev; `q19` ở tập test).
  - *Kiểm chứng evidence:* 100% các đoạn `evidence_quote` được kiểm chứng tồn tại nguyên văn trên đúng `gold_page` bằng script xác minh tự động [starter/scripts/verify_benchmark.py](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/starter/scripts/verify_benchmark.py) (kết quả kiểm tra: 20/20 PASSED).
- **Tiêu chí chọn chiến lược đã chốt trước khi xem test:**
  - Thứ tự ưu tiên đã chốt trước khi chạy tập test:
    1. Ưu tiên 1: **Evidence Hit@3** trên tập dev cao nhất (yêu cầu tối thiểu $\ge 50\%$).
    2. Ưu tiên 2: **Tính mạch lạc của chunk (Chunk Coherence)** trung bình $\ge 1.5/2.0$ (tránh việc chunk bị xé rách câu làm méo mó ngữ cảnh).
    3. Ưu tiên 3: **Số lượng chunk tối ưu** (ít chunk hơn đồng nghĩa với giảm dung lượng bộ nhớ và chi phí tính toán).

---

## Kết quả

### Bảng 1: Hiệu năng truy xuất và tài nguyên (Retrieval Accuracy & Resources)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| **Strategy A** (Fixed 500/50) | dev | 6/15 (40.0%) | 8/15 (53.3%) | 242 | 5.15s | $0.00 |
| | test | 2/5 (40.0%) | 2/5 (40.0%) | 242 | 5.15s | $0.00 |
| | **all** | **8/20 (40.0%)** | **10/20 (50.0%)** | **242** | **5.15s** | **$0.00** |
| **Strategy B** (Paragraph 800) | dev | 7/15 (46.7%) | 9/15 (60.0%) | 173 | 5.68s | $0.00 |
| | test | 1/5 (20.0%) | 3/5 (60.0%) | 173 | 5.68s | $0.00 |
| | **all** | **8/20 (40.0%)** | **12/20 (60.0%)** | **173** | **5.68s** | **$0.00** |
| **Strategy C** (Paragraph + Filter) | dev | 7/15 (46.7%) | 9/15 (60.0%) | 173 | 5.68s | $0.00 |
| | test | 1/5 (20.0%) | 3/5 (60.0%) | 173 | 5.68s | $0.00 |
| | **all** | **8/20 (40.0%)** | **12/20 (60.0%)** | **173** | **5.68s** | **$0.00** |

*Ghi chú:* File log thí nghiệm đầy đủ được lưu tại [artifacts/experiment_log.csv](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/artifacts/experiment_log.csv) và tóm tắt JSON tại [results/benchmark_summary.json](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/results/benchmark_summary.json).

### Bảng 2: Đánh giá chất lượng thủ công (Manual Audit Summary)

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| **Strategy A** (Fixed 500/50) | 1.10 / 2.0 (n=10) | 15/15 (100.0%) | N/A (Không cấu hình filter) | 0 câu mức 0; 3 câu mức 1; 2 câu mức 2 → **1.40 / 2.0** |
| **Strategy B** (Paragraph 800) | 2.00 / 2.0 (n=10) | 15/15 (100.0%) | N/A (Không cấu hình filter) | 0 câu mức 0; 2 câu mức 1; 3 câu mức 2 → **1.60 / 2.0** |
| **Strategy C** (Paragraph + Filter) | 2.00 / 2.0 (n=10) | 15/15 (100.0%) | **1/1 (100.0%)** (Câu `q19` tuân thủ) | 0 câu mức 0; 2 câu mức 1; 3 câu mức 2 → **1.60 / 2.0** |

- **Đường dẫn file trace chi tiết:**
  - Strategy A: [results/traces_strategy_a.json](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/results/traces_strategy_a.json)
  - Strategy B: [results/traces_strategy_b.json](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/results/traces_strategy_b.json)
  - Strategy C: [results/traces_strategy_c.json](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/results/traces_strategy_c.json)
- **Đường dẫn file nhãn thủ công:** [results/manual_audit.json](file:///c:/Users/DELL/Desktop/Lab06/K5-L3B-DAY06-NguyenThanhCong-2A202603789-DataIngestion/results/manual_audit.json).
- **Cách chọn mẫu thẩm định:**
  - *Mẫu Coherence:* Chọn 10 vị trí trang đầu tiên sắp xếp tăng dần trong danh sách các trang nội dung hợp lệ: `pages = [4, 5, 10, 11, 15, 17, 20, 24, 44, 54]`. Thẩm định chunk bao phủ vị trí đầu của từng trang.
  - *Mẫu Metadata & Grounding:* Đánh giá trên toàn bộ 5 câu hỏi của tập test độc lập (`q16`, `q17`, `q18`, `q19`, `q20`) với 3 chunk hàng đầu (top-3), tương ứng $5 \times 3 = 15$ bản ghi cho mỗi chiến lược.

---

## Phân tích và kết luận

### 1. So sánh chi tiết giữa các chiến lược
- **So sánh A và B (Ảnh hưởng của phương pháp Chunking):**
  - Chuyển từ Fixed Size (500 ký tự) sang Paragraph Chunking (tối đa 800 ký tự) giúp giảm số lượng chunk từ 242 xuống 173 (giảm **28.5%** dung lượng chỉ mục).
  - Độ mạch lạc (Chunk Coherence) tăng vượt bậc từ **1.10 lên 2.00 / 2.0**. Ở Strategy A, việc cắt cứng cơ học tại mốc 500 ký tự khiến 9/10 mẫu bị đứt gãy giữa câu (ví dụ ở trang 5: *"criticism, appreciation is work for second-rate"* bị ngắt cụt, thiếu mệnh đề đối lập *"than that of the men who make"*). Ngược lại, Strategy B tôn trọng ranh giới đoạn văn, bảo toàn cấu trúc mệnh đề trọn vẹn.
  - Về độ chính xác truy xuất toàn cục, Strategy B vượt trội về Evidence Hit@3 (**60.0%** so với 50.0% của A). Tuy nhiên, trên tập test nhỏ, Hit@1 của B giảm xuống 20% do hiện tượng đoạn văn dài bị loãng trọng tâm ngữ nghĩa trước các truy vấn ngắn.
- **So sánh B và C (Ảnh hưởng của Metadata Filter):**
  - Chiến lược B và C dùng chung không gian vector và bộ chunks. Trên 4 câu hỏi không có filter, kết quả của B và C trùng khớp hoàn toàn.
  - Đối với câu hỏi có filter (câu `q19` ở tập test: yêu cầu tìm kiếm trong phần `Note` về tác động của khoa học đến chiến tranh), Strategy C giúp loại bỏ 100% các đoạn bàn về chiến tranh ở các Section khác (như Section 28), đẩy chunk trang 55 từ Rank 3 lên Rank 2 với độ tập trung cao. Tuy nhiên, do kích thước tập test chỉ có 1 câu filter, Hit@1 và Hit@3 tổng thể của B và C không có sự khác biệt về mặt số học.

### 2. Phân tích 2 trường hợp lỗi cụ thể

#### Ví dụ lỗi 1 — Câu `q18` (Tập test, trang nguồn 54, Section 29)
- *Câu hỏi:* `"How does Hardy summarize his life's accomplishment and justification in the conclusion of Section 29?"`
- *Đáp án kỳ vọng:* Hardy khẳng định ông đã đóng góp thêm điều gì đó vào kho tàng tri thức nhân loại và giúp người khác đóng góp thêm, với giá trị chỉ khác biệt về mức độ chứ không khác biệt về bản chất so với sáng tạo của các nghệ sĩ lớn.
- *Bằng chứng nguồn (Trang 54):* `"I have added something to knowledge, and helped others to add more; and that these somethings have a value which differs in degree only, and not in kind, from that of the creations of the great mathematicians..."`
- *Hiện tượng:* **Cả ba chiến lược A, B, C đều trượt hoàn toàn (Hit@1 = False, Hit@3 = False).**
- *Truy vết top-3:* Các chiến lược trả về chunk trang 20 (similarity: 0.334), trang 39 (similarity: 0.312), và trang 16. Chunk trang 54 chỉ đạt similarity ~0.28 và bị loại khỏi top 3.
- *Nguyên nhân kỹ thuật:*
  1. Trang 54 là trang kết luận cuối cùng của tác phẩm, dung lượng rất ngắn (chỉ 325 ký tự sau chuẩn hóa).
  2. Đoạn văn mang tính triết lý trừu tượng cao; các từ khóa trong câu hỏi (`accomplishment`, `justification`, `conclusion`) không trùng lặp từ vựng trực tiếp với các từ trong đoạn văn (`added something to knowledge`).
  3. Mô hình `all-MiniLM-L6-v2` (384 chiều) có năng lực biểu diễn ngữ nghĩa giới hạn trên văn phong văn học cổ điển thế kỷ 20, dẫn đến việc các đoạn dài ở trang 20 và 39 chứa nhiều lần từ khóa `"mathematician"`, `"knowledge"`, `"creation"` đạt điểm cosine cao hơn nhờ mật độ từ vựng.

#### Ví dụ lỗi 2 — Câu `q16` (Tập test, trang nguồn 44, Section 26)
- *Câu hỏi:* `"What elementary branches of school mathematics does Hardy classify as genuinely useful in practical everyday life?"`
- *Đáp án kỳ vọng:* Số học, đại số sơ cấp, hình học Euclid sơ cấp, và phép tính vi tích phân sơ cấp.
- *Bằng chứng nguồn (Trang 44):* `"First, the bulk of school mathematics, arithmetic, elementary algebra, elementary Euclidean geometry, elementary differential and integral calculus."`
- *Hiện tượng:* Strategy A đạt **Hit@1 = True**, nhưng Strategy B và C lại nhận **Hit@1 = False** (chỉ đạt Hit@3 ở Rank 2).
- *Truy vết top-3:* Ở Strategy B và C, Rank 1 thuộc về chunk trang 36 (Section 21) với similarity 0.5218; chunk chứa evidence ở trang 44 chỉ xếp Rank 2 với similarity 0.4932.
- *Nguyên nhân kỹ thuật:*
  1. Trang 44 gồm 2 đoạn văn: đoạn 1 bàn về ngành dệt may công nghiệp; đoạn 2 liệt kê các môn toán phổ thông. Khi áp dụng `by_paragraph(max_size=800)`, đoạn 2 được gộp với dung lượng 712 ký tự, pha trộn giữa lập luận lý thuyết và danh sách môn học.
  2. Ở trang 36, đoạn văn thảo luận thuần túy về thuật ngữ `"school mathematics"` và tính thực dụng sơ cấp, tạo ra một dense vector có khoảng cách rất gần với câu hỏi của người dùng.
  3. Đây là ví dụ kinh điển về sự đánh đổi (**Trade-off**) của RAG: Strategy B bảo toàn cấu trúc đoạn văn giúp tăng Coherence, nhưng lại làm loãng mật độ thông tin tập trung, khiến một đoạn văn ở trang khác có sự tương đồng bề mặt cao hơn chiếm vị trí Rank 1. Strategy A vô tình cắt cứng tại mốc 500 ký tự đã cô lập danh sách môn học thành một chunk nhỏ có mật độ từ khóa rất cao.

### 3. Chiến lược được chọn, đánh đổi và điều kiện áp dụng
- **Chiến lược được lựa chọn:** **Chiến lược B (Paragraph Chunking, max 800 ký tự)** là chiến lược tối ưu nhất để đưa vào vận hành thực tế.
- **Lý do lựa chọn:**
  - Đạt tiêu chí ưu tiên cao nhất đã đề ra: **Evidence Hit@3 đạt 60.0%** trên toàn bộ benchmark (vượt trội so với 50.0% của Strategy A).
  - Đạt điểm chất lượng thông tin nền (Grounding Quality) cao nhất: **1.60 / 2.0**.
  - Tính mạch lạc tuyệt đối: **Coherence đạt 2.00 / 2.0**, loại bỏ hoàn toàn hiện tượng câu văn bị xé rách cụt lủn làm biến dạng ngữ nghĩa.
  - Tiết kiệm **28.5% tài nguyên vector store** so với Strategy A.
- **Đánh đổi chấp nhận:**
  - Chấp nhận sự sụt giảm Hit@1 trên một số câu hỏi có danh sách ngắn (như câu `q16`) để đổi lấy ngữ cảnh trọn vẹn cho tầng sinh ngôn ngữ (LLM generation) phía sau.
- **Điều kiện áp dụng:** Phù hợp nhất cho các tài liệu học thuật, văn kiện pháp lý, chính sách và sách chuyên khảo có cấu trúc đoạn văn rõ ràng. Nếu người dùng cung cấp thêm thông tin mục/chương từ giao diện, kích hoạt cơ chế lọc của **Chiến lược C** để tăng độ chính xác phân vùng.

### 4. Hạn chế của dữ liệu, nhãn và phương pháp đo
- *Tập test nhỏ (5 câu):* Tập test chỉ gồm 5 câu nhằm phục vụ thẩm định thủ công sâu, dẫn đến việc mỗi câu đúng/sai làm thay đổi tỷ lệ tới 20%, tạo ra biên độ dao động thống kê lớn.
- *Rủi ro thiên lệch thẩm định (Auditor Bias):* Người thực hiện gán nhãn thủ công (coherence, metadata, grounding) chính là tác giả xây dựng pipeline. Dù đã áp dụng tiêu chí chấm nghiêm ngặt (0, 1, 2) theo rubric, vẫn tồn tại rủi ro chủ quan nhất định trong việc phân định giữa mức 1 và mức 2.
- *Hạn chế của Embedding Model:* `all-MiniLM-L6-v2` chỉ có 384 chiều và giới hạn cửa sổ ngữ cảnh 256 tokens, gặp khó khăn khi biểu diễn các lập luận triết học ẩn dụ hoặc các trang văn bản cực ngắn (như trang 54).
- *Thời gian và chi phí:* Thời gian đo lường (~5.1s – 5.7s) bao gồm cả độ trễ I/O của container Docker cục bộ trên hệ điều hành Windows; chi phí 0 USD phản ánh mô hình local nhưng chưa tính đến chi phí phần cứng CPU/RAM.

### 5. Đề xuất cải tiến khi mở rộng hệ thống
1. **Áp dụng Hybrid Retrieval (Dense + Sparse):** Kết hợp vector search của MiniLM với bộ tìm kiếm từ khóa BM25 (thông qua `pg_trgm` hoặc `tsvector` có sẵn trong PostgreSQL). Phương pháp này sẽ giải quyết triệt để lỗi ở câu `q18` (bắt chính xác cụm từ *"added something to knowledge"*).
2. **Nâng cấp Embedding Model:** Chuyển đổi sang các mô hình hiện đại hơn như `BAAI/bge-base-en-v1.5` (768 chiều) hoặc `text-embedding-3-small` / `gemini-embedding-001` để tăng khả năng nắm bắt ngữ nghĩa trừu tượng trong văn bản triết học.
3. **Chunking theo cấu trúc phân cấp (Hierarchical Chunking):** Lưu trữ chunk nhỏ (200-300 ký tự) phục vụ truy xuất vector chính xác, nhưng trả về cho LLM cửa sổ ngữ cảnh đoạn văn cha (Parent Document Retriever) để giải quyết xung đột giữa Hit@1 và Coherence như đã thấy ở câu `q16`.
4. **Tự động trích xuất Metadata giàu ngữ cảnh:** Sử dụng LLM trích xuất thêm các thực thể (`entities`: nhà toán học, định lý) và luận điểm chính (`theses`) vào metadata để tăng cường năng lực lọc cho Chiến lược C.

