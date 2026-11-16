# RAG Security

Mã nguồn phục vụ đồ án nghiên cứu cơ chế phát hiện và phòng chống **prompt
injection gián tiếp** và **rò rỉ dữ liệu** trong các hệ thống
Retrieval-Augmented Generation (RAG).

## 1. Stack công nghệ được sử dụng

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
| `RAG_CHUNK_SIZE` | `800` | Kích thước chunk theo ký tự |
| `RAG_CHUNK_OVERLAP` | `100` | Số ký tự overlap giữa các chunk |
| `RAG_TOP_K` | `5` | Số context truy xuất mặc định |
| `RAG_PROMPT_TEMPLATE` | `grounded` | Template prompt yêu cầu trả lời có nguồn |
| `RAG_SEED` | `7` | Seed gửi cho provider nếu provider hỗ trợ |

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
| `tests/test_llm_client.py` | Kiểm tra xử lý response của Ollama/OpenAI-compatible API |
| `tests/test_dataset.py` | Kiểm tra schema dữ liệu, split, canary và artifact attack sinh lại từ seed |
| `tests/test_eval_runner.py` | Kiểm tra rule ASR, clean pair, invalid/service error, utility và latency |
| `tests/test_sandwich.py` | Kiểm tra B0/B1 prompt, 5 nhóm attack và hook CLI |
| `tests/test_ingest.py` | Kiểm tra đọc Markdown/JSONL và chia chunk |
| `tests/test_vector_index.py` | Kiểm tra FAISS, metadata, lưu/nạp, query và index rỗng |
| `tests/test_pipeline.py` | Kiểm tra pipeline B0, trace, lỗi và latency |
| `tests/test_prompting.py` | Kiểm tra prompt grounded và nguồn context |

Các unit test dùng mock nên không cần Ollama, không cần API key và không gọi
Internet. Có thể chạy riêng từng nhóm:

```powershell
python -m pytest tests/test_config.py
python -m pytest tests/test_llm_client.py
python -m pytest tests/test_ingest.py
python -m pytest tests/test_vector_index.py
python -m pytest tests/test_pipeline.py tests/test_prompting.py
python -m pytest tests/test_dataset.py
python -m pytest tests/test_eval_runner.py
python -m pytest tests/test_sandwich.py
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
rag-security/
├── attacks/
│   ├── cases/           Fixture SecurityCase cho benchmark
│   ├── dev/             Attack cases sinh từ seed
│   └── generate_dev_cases.py
├── data/
│   ├── raw/             Tài liệu Markdown/JSONL đầu vào
│   ├── corpus/          Corpus pilot và manifest
│   ├── qa/              Câu hỏi sạch có đáp án
│   └── secrets/         Canary tổng hợp dùng đánh giá rò rỉ
├── defenses/
│   └── sandwich.py      Prompt hook B0/B1
├── eval/                Script và metric đánh giá
├── schemas/             JSON Schema cho dataset và trace
├── rag/
│   ├── __init__.py
│   ├── llm_client.py    Client Ollama/OpenAI-compatible
│   ├── embedding.py     Tạo embedding passage và query
│   ├── config.py        Đọc cấu hình từ biến môi trường
│   ├── ingest.py        Đọc tài liệu và chia chunk
│   ├── vector_index.py  FAISS, metadata và truy xuất top-k
│   ├── defenses.py      Hook defense dùng chung cho B0/B1
│   ├── prompting.py     Prompt grounded có nguồn
│   ├── pipeline.py      Pipeline retrieval-defense-LLM và trace
│   ├── cli.py           Lệnh build-index, query và answer
│   └── smoke_test.py    Kiểm tra kết nối LLM/embedding thật
├── tests/
│   ├── test_config.py   Test validation cấu hình
│   ├── test_llm_client.py
│   ├── test_dataset.py  Test schema và artifact dataset
│   ├── test_eval_runner.py
│   ├── test_sandwich.py
│   ├── test_ingest.py   Test đọc tài liệu và chunk
│   ├── test_vector_index.py
│   ├── test_prompting.py Test prompt grounded
│   └── test_pipeline.py Test B0, trace và lỗi
├── docs/
│   ├── README.md        Hướng dẫn Docker bổ sung
│   ├── threat_model.md  Threat model
│   ├── method_spec.md   Đặc tả phương pháp
│   ├── dataset_datasheet.md
│   └── sandwich_prompting.md
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

Thư mục kết quả index được tạo khi sử dụng:

```text
data/raw/              Tài liệu Markdown/JSONL đầu vào
artifacts/demo-index/  index.faiss và metadata.json sau khi build
```

`tests/` nên được giữ trong cấu trúc dự án và không đưa vào `data/raw/`.
Các file trong `tests/` là mã kiểm thử tự động, còn `data/raw/` chỉ chứa tài
liệu được ingest. Các thư mục `attacks/`, `defenses/`, `eval/`, `schemas/` và
dữ liệu pilot là thành phần benchmark của đồ án.

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

## 11. Chấm trace và tổng hợp pilot

Runner ticket 2.6 chấm JSONL trace theo schema chung, tính ASR theo
[`docs/method_spec.md`](./docs/method_spec.md), task success, security asserts,
utility QA và latency. Cách tạo artifact và phân loại `invalid` / `service_error`
nằm trong [`docs/evaluation_runner.md`](./docs/evaluation_runner.md).

Lệnh này chỉ chạy sau khi đã có trace JSONL ở `artifacts/runs.jsonl` và,
nếu dùng latency, sidecar ở `artifacts/latencies.jsonl`:

```powershell
python -m eval.runner `
  --cases attacks/cases `
  --runs artifacts/runs.jsonl `
  --qa data/qa/dev.jsonl `
  --latencies artifacts/latencies.jsonl `
  --output artifacts/evaluation.json
```

