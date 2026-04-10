# Báo Cáo Lab 7: Embedding & Vector Store
**Họ tên:** [Bùi Quang Vinh]  
**Nhóm:** B3-C401  
**Ngày:** 10/04/2026

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**  
Hai vector có cosine similarity cao nghĩa là chúng gần cùng hướng trong không gian embedding, nên thường biểu diễn các đoạn văn có nội dung ngữ nghĩa gần nhau. Với text retrieval, điều này cho thấy hai câu hoặc hai chunk đang nói về cùng một chủ đề hoặc cùng một ý chính.

**Ví dụ HIGH similarity:**
- Sentence A: Biện pháp bảo đảm phát sinh hiệu lực đối kháng khi đăng ký hoặc bên nhận bảo đảm nắm giữ tài sản.
- Sentence B: Hiệu lực đối kháng với người thứ ba xuất hiện từ lúc đăng ký biện pháp bảo đảm hoặc chiếm giữ tài sản bảo đảm.
- Tại sao tương đồng: Hai câu diễn đạt cùng một quy tắc pháp lý của Điều 297, chỉ khác cách dùng từ.

**Ví dụ LOW similarity:**
- Sentence A: Thứ tự ưu tiên thanh toán được xác định theo thứ tự xác lập hiệu lực đối kháng.
- Sentence B: Món ăn này nên được nêm thêm đường và nước mắm trước khi dọn ra bàn.
- Tại sao khác: Một câu thuộc domain pháp lý, câu còn lại là hướng dẫn nấu ăn nên không chia sẻ ngữ cảnh ngữ nghĩa.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**  
Cosine similarity đo độ giống nhau theo hướng của vector thay vì độ lớn tuyệt đối, nên phù hợp hơn với embedding văn bản. Với text, điều quan trọng là hai câu có cùng nghĩa hay không, không phải vector của chúng dài bao nhiêu.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*  
> `step = chunk_size - overlap = 500 - 50 = 450`  
> `num_chunks = ceil((10000 - 50) / 450) = ceil(9950 / 450) = ceil(22.11) = 23`
>
> *Đáp án:* `23 chunks`

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**  
Khi overlap tăng lên 100 thì `step = 400`, nên số chunk tăng thành `ceil((10000 - 100) / 400) = 25`. Overlap lớn hơn giúp giữ ngữ cảnh ở ranh giới giữa các chunk tốt hơn, đổi lại phải lưu trữ nhiều chunk hơn.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Luật dân sự 2015, tập trung vào các quy định và tham luận về biện pháp bảo đảm thực hiện nghĩa vụ

**Tại sao nhóm chọn domain này?**
> Nhóm chọn domain luật dân sự vì đây là lĩnh vực có cấu trúc điều khoản rõ ràng nhưng nội dung lại dày đặc thuật ngữ chuyên môn, rất phù hợp để so sánh hiệu quả của các chiến lược chunking và retrieval. Bộ tài liệu về BLDS 2015 vừa có tính thực tiễn cao, vừa cho phép benchmark bằng các câu hỏi bám theo Điều/Khoản cụ thể như Điều 292, 293, 295, 297 và 308. Ngoài ra, đây cũng là domain mà việc giữ đúng ngữ cảnh pháp lý quan trọng hơn nhiều so với việc chỉ chia đều theo số ký tự.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | Tài liệu Bộ luật DS 2015 — Tham luận về biện pháp bảo đảm | Tổng hợp tham luận hội thảo BLDS 2015 | 140,820 | `doc_type=legal`, `lang=vi`, `category=bao_dam`, `source`, `chunk_index` |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `doc_type` | string | `legal` | Giúp lọc đúng tài liệu pháp lý và tránh lẫn với tài liệu khác domain |
| `lang` | string | `vi` | Hữu ích khi chọn embedding backend và xử lý đúng tiếng Việt |
| `chunk_index` | int | `42` | Giúp truy vết vị trí chunk trong tài liệu gốc và hiển thị thêm context lân cận |
| `source` | string | `Tài liệu Bộ luật DS 2015.md` | Giúp trích dẫn nguồn và kiểm tra lại đoạn luật gốc khi trả lời |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Mình chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu: `Tài liệu Bộ luật DS 2015.md`, `data/vi_retrieval_notes.md`, và `data/rag_system_design.md`. Hai tài liệu còn lại cho xu hướng tương tự, nhưng bảng dưới đây tập trung vào tài liệu pháp lý chính vì đây là bộ dữ liệu dùng cho benchmark retrieval.

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| Tài liệu Bộ luật DS 2015.md | FixedSizeChunker (`fixed_size`) | 123 | 1194.5 | Trung bình |
| Tài liệu Bộ luật DS 2015.md | SentenceChunker (`by_sentences`) | 223 | 629.8 | Khá thấp |
| Tài liệu Bộ luật DS 2015.md | RecursiveChunker (`recursive`) | 173 | 810.9 | Khá |

