# Simtopia

A simple space trade prototype with a FastAPI backend, SQLite database, and a browser UI.

## Run the backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

If you are using a free-threaded Python build and hit `orjson` install errors, create the venv with a standard CPython build, for example:

```bash
make venv PYTHON=python3.12
make install
```

You can also run everything in one shot with a specific interpreter:

```bash
make run PYTHON=python3.12
```

Open http://127.0.0.1:8000 in a browser.
