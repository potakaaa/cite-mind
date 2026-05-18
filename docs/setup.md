# Setup

This guide covers local installation, `.env` configuration, and run commands for Cite Mind.

## 1. Create A Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

The main runtime dependencies include Streamlit, Pydantic, Requests, PyMuPDF, pdfplumber, python-docx, and ReportLab.

## 3. Create `.env`

```bash
cp .env.example .env
```

Important settings:

```env
APP_NAME=Cite Mind
APP_ENV=development
LOG_LEVEL=INFO
MAX_AGENTS=3

DEFAULT_LLM_PROVIDER=ollama

UPLOAD_DIR=./data/uploads
OUTPUT_DIR=./data/outputs
```

`MAX_AGENTS` is validated between 1 and 3. The current MVP defines three agent roles: research reader, critic, and writer.

## 4. Configure An LLM Provider

### Ollama

Ollama is the default provider in `.env.example`.

```env
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_RETRIES=0
```

Prepare the model:

```bash
ollama pull llama3.1:8b
```

Start the server if it is not already running:

```bash
ollama serve
```

### Gemini

```env
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

The Gemini provider calls the Google Generative Language `generateContent` endpoint.

### OpenRouter

```env
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
```

The OpenRouter provider calls the OpenRouter chat completions endpoint.

## 5. Run Cite Mind

Recommended Streamlit command:

```bash
streamlit run app/ui/streamlit_app.py
```

Alternative entry point:

```bash
python main.py --ui
```

Environment summary:

```bash
python main.py
```

Optional provider smoke test:

```env
LLM_SMOKE_TEST_PROMPT=Say hello from Cite Mind.
```

Then run:

```bash
python main.py
```

## 6. Output Locations

- Uploaded PDFs: `data/uploads/`
- Extracted PDF text: `data/extracted_text/`
- Generated Markdown, DOCX, and PDF exports: `data/outputs/`

## Troubleshooting

### Missing API Keys

`GEMINI_API_KEY` is required when `DEFAULT_LLM_PROVIDER=gemini` or when Gemini is selected in the UI.

`OPENROUTER_API_KEY` is required when `DEFAULT_LLM_PROVIDER=openrouter` or when OpenRouter is selected in the UI.

After changing `.env`, restart Streamlit.

### Ollama Connection Errors

Check that Ollama is reachable:

```bash
curl http://localhost:11434/api/tags
```

If the command fails, start Ollama:

```bash
ollama serve
```

If the server is running but generation fails, pull the configured model:

```bash
ollama pull llama3.1:8b
```

### PDF Extraction Errors

The PDF reader validates the file extension and MIME type, then extracts text with PyMuPDF. If no meaningful text is found, it tries pdfplumber. Common failure cases are scanned PDFs, encrypted files, corrupted files, and PDFs without embedded text.

Use one of these workarounds:

- Paste the paper text directly in the UI.
- Run OCR outside Cite Mind and paste the OCR text.
- Try a text-based version of the paper.