### Strategy Của Tôi

**Loại:** custom strategy `VietnameseLegalChunker`

**Mô tả cách hoạt động:**  
`VietnameseLegalChunker` không chia văn bản luật theo số ký tự cố định ngay từ đầu, mà chia theo các “điểm neo” pháp lý của tài liệu. Thuật toán trước hết chuẩn hóa xuống dòng và tách riêng các marker như `Điều`, `Khoản`, `Điểm`, `Tình huống`, `Nhận định`, `Quyết định` nếu chúng đang dính trong cùng một đoạn dài. Sau đó văn bản được tách thành các đơn vị nhỏ hơn ở mức paragraph và câu; mỗi đơn vị được gắn nhãn `anchor` nếu nó mở ra một ý pháp lý mới, ví dụ một điều luật, một luận điểm, một tình huống hoặc một phần quyết định.  

Từ các đơn vị này, thuật toán dùng cơ chế `anchor-aware greedy packing`: các đơn vị liên tiếp được gom lại quanh anchor cho đến khi chunk đạt gần kích thước mục tiêu, thay vì dừng ngay ở mỗi ranh giới nhỏ. Nếu gặp một anchor mới và chunk hiện tại đã có đủ context, chunk cũ sẽ được đóng và chunk mới bắt đầu. Chỉ khi một đơn vị vẫn còn quá dài thì nó mới tiếp tục bị tách theo câu, dấu `;`, `:`, `,` hoặc khoảng trắng. Các chunk quá nhỏ sau cùng sẽ được merge lại để tránh việc trả về các mảnh rời rạc thiếu ngữ cảnh. `chunk_size` mặc định được đặt lớn hơn chunking cơ bản, hiện dùng `1200` ký tự, vì văn bản pháp lý cần context dài hơn để giữ nguyên mạch lập luận.

**Tại sao tôi chọn strategy này cho domain nhóm?**  
Văn bản pháp luật và bài tham luận pháp lý ở Việt Nam thường có cấu trúc rất rõ: mở đầu bằng vấn đề pháp lý, sau đó tới điều luật, phân tích, ví dụ, tình huống và kết luận hoặc quyết định. Nếu dùng `FixedSizeChunker`, một luận điểm có thể bị cắt đôi giữa hai câu; còn nếu chỉ tách cứng theo heading thì phần phân tích dài vẫn dễ bị vụn. `VietnameseLegalChunker` khai thác các điểm neo pháp lý này để mỗi chunk chứa một ý pháp lý hoàn chỉnh hơn. Khi user hỏi về “hiệu lực đối kháng”, “cầm giữ tài sản” hay “thứ tự ưu tiên thanh toán”, retriever có khả năng trả đúng chunk chứa luận điểm liên quan thay vì chunk bị cắt giữa hai ý.

