# Search Feature Improvements (May 30, 2026)

## Problem Overview
During testing of the search capabilities with local LLMs (Ollama `qwen3:14b`), several issues were identified that degraded the quality of the research output and caused system failures:
1. **API Fragility**: The `AcademicSearchTool` crashed entirely (`400 Bad Request`) when attempting to filter papers by year because the OpenAlex API syntax was malformed. Furthermore, strict rate limiting from Semantic Scholar (`429 Too Many Requests`) would cause the entire tool call to fail, even if other providers succeeded.
2. **Poor Web Snippets**: The `WebSearchTool` (using DuckDuckGo) returned brief, 15-word snippets. The LLM would often hallucinate details or misunderstand the context (e.g., misinterpreting a Chinese business platform for a sign language paper) because it couldn't read the actual article.
3. **Lack of Iteration**: The LLM treated search as a one-and-done operation, frequently giving up if the first query returned no results instead of trying different keywords.
4. **Local Model Timeouts**: The local Ollama server timed out reading requests (`Read timed out. (read timeout=120)`) because generating responses based on heavy context windows takes longer than the default 2-minute limit.

## Implemented Solutions

### 1. Robust Academic API Integration
- **Fixed OpenAlex Year Filter**: Refactored the `min_year` and `max_year` logic in `citation_lookup.py` to use the correct OpenAlex range syntax (e.g., `publication_year:2025-2026`). 
- **Graceful Provider Fallbacks**: Updated the `search_papers` method to catch individual `requests.RequestException` errors. If Semantic Scholar rate-limits the application, it no longer crashes the tool; instead, it gracefully returns whatever successful results were pulled from OpenAlex.

### 2. ReadUrlTool (Web Scraping)
- **Dependency Added**: Added `beautifulsoup4` to `requirements.txt`.
- **New Tool**: Created `app/tools/web_fetch.py` containing the `ReadUrlTool`.
- **Functionality**: The tool downloads the HTML of a provided URL, strips out boilerplate (scripts, styles, navbars, footers), and condenses the text into a clean string (capped at 5,000 characters). This allows the agent to actually "click" on links and read the full page context to verify facts instead of relying on tiny DuckDuckGo snippets.
- **Integration**: Attached the `ReadUrlTool` to the `ChatAgent`.

### 3. Iterative Research Prompting
- **Behavioral Shift**: Updated the `CHAT_SYSTEM_PROMPT` in `app/ui/streamlit_app.py`.
- **New Instructions**: The agent is now explicitly instructed to act as a proactive, iterative researcher. If search results are ambiguous or irrelevant, it must NOT give up. It is instructed to loop, try different keywords, and use `ReadUrlTool` to verify sources until satisfactory information is found.

### 4. Environment Configuration
- **Timeout Increased**: Increased the `OLLAMA_TIMEOUT_SECONDS` variable in the `.env` file from `120` to `600` (10 minutes). This gives the heavy `qwen3:14b` model sufficient time to process massive context windows (containing multiple paper abstracts and full webpage text) without dropping the connection.