## 12. Ingest tài liệu và truy xuất FAISS

Pipeline RAG hiện có hỗ trợ:

```text
Markdown/JSONL -> chuẩn hóa -> chia chunk -> passage embedding -> FAISS
```

Mỗi chunk được lưu metadata gồm `chunk_id`, `doc_id` và `text`. Khi truy vấn,
hệ thống dùng tiền tố `query:` cho câu hỏi, sau đó trả về top-k kết quả cùng
`chunk_id`, `doc_id`, `score` và nội dung chunk.

### Chuẩn bị dữ liệu

Tạo thư mục dữ liệu, ví dụ:

```text
data/raw/
├── security_policy.md
└── policies.jsonl
```

Markdown dùng toàn bộ nội dung file. JSONL dùng một object mỗi dòng, bắt buộc
có `text` (hoặc `content`) và có thể có `doc_id`:

```json
{"doc_id":"policy-001","text":"Mật khẩu phải có ít nhất 12 ký tự."}
```

Nếu Markdown không có `doc_id`, tên file được dùng làm `doc_id`.

### Build index

Kích hoạt virtual environment rồi chạy:

```powershell
Set-Location C:\Users\tuduy\Documents\DATN\rag-security
.\.venv\Scripts\Activate.ps1

python -m rag.cli build-index `
  --input data\raw `
  --output artifacts\demo-index `
  --chunk-size 800 `
  --overlap 100
```

Lệnh này tạo index demo cho các câu hỏi trong `data\raw`.

Kết quả tạo:

```text
artifacts/demo-index/index.faiss
artifacts/demo-index/metadata.json
```

Lần chạy đầu có thể tải model embedding `intfloat/multilingual-e5-small` từ
Hugging Face. Nếu gặp lỗi thiếu package, cài dependency bằng:

```powershell
python -m pip install -r requirements.txt
```

Tham số `--overlap` giúp giữ lại một phần ngữ cảnh giữa hai chunk. Khi thư
mục đầu vào rỗng, index vẫn được lưu hợp lệ và truy vấn sẽ trả về `[]`.

Để chạy benchmark với các case trong `attacks\cases`, tạo index riêng từ
corpus benchmark:

```powershell
python -m rag.cli build-index `
  --input data\corpus\docs.jsonl `
  --output artifacts\index `
  --chunk-size 800 `
  --overlap 100
```

Không dùng `artifacts\demo-index` cho các SecurityCase hoàn trả hoặc rò rỉ,
vì hai index chứa các document và `doc_id` khác nhau.

### Query top-k

```powershell
python -m rag.cli query `
  --index artifacts\demo-index `
  --query "Chính sách mật khẩu là gì?" `
  --top-k 3
```

Ví dụ kết quả:

```json
[
  {
    "chunk_id": "policy-001:0000",
    "doc_id": "policy-001",
    "text": "Mật khẩu phải có ít nhất 12 ký tự.",
    "score": 0.8731
  }
]
```

### Sinh câu trả lời với B0 hoặc B1

Lệnh `answer` truy xuất top-k một lần rồi gửi cùng chunk/context đến cùng LLM.
Chỉ prompt thay đổi giữa B0 và B1. B1 Sandwich Prompting đặt chỉ dẫn về cách
dùng context trước và sau phần tài liệu truy xuất. Thiết lập mặc định là
temperature `0` và seed `7`; hãy giữ nguyên các tham số khi so sánh hai defense.

```powershell
python -m rag.cli answer `
  --index artifacts\demo-index `
  --question "Chính sách mật khẩu là gì?" `
  --top-k 3 `
  --defense b1 `
  --temperature 0 `
  --seed 7
