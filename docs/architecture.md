# Architecture

Cite Mind is organized as a small layered Python application:

```text
Streamlit UI / main.py
        |
    services
        |
  orchestrator
        |
     agents
        |
   LLM router
        |
 LLM providers
```

Supporting tools handle PDF extraction, text chunking, file paths, citation lookup, and exports.

## Entry Points

- `main.py` prints environment information, optionally runs an LLM smoke test, or launches Streamlit with `python main.py --ui`.
- `app/ui/streamlit_app.py` renders the Streamlit app.

The Streamlit app has two tabs:

- `Pipeline`: upload a PDF or paste text, choose a task type, run the multi-agent workflow, and download exports.
- `Chat`: ask research questions with optional document context.

## Configuration

`config.py` loads `.env` with `python-dotenv` and exposes a Pydantic `Settings` object.

Core settings include:

- app metadata: `APP_NAME`, `APP_ENV`, `LOG_LEVEL`, `MAX_AGENTS`
- provider routing: `DEFAULT_LLM_PROVIDER`
- provider config: Gemini, Ollama, OpenRouter keys, URLs, models, and timeouts
- storage paths: `UPLOAD_DIR`, `OUTPUT_DIR`

`settings.validate_provider_config()` validates only the selected provider. Gemini and OpenRouter require API keys. Ollama requires a base URL.

## Orchestrator

The orchestrator lives in `app/orchestrator/`.

- `TaskType` defines supported workflows, including `chat` for prompt-driven routing.
- `TaskRouter` maps explicit task types to pipeline names, or infers a chat route from the user's prompt and attachment metadata.
- `pipeline.py` defines reusable pipeline steps and can build dynamic chat pipelines.
- `Orchestrator` executes each step, stores intermediate outputs in context, and returns a `TaskResult`.

Supported task routes:

| Task type | Pipeline | Agent sequence | Writer mode |
| --- | --- | --- | --- |
| `study_table` | `study_table` | research reader -> writer | `study_table` |
| `study_table_with_gaps` | `study_table_with_gaps` | research reader -> critic -> writer | `gaps` |
| `paper_summary` | `paper_summary` | research reader -> writer | `summary` |
| `full_report` | `full_report` | research reader -> critic -> writer | `full_report` |
| `chat` | inferred, for example `chat_summary` or `chat_gaps_with_critic` | inferred from prompt/attachments | inferred |

Each pipeline step records metadata: step name, agent name, status, duration, output keys, and error details when execution fails.

## Agents

Agents live in `app/agents/` and inherit from `BaseAgent`.

`BaseAgent` handles the shared flow:

1. Build a prompt.
2. Call `LLMRouter.generate()`.
3. Parse or normalize the response.
4. Raise `AgentExecutionError` on provider, validation, or parsing failures.

### Research Reader Agent

`ResearchReaderAgent` extracts structured study data from paper text. It chunks long text, runs extraction over each chunk, and merges multiple partial JSON outputs when needed.

The response is validated as `StudySchema`.

### Critic Agent

`CriticAgent` reviews the structured study data for limitations, methodological weaknesses, gaps, and confidence notes.

The response is validated as `CritiqueSchema`.

### Writer Agent

`WriterAgent` turns structured study data and optional critique data into user-facing Markdown.

Supported writer modes are:

- `study_table`
- `summary`
- `gaps`
- `rrl`
- `full_report`

The orchestrator currently uses all except `rrl`.

## Services

Services live in `app/services/` and provide application-level workflows.

### Document Service

`DocumentService` accepts either raw text or PDF input.

For raw text, it validates non-empty content and chunks it.

For PDFs, it saves uploaded bytes when needed, validates the PDF, extracts text, chunks the extracted text, and returns document metadata.

### Research Service

`ResearchService` coordinates document preparation and orchestrator execution. It is the main service used by the Streamlit pipeline tab.

When `include_metadata=True`, it returns:

- final output
- task type
- step metadata
- intermediate study and critique data
- document metadata

### Export Service

`ExportService` writes final research output to:

- Markdown
- DOCX
- PDF

Exports are saved under `data/outputs/`.

## Tools

Tools live in `app/tools/`.

- `PDFReader`: extracts text with PyMuPDF, falls back to pdfplumber when needed, cleans text, and chunks pages.
- `TextChunker`: chunks long text with overlap metadata.
- `FileManager`: validates PDF files, manages upload and extracted text directories.
- `CitationLookup`: provides Crossref DOI lookup, title lookup through Crossref/OpenAlex/Semantic Scholar, and paper search through OpenAlex/Semantic Scholar.

Citation lookup is available as a tool module but is not currently wired into the Streamlit pipeline.

## LLM Router And Providers

LLM code lives in `app/llm/`.

`LLMRouter` is the single agent-facing generation interface. It constructs provider instances for:

- `GeminiProvider`
- `OllamaProvider`
- `OpenRouterProvider`

Provider selection works like this:

1. If a provider is passed explicitly, use it.
2. If `task_type == "long_document_reasoning"`, use Gemini.
3. Otherwise use `DEFAULT_LLM_PROVIDER`.

The current orchestrator passes the selected Streamlit provider through each agent call.

Each provider implements `generate(prompt, **kwargs)` and normalizes text output. Shared HTTP retry and timeout behavior lives in `BaseLLMProvider`.

## Data Flow

```text
PDF upload or pasted text
        |
DocumentService
        |
paper_text + metadata
        |
ResearchService
        |
TaskInput
        |
Orchestrator
        |
ResearchReaderAgent
        |
CriticAgent, for gap/report workflows
        |
WriterAgent
        |
TaskResult
        |
Streamlit output + ExportService downloads
```

## Error Handling

- Provider setup errors surface as `LLMProviderError` or wrapped `AgentExecutionError`.
- Invalid agent responses fail schema parsing and stop the pipeline.
- Document ingestion errors are wrapped as `DocumentServiceError`.
- Pipeline failures are wrapped as `PipelineValidationError`, then surfaced by `ResearchServiceError` in the UI.
