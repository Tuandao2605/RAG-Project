## Local development

Create a virtual environment, install the dependencies, and enable the
pre-commit hooks:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pre-commit install
```

Run the checks manually:

```powershell
pre-commit run --all-files
pytest
```

## Docker

The image expects a FastAPI application exposed as `app.main:app` by default.
Build and run it with:

```powershell
docker build -t rag-security .
docker run --rm -p 8000:8000 rag-security
```

For another import path, override `APP_MODULE` at build time:

```powershell
docker build --build-arg APP_MODULE=src.main:app -t rag-security .
```