**Code snippet (nếu custom):**
```python
class VietnameseLegalChunker:
    def __init__(self, chunk_size: int = 1200, min_chunk_size: int = 200) -> None:
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.target_chunk_size = max(min_chunk_size, int(chunk_size * 0.85))
        self._fallback_chunker = RecursiveChunker(
            separators=["\n\n", "\n", ". ", "; ", ": ", ", ", " ", ""],
            chunk_size=chunk_size,
        )

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        normalized_text = self._prepare_text(text)
        units = self._extract_units(normalized_text)
        if not units:
            return self._fallback_chunker.chunk(normalized_text.strip())
        chunks = self._assemble_chunks(units)
        return self._merge_small_chunks(chunks)

    def _assemble_chunks(self, units: list[tuple[str, bool]]) -> list[str]:
        chunks = []
        current_parts = []
        current_length = 0

        for unit_text, is_anchor in units:
            separator_length = 2 if current_parts else 0
            projected_length = current_length + separator_length + len(unit_text)
            enough_context = current_length >= self.target_chunk_size or len(current_parts) >= 3

            if current_parts and (projected_length > self.chunk_size or (is_anchor and enough_context)):
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
                current_length = 0

            current_parts.append(unit_text)
            current_length = projected_length

        if current_parts:
            chunks.append("\n\n".join(current_parts).strip())
        return chunks
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| Tài liệu Bộ luật DS 2015.md | best baseline: `FixedSizeChunker` | 123 | 1194.5 | Khá, nhưng dễ cắt đôi luận điểm pháp lý và bỏ lỡ mốc Điều/Khoản |
| Tài liệu Bộ luật DS 2015.md | **của tôi: `VietnameseLegalChunker`** | 177 | 792.7 | Tốt hơn, giữ ý pháp lý trọn vẹn; benchmark đạt top-3 relevant `5/5`, retrieval score `9/10` |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Nguyễn Bình Minh | `LegalChunker` | 8/10 | Regex bám rất sát cấu trúc luận điểm pháp lý, giữ được các cụm “Thứ nhất”, “Tình huống”, heading La Mã | Chunk khá lớn (`1500` ký tự) nên có lúc giảm độ chính xác ở câu hỏi cần đúng điều khoản nhỏ |
| Trần Quốc Việt | `LegalDocumentChunker` (structure-aware + hybrid fallback) | 0/10 | Thiết kế hợp domain, có fallback fixed-size + overlap và mô tả giải pháp khá rõ | Benchmark thực tế trong file cho `4/5` query relevant top-3, retrieval lệch nhiều so với gold answer |
| Nguyễn Việt Hoàng | `LegalArticleChunker` / `VietnameseLegalChunker` định hướng article-aware | 9/10 | Kết quả định lượng tốt nhất trong nhóm, `5/5` top-3 relevant, giữ tốt ranh giới Điều/Khoản | Vẫn có query mà top-1 chưa phải chunk tối ưu nhất, đặc biệt với Điều 295 |
| Lê Quang Minh | Chunk nhỏ + real embeddings `text-embedding-3-small` | Không ghi rõ trong file | Dùng embedding thật, nạp `739` chunks nên semantic matching tốt hơn mock embedding | File chỉ có log truy vấn và chưa có bảng benchmark tổng kết, nên khó so sánh định lượng trực tiếp |
| Ngô Quang Phúc | `LegalDocumentChunker` | 8/10 | Chunk trực tiếp theo Điều/Chương, metadata filter hiệu quả, benchmark đạt `4/5` query thành công | Không dùng real embeddings, query khó không có filter còn yếu; chỉ có `5` chunk nên độ phủ chi tiết hạn chế |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> Nếu xét theo số liệu rõ ràng trong file nhóm, strategy của Nguyễn Việt Hoàng cho kết quả tốt nhất vì đạt `5/5` câu có chunk relevant trong top-3 và tổng điểm retrieval `9/10`, đồng thời vẫn giữ được ngữ cảnh pháp lý trọn vẹn. Tuy vậy, nhóm cũng rút ra rằng không chỉ chunking quyết định kết quả: metadata filtering của Ngô Quang Phúc và embedding thật của Lê Quang Minh đều cho thấy hiệu quả rất rõ khi truy vấn các câu hỏi pháp lý cụ thể. Vì thế, hướng tốt nhất cho domain này là kết hợp structure-aware chunking với metadata và một embedding backend tốt.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:  
Mình dùng regex `(?<=[.!?])(?:\s+|\n+)` để tách câu dựa trên dấu kết thúc câu theo sau bởi khoảng trắng hoặc xuống dòng. Sau khi tách, mỗi câu đều được `strip()` và các câu rỗng bị loại bỏ; các câu hợp lệ được gom lại theo `max_sentences_per_chunk`. Edge case chính là text rỗng, nhiều khoảng trắng liên tiếp, và trường hợp mỗi chunk chỉ chứa đúng 1 câu.

**`RecursiveChunker.chunk` / `_split`** — approach:  
Thuật toán thử lần lượt các separator theo thứ tự ưu tiên `["\n\n", "\n", ". ", " ", ""]` để chia văn bản theo các ranh giới ngày càng nhỏ hơn. Trong mỗi mức, code dùng một `buffer` để ghép các mảnh nhỏ miễn là tổng độ dài chưa vượt `chunk_size`; nếu một mảnh vẫn quá dài thì tiếp tục gọi đệ quy với separator tiếp theo. Base case là khi đoạn hiện tại đã đủ ngắn, hoặc đã hết separator, khi đó code cắt thẳng theo `chunk_size`.

### EmbeddingStore

**`add_documents` + `search`** — approach:  
Mỗi `Document` được chuyển thành một record gồm `id`, `doc_id`, `content`, `metadata` và `embedding`, trong đó `doc_id` cũng được copy vào metadata để tiện lọc và xóa. `add_documents` lưu record vào `_store` trong bộ nhớ, và nếu ChromaDB khả dụng thì đồng thời thêm vào collection. Khi search, store embed câu query rồi tính điểm với từng record bằng `_dot`; vì backend mặc định là `_mock_embed` đã normalize vector nên dot product ở đây hoạt động gần như cosine similarity.

**`search_with_filter` + `delete_document`** — approach:  
`search_with_filter` filter trước rồi mới rank, nghĩa là chỉ giữ lại các record có metadata khớp hoàn toàn với `metadata_filter`, sau đó mới chạy `_search_records` trên tập ứng viên còn lại. `delete_document` tìm mọi record có `metadata["doc_id"] == doc_id`, xóa chúng khỏi `_store`, và nếu đang dùng ChromaDB thì gọi thêm `collection.delete()` để đồng bộ.

### KnowledgeBaseAgent

**`answer`** — approach:  
`KnowledgeBaseAgent.answer` gọi `store.search()` để lấy `top_k` chunk liên quan nhất, sau đó ghép thành context với format `[Chunk 1]`, `[Chunk 2]`, ... để LLM biết nguồn nào đang được đưa vào prompt. Prompt được viết theo kiểu RAG tối giản: yêu cầu agent chỉ dùng context đã retrieve để trả lời và phải nói rõ nếu context không đủ. Nếu không retrieve được gì, code chèn câu `"No supporting context was retrieved."` thay vì để prompt rỗng.

### Test Results

```text
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\Work\Day-07-Lab-Data-Foundations
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================= 42 passed in 0.18s ==============================
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Biện pháp bảo đảm phát sinh hiệu lực đối kháng khi đăng ký hoặc bên nhận bảo đảm nắm giữ tài sản. | Hiệu lực đối kháng với người thứ ba xuất hiện từ lúc đăng ký biện pháp bảo đảm hoặc chiếm giữ tài sản bảo đảm. | high | 0.1718 | Yes |
| 2 | Tài sản bảo đảm có thể là tài sản hiện có hoặc tài sản hình thành trong tương lai. | Điều 295 cho phép dùng tài sản hiện có hoặc tài sản sẽ hình thành trong tương lai để bảo đảm nghĩa vụ. | high | -0.1451 | No |
| 3 | Thứ tự ưu tiên thanh toán được xác định theo thứ tự xác lập hiệu lực đối kháng. | Món ăn này nên được nêm thêm đường và nước mắm trước khi dọn ra bàn. | low | 0.0490 | Yes |
| 4 | Nghĩa vụ được bảo đảm toàn bộ bao gồm lãi, tiền phạt và bồi thường thiệt hại. | Phạm vi nghĩa vụ được bảo đảm bao gồm cả trả lãi, tiền phạt và bồi thường thiệt hại nếu không có thỏa thuận khác. | high | 0.0686 | No |
| 5 | BLDS 2015 có 09 biện pháp bảo đảm thực hiện nghĩa vụ. | BLDS 2015 bổ sung bảo lưu quyền sở hữu và cầm giữ tài sản vào các biện pháp bảo đảm. | high | 0.1630 | Yes |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**  
Bất ngờ nhất là cặp 2 và cặp 4: về mặt ngữ nghĩa chúng rất gần nhau nhưng điểm thực tế với backend mặc định lại thấp, thậm chí âm. Điều này cho thấy chất lượng biểu diễn nghĩa phụ thuộc mạnh vào embedding backend; `_mock_embed` hữu ích cho test tính đúng của code, nhưng không đủ tin cậy để đánh giá semantic retrieval thật.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | BLDS 2015 quy định bao nhiêu biện pháp bảo đảm thực hiện nghĩa vụ và gồm những biện pháp nào? | Theo Điều 292 BLDS 2015, có 09 biện pháp bảo đảm thực hiện nghĩa vụ, gồm: cầm cố tài sản, thế chấp tài sản, đặt cọc, ký cược, ký quỹ, bảo lưu quyền sở hữu, bảo lãnh, tín chấp, cầm giữ tài sản. So với BLDS 2005, BLDS 2015 bổ sung thêm bảo lưu quyền sở hữu và cầm giữ tài sản. |
| 2 | Hiệu lực đối kháng với người thứ ba phát sinh khi nào theo BLDS 2015? | Theo khoản 1 Điều 297 BLDS 2015, biện pháp bảo đảm phát sinh hiệu lực đối kháng với người thứ ba kể từ khi đăng ký biện pháp bảo đảm hoặc bên nhận bảo đảm nắm giữ, chiếm giữ tài sản bảo đảm. Khi phát sinh hiệu lực đối kháng, bên nhận bảo đảm có quyền truy đòi tài sản và quyền ưu tiên thanh toán. |
| 3 | Phạm vi nghĩa vụ được bảo đảm theo Điều 293 BLDS 2015 bao gồm những gì? | Theo khoản 1 Điều 293 BLDS 2015, nghĩa vụ có thể được bảo đảm một phần hoặc toàn bộ. Nếu không có thỏa thuận và pháp luật không quy định khác thì nghĩa vụ được bảo đảm toàn bộ, bao gồm nghĩa vụ trả lãi, tiền phạt và bồi thường thiệt hại. Điểm mới là BLDS 2015 bổ sung tiền phạt vào phạm vi nghĩa vụ được bảo đảm. |
| 4 | Tài sản bảo đảm phải đáp ứng những điều kiện gì theo Điều 295 BLDS 2015? | Theo Điều 295 BLDS 2015, tài sản bảo đảm phải thuộc quyền sở hữu của bên bảo đảm (trừ cầm giữ và bảo lưu quyền sở hữu), có thể mô tả chung nhưng phải xác định được, có thể là tài sản hiện có hoặc tài sản hình thành trong tương lai, và có giá trị có thể lớn hơn, bằng hoặc nhỏ hơn giá trị nghĩa vụ được bảo đảm. |
| 5 | Thứ tự ưu tiên thanh toán giữa các bên cùng nhận bảo đảm được xác định như thế nào theo Điều 308 BLDS 2015? | Theo Điều 308 BLDS 2015: nếu các biện pháp bảo đảm đều phát sinh hiệu lực đối kháng thì ưu tiên theo thứ tự xác lập hiệu lực đối kháng; nếu có biện pháp phát sinh hiệu lực đối kháng và có biện pháp không phát sinh thì biện pháp có hiệu lực đối kháng được ưu tiên trước; nếu các biện pháp đều không phát sinh hiệu lực đối kháng thì ưu tiên theo thứ tự xác lập biện pháp bảo đảm. Ngoài ra, các bên có thể thỏa thuận thay đổi thứ tự ưu tiên. |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | BLDS 2015 quy định bao nhiêu biện pháp bảo đảm thực hiện nghĩa vụ và gồm những biện pháp nào? | Điều 292 BLDS 2015 quy định các biện pháp bảo đảm thực hiện nghĩa vụ gồm: cầm cố, thế chấp, đặt cọc, ký cược, ký quỹ, bảo lưu quyền sở hữu, bảo lãnh, tín chấp và cầm giữ tài sản. | 0.7064 | Yes | Agent trả lời đúng 09 biện pháp và nêu được điểm mới của BLDS 2015 là bổ sung bảo lưu quyền sở hữu và cầm giữ tài sản. |
| 2 | Hiệu lực đối kháng với người thứ ba phát sinh khi nào theo BLDS 2015? | Top-1 lấy trúng chunk bàn về hiệu lực đối kháng và thứ tự ưu tiên; trong top-3 có đầy đủ ngữ cảnh Điều 297. | 0.5211 | Yes | Agent trả lời đúng là hiệu lực đối kháng phát sinh từ khi đăng ký biện pháp bảo đảm hoặc bên nhận bảo đảm nắm giữ, chiếm giữ tài sản bảo đảm. |
| 3 | Phạm vi nghĩa vụ được bảo đảm theo Điều 293 BLDS 2015 bao gồm những gì? | Top-1 nằm đúng cụm nội dung về Điều 293 và điểm mới “tiền phạt” trong phạm vi nghĩa vụ được bảo đảm. | 0.5953 | Yes | Agent trả lời đúng nghĩa vụ có thể được bảo đảm một phần hoặc toàn bộ, gồm cả trả lãi, tiền phạt và bồi thường thiệt hại. |
| 4 | Tài sản bảo đảm phải đáp ứng những điều kiện gì theo Điều 295 BLDS 2015? | Top-1 chưa phải chunk tốt nhất, nhưng top-3 có chunk chứa đúng Điều 295 và đủ 4 điều kiện cốt lõi. | 0.4781 | Yes | Agent vẫn trả lời đúng 4 điều kiện của tài sản bảo đảm theo Điều 295, nhưng đây là query yếu nhất trong 5 câu benchmark. |
| 5 | Thứ tự ưu tiên thanh toán giữa các bên cùng nhận bảo đảm được xác định như thế nào theo Điều 308 BLDS 2015? | Top-1 lấy trúng chunk Điều 308, nêu đủ ba trường hợp ưu tiên và khả năng thỏa thuận thay đổi thứ tự ưu tiên. | 0.6372 | Yes | Agent trả lời đúng ba nhánh ưu tiên thanh toán theo Điều 308 và nêu thêm việc các bên có thể thỏa thuận thay đổi thứ tự. |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5

