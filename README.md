# RAG Security

Mã nguồn phục vụ đồ án nghiên cứu cơ chế phát hiện và phòng chống **prompt
injection gián tiếp** và **rò rỉ dữ liệu** trong các hệ thống
Retrieval-Augmented Generation (RAG).

## 1. Stack công nghệ được chốt

Cấu hình mặc định ưu tiên chạy local để thí nghiệm có thể tái lập và không
bắt buộc phải có API key:

| Thành phần | Lựa chọn | Lý do |
| --- | --- | --- |
| LLM mặc định | Ollama + `qwen2.5:3b` | Chạy local, phù hợp giai đoạn phát triển |
| LLM tùy chọn | OpenAI-compatible API | Hỗ trợ OpenAI, vLLM và các server tương thích |
| Mô hình embedding | `intfloat/multilingual-e5-small` | Hỗ trợ đa ngôn ngữ, bao gồm tiếng Việt, chạy được trên CPU |
| Cơ sở dữ liệu vector | FAISS (`faiss-cpu`) | Nhẹ, dễ cài đặt và phù hợp benchmark local |
| Môi trường chạy | Python 3.11 | Đồng nhất với cấu hình tooling và Docker |

Mô hình embedding được tải từ Hugging Face ở lần chạy đầu tiên và được
`sentence-transformers` lưu vào cache. Mô hình LLM được Ollama quản lý và
tải về riêng. Không commit model hoặc API credential vào repository.

## 2. Điều kiện cần trước khi cài đặt

- Git
- Python 3.11
- PowerShell trên Windows (các lệnh bên dưới dùng cú pháp PowerShell)
- Ollama nếu sử dụng LLM local mặc định; hoặc một endpoint
  OpenAI-compatible nếu sử dụng LLM qua API

Cài Ollama từ <https://ollama.com/download>. Sau khi cài đặt, kiểm tra và tải
mô hình:

```powershell
ollama --version
ollama pull qwen2.5:3b
```

Nếu Ollama chưa tự chạy dưới dạng background service, mở một terminal riêng:

```powershell
ollama serve
```

## 3. Cài đặt từ một bản clone mới

```powershell
git clone <repository-url>
Set-Location .\rag-security

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Copy-Item .env.example .env
```

Nếu PowerShell không cho phép kích hoạt virtual environment, có thể gọi trực
tiếp Python trong virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Không ghi API key thật vào `.env.example`, mã nguồn hoặc Git. File `.env` đã
được đưa vào `.gitignore`.

## 4. Kiểm tra kết nối cơ bản

Sau khi Ollama đang chạy và đã tải model `qwen2.5:3b`, thực hiện:

```powershell
python -m rag.smoke_test
```

Kết quả có dạng:

```text
LLM provider: ollama
LLM response: ...
Embedding model: intfloat/multilingual-e5-small
Embedding shape: (2, 384)
```

Lần tạo embedding đầu tiên có thể mất vài phút vì hệ thống cần tải và nạp
model. Nếu kiểm tra thất bại, chương trình sẽ báo lỗi ở endpoint LLM, cấu hình
đang chọn hoặc dependency embedding.

## 5. Sử dụng OpenAI hoặc vLLM

Mở file `.env` và thiết lập:

```dotenv
RAG_LLM_PROVIDER=openai_compatible
RAG_OPENAI_BASE_URL=https://api.openai.com/v1
RAG_OPENAI_API_KEY=thay-bang-api-key-cua-ban
RAG_OPENAI_LLM_MODEL=gpt-4o-mini
```

Với vLLM, sử dụng URL OpenAI-compatible và tên model mà vLLM đang phục vụ:

```dotenv
RAG_OPENAI_BASE_URL=http://localhost:8000/v1
RAG_OPENAI_API_KEY=local
RAG_OPENAI_LLM_MODEL=ten-model-dang-phuc-vu
```

Sau đó chạy lại:

```powershell
python -m rag.smoke_test
```

## 6. Cấu hình

Toàn bộ cấu hình được đọc từ biến môi trường. File mẫu đầy đủ nằm tại
[.env.example](./.env.example).

