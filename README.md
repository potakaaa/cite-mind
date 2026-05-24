# Cite Mind

Cite Mind is a chat-first, multi-agent assistant. The intended experience is a normal chatbot: open the app, choose a model provider if needed, type a message, and keep the conversation going. Attachments are optional context, not the center of the product.

The app can still use multiple specialized agents behind the scenes, but the user experience should stay simple. Users should not have to understand pipelines, task types, exports, or retrieval settings before they can ask a question.

## Product Direction

- A single primary chat interface.
- Optional file attachments for extra context.
- Multi-agent reasoning handled in the background.
- Simple provider configuration for Ollama, Gemini, or OpenRouter.
- Conversation history that keeps recent context available.
- Research help when documents are attached, without forcing a separate workflow.
- Minimal controls in the main UI.

## Current Status

The codebase currently contains an earlier research-workflow MVP. Some modules still support structured paper workflows, exports, and optional cross-paper retrieval. Those pieces are implementation details for now and should be folded into the simpler chat experience over time.

The README describes the desired app context going forward:

```text
user message + optional attachments
        |
chat UI
        |
multi-agent coordinator
        |
specialized agents as needed
        |
assistant response
```

## Expected Chat Experience

Users should be able to:

1. Open the app.
2. Type a message.
3. Optionally attach PDFs or text files.
4. Ask follow-up questions naturally.
5. Receive one clear assistant response.

Example prompts:

```text
Help me understand this paper.
```

```text
Summarize the attached document and tell me what questions I should ask next.
```

```text
Compare the methods used in these files.
```

```text
Draft a literature review outline from this conversation.
```

## Multi-Agent Behavior

The app may route work through agents such as:

- A coordinator that decides what needs to happen.
- A reader that extracts useful details from attached documents.
- A critic that checks limitations, gaps, and weak reasoning.
- A writer that turns the result into a clear response.
- A citation or search helper when paper lookup is needed.

This should feel like one assistant to the user. Agent names, intermediate steps, and workflow controls should only appear when they are useful for transparency or debugging.

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

You can configure more than one provider. The app should show only providers that pass local configuration validation.

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

## Usage

The target usage is:

1. Open the Streamlit app.
2. Select an available LLM provider only if needed.
3. Type a message in the chat input.
4. Optionally attach files for context.
5. Continue asking follow-up questions.

Attachments should support research-style questions, summaries, comparisons, critique, and drafting. The assistant should decide whether to call document-reading, critique, writing, retrieval, or citation helpers.

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

Some docs still describe the older workflow-oriented MVP and should be updated after the chat-first UI is implemented.

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

### Attachment Text Cannot Be Read

PDF extraction can fail when a PDF is scanned, image-only, corrupted, encrypted, or not actually a PDF. Try a text-based PDF, paste the document text directly, or run OCR before uploading.

## Tests

Run the test suite with:

```bash
pytest
```