**Actual retrieval score:** 9 / 10

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> Điều mình học được nhiều nhất từ các thành viên khác là chunking tốt cho domain luật không chỉ là “cắt đúng chỗ”, mà còn phải đi cùng metadata và embedding phù hợp. Từ phần của Ngô Quang Phúc, mình thấy metadata filter theo điều luật giúp tăng độ chính xác rất mạnh ở các câu hỏi kiểu “Điều X quy định gì”; từ Lê Quang Minh, mình thấy dùng embedding thật như `text-embedding-3-small` có lợi thế rõ rệt so với mock embedding khi cần semantic retrieval. Ngoài ra, cách Nguyễn Bình Minh dùng nhiều regex để bám các mốc như đề mục La Mã, “Thứ nhất”, “Tình huống” cũng cho thấy chunking theo cấu trúc lập luận pháp lý là hướng rất đáng học.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Qua phần demo và phần tổng hợp trong file nhóm, mình thấy cách đánh giá retrieval hiệu quả nhất là không chỉ nhìn điểm similarity mà phải kiểm tra cả top-1/top-3 hit rate và chất lượng grounding của câu trả lời. Một bài học quan trọng khác là với tài liệu chuyên ngành, chunk theo cấu trúc văn bản gần như luôn tốt hơn cắt đều theo ký tự. Cách so sánh vừa định lượng vừa đọc lại câu trả lời thực tế giúp nhìn rõ strategy nào thật sự dùng được.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**  
Nếu làm lại, mình sẽ gắn thêm metadata ở mức `Điều`, `Khoản`, và loại luận điểm để hỗ trợ filter chính xác hơn cho các câu hỏi có trích dẫn điều luật cụ thể. Mình cũng sẽ benchmark thêm với multilingual embedder thật thay vì chỉ dựa vào backend mặc định, vì phần đánh giá semantic hiện vẫn bị giới hạn bởi `_mock_embed`. Ngoài ra, mình sẽ bổ sung một bước reranking nhẹ để giảm trường hợp top-1 chưa đúng nhất như query về Điều 295.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 9 / 10 |
| Chunking strategy | Nhóm | 13 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 10 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 5 / 5 |
| **Tổng** | | **87 / 100** |
