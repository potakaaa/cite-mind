# Cite Mind

Cite Mind is a lightweight multi-agent research assistant for reading papers and turning them into structured research outputs. The current MVP runs as a Streamlit app, accepts a PDF or pasted paper text, routes the work through specialized agents, and exports the final result as Markdown, DOCX, and PDF.

## MVP Features

- Upload a PDF or paste raw paper text.
- Run one of four supported workflows:
  - `study_table`
  - `study_table_with_gaps`
  - `paper_summary`
  - `full_report`
- Use a multi-agent pipeline with a research reader, optional critic, and writer.
- Select an LLM provider from configured providers: Ollama, Gemini, or OpenRouter.
- Chat with an assistant, optionally grounded in uploaded or pasted document context.
- Optionally index multiple papers for cross-paper RAG question answering.
- Save generated outputs under `data/outputs/`.
- Save extracted PDF text under `data/extracted_text/`.
- Save optional RAG vector data under `data/vector_db/`.

## Requirements

- Python 3.11 or newer is recommended.
- One LLM provider:
  - Ollama running locally, or
  - a Gemini API key, or
  - an OpenRouter API key.

## Installation

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Environment Setup

Edit `.env` after copying `.env.example`.

### Ollama

Ollama is the default local provider.

```env
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_RETRIES=0
```

Install and start Ollama, then pull the configured model:

```bash
ollama pull llama3.1:8b
ollama serve
```

If Ollama is already running as a service, you only need the `ollama pull` command.

### Gemini

```env
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

### OpenRouter

```env
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
```

You can configure more than one provider. The Streamlit app shows the providers that pass local configuration validation.

## Run The App

Start the Streamlit UI:

```bash
streamlit run app/ui/streamlit_app.py
```

You can also launch it through the project entry point:

```bash
python main.py --ui
```

To print a quick environment summary:

```bash
python main.py
```

To run an optional LLM smoke test, set `LLM_SMOKE_TEST_PROMPT` in `.env` and run:

```bash
python main.py
```

## Basic Usage

1. Open the Streamlit app.
2. Choose an available LLM provider.
3. In the `Pipeline` tab, upload a PDF or paste paper text.
4. Select a task type.
5. Click `Run workflow`.
6. Review the final output and download Markdown, DOCX, or PDF exports.

The `Chat` tab supports general research planning questions. You can optionally upload a PDF or paste text first so the chat response uses document context.

The `Cross-paper RAG` tab is disabled by default for the MVP path. To use it, either enable the in-app checkbox or set `RAG_ENABLED=true` in `.env`, then index multiple PDFs or pasted papers before asking a question. Retrieved source chunk metadata is shown with each answer.

## Project Structure

```text
cite-mind/
├── main.py
├── config.py
├── app/
│   ├── agents/
│   ├── llm/
│   ├── orchestrator/
│   ├── prompts/
│   ├── rag/
│   ├── schemas/
│   ├── services/
│   ├── tools/
│   └── ui/
├── data/
│   ├── extracted_text/
│   ├── outputs/
│   ├── uploads/
│   └── vector_db/
├── docs/
└── tests/
```

## Documentation

- [Setup](docs/setup.md)
- [Architecture](docs/architecture.md)
- [Usage](docs/usage.md)

## Troubleshooting

### Missing API Key

If Gemini or OpenRouter fails with a missing key error, set the matching variable in `.env`:

```env
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
```

Then restart Streamlit so `config.py` reloads the environment.

### Ollama Not Running

If Ollama requests fail with a connection error, make sure the server is running and the model exists:

```bash
ollama serve
ollama pull llama3.1:8b
```

Also confirm `OLLAMA_BASE_URL` matches the local Ollama server URL.

### PDF Extraction Errors

Cite Mind uses PyMuPDF first and pdfplumber as a fallback. Extraction can fail when a PDF is scanned/image-only, corrupted, encrypted, or not actually a PDF. Try a text-based PDF, paste the paper text directly, or run OCR outside Cite Mind before uploading.

## Tests

Run the test suite with:

```bash
pytest
```