| Biến | Giá trị mặc định | Mô tả |
| --- | --- | --- |
| `RAG_LLM_PROVIDER` | `ollama` | `ollama` hoặc `openai_compatible` |
| `RAG_OLLAMA_BASE_URL` | `http://localhost:11434` | Địa chỉ Ollama server |
| `RAG_OLLAMA_LLM_MODEL` | `qwen2.5:3b` | Model chat trên Ollama |
| `RAG_OPENAI_BASE_URL` | `https://api.openai.com/v1` | Endpoint OpenAI-compatible |
| `RAG_OPENAI_API_KEY` | rỗng | Bắt buộc khi dùng chế độ API |
| `RAG_OPENAI_LLM_MODEL` | `gpt-4o-mini` | Model dùng qua API |
| `RAG_EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | Model embedding trên Hugging Face |
| `RAG_EMBEDDING_DEVICE` | `cpu` | Có thể chọn `cpu`, `cuda` hoặc Torch device khác |

## 7. Kiểm tra trong quá trình phát triển

```powershell
pre-commit install
pre-commit run --all-files
python -m pytest
```

`pytest` không phải là một file trong project. Đây là test runner tự động quét
thư mục `tests/` và chạy các hàm có tên bắt đầu bằng `test_`. Hiện tại có:

| File | Nội dung kiểm tra |
| --- | --- |
| `tests/test_config.py` | Kiểm tra provider và validation API key |
| `tests/test_clients.py` | Kiểm tra xử lý response của Ollama/OpenAI-compatible API |
| `tests/test_dataset.py` | Kiểm tra schema dữ liệu, split, canary và artifact attack sinh lại từ seed |

Các test này dùng mock nên không cần Ollama, không cần API key và không gọi
Internet. Có thể chạy riêng từng file:

```powershell
python -m pytest tests/test_config.py
python -m pytest tests/test_clients.py
```

Smoke test được tách riêng vì cần model service đang chạy và có thể phải tải
model weights ở lần đầu:

```powershell
python -m rag.smoke_test
```

### Có thể dùng Google Colab thay cho Ollama local không?

Có, nhưng Colab không thể được gọi bằng `localhost` từ máy Windows. Colab
chạy trên một máy ảo tạm thời ở xa, còn `localhost` trong file `.env` của
Windows trỏ về chính máy Windows.

Có hai cách sử dụng:

1. **Khuyến nghị cho đồ án:** chạy LLM trực tiếp trong notebook Colab bằng
   `transformers` hoặc vLLM, sau đó chạy phần benchmark/RAG cũng trong Colab.
   Cách này phù hợp khi cần GPU và không cần kết nối ngược về máy Windows.
2. **Chạy Ollama trong Colab:** cài Ollama trong runtime Colab, tải model và
   dùng một tunnel để tạo URL public tạm thời. Khi đó phải đặt
   `RAG_LLM_PROVIDER=ollama` và `RAG_OLLAMA_BASE_URL` thành URL tunnel, không
   được dùng `http://localhost:11434`.

Ví dụ, chạy Ollama trong Colab:

```python
!curl -fsSL https://ollama.com/install.sh | sh
!nohup ollama serve > /tmp/ollama.log 2>&1 &
!ollama pull qwen2.5:3b
```

Tuy nhiên, để máy Windows gọi được Ollama trong Colab cần thêm tunnel như
ngrok hoặc Cloudflare Tunnel. URL tunnel thường thay đổi mỗi lần runtime
Colab khởi động, runtime có thể bị ngắt và model phải tải lại. Vì vậy không
nên dùng đây làm môi trường benchmark ổn định cuối cùng.

Nếu chạy toàn bộ notebook trên Colab, có thể giữ cấu hình:

```dotenv
RAG_LLM_PROVIDER=ollama
RAG_OLLAMA_BASE_URL=http://localhost:11434
RAG_OLLAMA_LLM_MODEL=qwen2.5:3b
```

