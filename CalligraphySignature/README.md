# FastAPI Hello Project

A simple FastAPI project with a hello endpoint.

## Setup

1. Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies into the venv:
```bash
./venv/bin/pip install -r requirements.txt
```
(Or after `source venv/bin/activate`: `pip install -r requirements.txt`.)

3. Run the server (use the venv so FastAPI loads):

   **Option A – script (recommended):**
   ```bash
   ./run.sh
   ```

   **Option B – venv’s uvicorn directly:**
   ```bash
   source venv/bin/activate
   uvicorn main:app --reload
   ```
   or without activating:
   ```bash
   venv/bin/uvicorn main:app --reload
   ```

   **Important:** Use `venv/bin/uvicorn` or `./run.sh` (or activate the venv first). Running `uvicorn` or `python main.py` with the system Python will fail because FastAPI is only installed in `venv`.

4. Access the API:
- API endpoint: http://localhost:8000/hello?name=YourName
- API documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Usage

The `/hello` endpoint accepts a query parameter `name` and returns a greeting:

```
GET /hello?name=Alice
Response: "hello, Alice"
```

## IDE: “Import fastapi could not be resolved”

The app runs correctly with `./run.sh` or `venv/bin/uvicorn`. If the editor still shows that warning:

1. **Choose the venv interpreter:** `Cmd+Shift+P` → **Python: Select Interpreter** → pick `./venv/bin/python` or `/Users/xiaodan/Projects/FirstFastApi/venv/bin/python`.
2. **Reload the window:** `Cmd+Shift+P` → **Developer: Reload Window**.
