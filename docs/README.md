## Phát triển local

Tạo virtual environment, cài dependency và kích hoạt hook pre-commit:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pre-commit install
```

Chạy các bước kiểm tra thủ công:

```powershell
pre-commit run --all-files
pytest
```

## Chạy bằng Docker

Image Docker hiện dùng để kiểm tra môi trường Python. Build và chạy image bằng:

```powershell
docker build -t rag-security .
docker run --rm -p 8000:8000 rag-security
```

Nếu ứng dụng sử dụng import path khác, có thể truyền `APP_MODULE` khi build:

```powershell
docker build --build-arg APP_MODULE=src.main:app -t rag-security .
```