vì lúc này code và Ollama cùng chạy bên trong Colab. Nếu chạy code trên
Windows nhưng Ollama ở Colab, bắt buộc phải thay `localhost` bằng URL tunnel.

## 8. Cấu trúc thư mục

Threat model, schema dùng chung và hai case bàn giao cho các phần triển khai
nằm tại [docs/threat_model.md](./docs/threat_model.md). Đặc tả phương pháp cho
prototype Sprint 3 ở [docs/method_spec.md](./docs/method_spec.md); bộ dữ liệu
pilot và split ở [docs/dataset_datasheet.md](./docs/dataset_datasheet.md).

```text
attacks/     Payload tấn công và các mẫu benchmark
  cases/       Fixture SecurityCase (retrieval cố định) do A bàn giao
  dev/         Bộ attack dev sinh từ seed (cases.jsonl, summary.json)
data/raw/    Tài liệu nguồn lành tính và độc hại
data/corpus/ Corpus pilot: docs.jsonl + manifest.json (split, giấy phép)
data/qa/     Câu hỏi sạch có đáp án: dev.jsonl, test.jsonl
data/secrets/Secret tổng hợp, chỉ dùng để đánh giá rò rỉ dữ liệu
defenses/    Các cơ chế phát hiện và cô lập
eval/        Script và metric đánh giá
rag/         Cấu hình dùng chung, client provider và smoke test
schemas/     JSON Schema cho case, metadata, chunk và trace đánh giá
docs/        Ghi chú nghiên cứu và thiết kế
```

## 9. Chạy bằng Docker

Image chỉ kiểm tra môi trường Python. Model service được chạy bên ngoài
container, vì vậy cần dùng Ollama trên máy host hoặc cấu hình một endpoint
OpenAI-compatible:

```powershell
docker build -t rag-security .
docker run --rm rag-security
```

Để chạy smoke test trong container, trước hết phải có model service mà
container truy cập được. Với Ollama trên Docker Desktop, đặt
`RAG_OLLAMA_BASE_URL` thành địa chỉ có thể truy cập từ container, ví dụ
`http://host.docker.internal:11434`, rồi chạy:

```powershell
docker run --rm --env-file .env rag-security python -m rag.smoke_test
```

## 10. Bộ dữ liệu pilot Sprint 2

Bộ dữ liệu dùng cho pilot B0/B1 nằm trong repo và kiểm tra được offline, không
cần model hay API key:

| Thành phần | Tệp | Quy mô |
| --- | --- | --- |
| Corpus | [`data/corpus/docs.jsonl`](./data/corpus/docs.jsonl) + [`manifest.json`](./data/corpus/manifest.json) | 35 document (dev 27 / test 8) |
| QA sạch | [`data/qa/dev.jsonl`](./data/qa/dev.jsonl), [`data/qa/test.jsonl`](./data/qa/test.jsonl) | 25 câu (dev 17 / test 8) |
| Attack case dev | [`attacks/dev/cases.jsonl`](./attacks/dev/cases.jsonl) | 60 case, 5 nhóm × 12 |
| Canary tổng hợp | [`data/secrets/canaries.json`](./data/secrets/canaries.json) | 3 giá trị giả |

Hợp đồng dữ liệu ở [`schemas/rag_dataset.schema.json`](./schemas/rag_dataset.schema.json);
provenance, split, taxonomy và hạn chế ở
[`docs/dataset_datasheet.md`](./docs/dataset_datasheet.md).

Sinh lại attack case và kiểm tra nhãn:

```powershell
python attacks/generate_dev_cases.py            # ghi lại artifact từ seed
python attacks/generate_dev_cases.py --check    # artifact phải khớp seed
python attacks/validate_dataset.py              # schema + ngữ nghĩa + bảng kiểm kê
python -m pytest tests/test_dataset.py -q
```

`attacks/validate_dataset.py` trả mã 1 nếu corpus, QA hoặc attack case vi phạm
hợp đồng: split rò rỉ, canary ngoài document `secret`, payload chứa canary,
marker trùng với dữ liệu sạch, host document không thuộc split dev, hoặc nhóm
tấn công thiếu case/vị trí chèn.