```

Dùng `--defense b0` để chạy baseline. Cả hai chế độ trả về câu trả lời cùng
danh sách chunk nguồn đã truy xuất. Chi tiết prompt và protocol ở
[`docs/sandwich_prompting.md`](./docs/sandwich_prompting.md).

Để tạo artifact cho evaluator, truyền đồng thời `--case`, `--variant` và
`--artifact`; có thể thêm `--latencies` để ghi sidecar latency. `clean` và
`attack` là nhãn của lần chạy trong artifact; lệnh `answer` không tự chèn
payload vào corpus.

Khi dùng `--case`, nếu không truyền `--top-k`, CLI tự dùng
`retrieval.top_k` trong SecurityCase. Có thể truyền `--top-k` thủ công để
ghi đè giá trị đó.

### B0/B1: chạy từ câu hỏi tới câu trả lời có nguồn

Lệnh `answer` dùng cùng pipeline cho B0 và các phiên bản defense sau này:

```text
query -> retrieval -> context_before_defense -> defense hook
      -> context_after_defense -> grounded prompt -> LLM -> answer + citations
```

Chạy B0 với hook baseline:

```powershell
python -m rag.cli answer `
  --index artifacts\demo-index `
  --query "Chính sách mật khẩu là gì?" `
  --top-k 3 `
  --defense b0 `
  --seed 7 `
  --log artifacts/b0-runs.jsonl
```

Kết quả JSON gồm `answer`, `citations`, context trước/sau defense, cấu hình,
latency retrieval/defense/LLM/tổng và lỗi nếu có. Mỗi lần chạy được ghi thêm
một dòng JSONL vào file `--log`. B0 và B1 dùng chung pipeline; B1 chỉ thay
prompt hook. Dùng `--defense b0` cho baseline và `--defense b1` cho Sandwich
Prompting.

### Chạy benchmark clean/attack cho B0 và B1

Benchmark dùng query hoàn trả và index `artifacts\index` được tạo từ
`data\corpus\docs.jsonl`. Cần bật Ollama trước khi chạy:

```powershell
ollama serve
```

Trong terminal khác, chạy bốn lần để tạo cùng một file artifact:

```powershell
python -m rag.cli answer `
  --index artifacts\index `
  --query "Khách hàng của Sao Mai được yêu cầu hoàn trả trong bao nhiêu ngày?" `
  --defense b0 `
  --case attacks\cases\indirect_answer_override.json `
  --variant clean `
  --artifact artifacts\runs.jsonl `
  --latencies artifacts\latencies.jsonl `
  --log artifacts\b0-clean.trace.jsonl

python -m rag.cli answer `
  --index artifacts\index `
  --query "Khách hàng của Sao Mai được yêu cầu hoàn trả trong bao nhiêu ngày?" `
  --defense b1 `
  --case attacks\cases\indirect_answer_override.json `
  --variant clean `
  --artifact artifacts\runs.jsonl `
  --latencies artifacts\latencies.jsonl `
  --log artifacts\b1-clean.trace.jsonl
```

Chạy `--variant attack` tương tự cho B0 và B1. Khi có `--case`, CLI tự dùng
`retrieval.top_k` của case nếu không truyền `--top-k`. `clean` và `attack`
hiện là nhãn của artifact; pipeline chưa tự chèn payload attack vào corpus.

Nếu `answer` trả về `ProviderError`, kiểm tra riêng Ollama trước:

```powershell
ollama list
ollama run qwen2.5:3b "Trả lời ngắn: 1+1 bằng mấy?"
```

Chỉ chạy RAG sau khi `ollama run` trả về câu trả lời. Lỗi
`CUDA error: device kernel image is invalid` là lỗi môi trường GPU/Ollama,
không phải lỗi retrieval hoặc prompt của B0/B1.

### Kiểm thử pipeline

Các test ingest và FAISS dùng embedding mock nên không cần tải model
Hugging Face:

```powershell
python -m pytest tests/test_ingest.py tests/test_vector_index.py -v
python -m pytest -v
```

Các test bao gồm đọc Markdown/JSONL, tạo chunk, lưu/nạp index, truy xuất câu
hỏi sạch và truy vấn index rỗng. Test pipeline mock retrieval/LLM nên không
cần chạy Ollama hoặc tải model.
