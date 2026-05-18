# Usage

Cite Mind supports two user-facing workflows in Streamlit: the structured pipeline and chat.

Start the app:

```bash
streamlit run app/ui/streamlit_app.py
```

## Pipeline Workflow

Use the `Pipeline` tab when you want a structured output from a paper.

1. Select an LLM provider.
2. Choose `Upload PDF` or `Paste text`.
3. Provide the paper content.
4. Select a task type.
5. Click `Run workflow`.
6. Review the final Markdown output.
7. Download Markdown, DOCX, or PDF exports.

Exports are saved under `data/outputs/`.

## Supported Task Types

### Study Table

Task type: `study_table`

Agent sequence:

```text
research reader -> writer
```

Use this when you want a compact table of study metadata, methods, findings, and evidence extracted from a paper.

Example input:

```text
Paste the full text of a research paper and select Study table.
```

Expected output:

```text
A Markdown table summarizing the study fields that the reader agent extracted.
```

### Study Table With Gaps

Task type: `study_table_with_gaps`

Agent sequence:

```text
research reader -> critic -> writer
```

Use this when you want extracted study information plus limitations, gaps, and future work opportunities.

Example input:

```text
Upload a PDF of an empirical paper and select Study table with gaps.
```

Expected output:

```text
A study table plus critique-oriented notes grounded in the extracted study data.
```

### Paper Summary

Task type: `paper_summary`

Agent sequence:

```text
research reader -> writer
```

Use this when you want a narrative summary of one paper.

Example input:

```text
Paste an abstract, methods section, and results section, then select Paper summary.
```

Expected output:

```text
A Markdown summary covering the paper's purpose, method, findings, and unavailable fields.
```

### Full Report

Task type: `full_report`

Agent sequence:

```text
research reader -> critic -> writer
```

Use this when you want the most complete MVP output, including extracted study details and critique.

Example input:

```text
Upload a complete text-based PDF and select Full report.
```

Expected output:

```text
A longer Markdown report based on the extracted study data and critic output.
```

## Chat Workflow

Use the `Chat` tab for conversational research planning.

Optional context sources:

- Upload PDF
- Paste text
- No context

Example questions:

```text
What search terms should I use for a literature review on AI-assisted citation screening?
```

```text
Based on the loaded paper, what are the main methodological limitations?
```

```text
What related evaluation metrics should I consider for this study design?
```

The chat prompt includes recent conversation history and up to 12,000 characters of active document context.

## Programmatic Usage

You can call the research service directly from Python:

```python
from app.orchestrator.task_schema import TaskType
from app.services.research_service import ResearchService

service = ResearchService()
result = service.run(
    task_type=TaskType.PAPER_SUMMARY,
    raw_text="Paste paper text here...",
    provider="ollama",
    include_metadata=True,
)

print(result["final_output"])
```

You can also call the orchestrator directly when you already have paper text:

```python
from app.orchestrator.orchestrator import run_task

result = run_task(
    task_type="study_table",
    paper_text="Paste paper text here...",
    provider="ollama",
)

print(result.final_output)
```

## Input Notes

- PDF input must be a `.pdf` file.
- Text-based PDFs work best.
- Scanned PDFs need OCR before Cite Mind can process them reliably.
- Pasted text must not be empty.
- Large documents are chunked before extraction.

## Troubleshooting

### No Providers Appear In The UI

The app lists providers that pass configuration validation. Ollama needs `OLLAMA_BASE_URL`; Gemini needs `GEMINI_API_KEY`; OpenRouter needs `OPENROUTER_API_KEY`.

### Workflow Fails With Missing API Key

Set the required key in `.env` and restart the Streamlit process.

### Workflow Fails With Ollama Connection Error

Start Ollama and confirm the configured model exists:

```bash
ollama serve
ollama pull llama3.1:8b
```

### PDF Has No Readable Text

The PDF may be scanned, image-only, encrypted, or corrupted. Paste text directly or run OCR outside Cite Mind.

### Export Fails

Make sure `python-docx` and `reportlab` installed successfully:

```bash
pip install -r requirements.txt
```
