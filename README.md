# Cite Mind

Cite Mind is a lightweight, modular research multi-agent assistant.

## Overview
This project provides a clean Python foundation for building an MVP research workflow with:
- 1 orchestrator that coordinates tasks
- up to 3 focused agents
- pluggable LLM providers and tools
- clear separation of prompts, schemas, and services

## MVP Direction
The initial MVP focuses on:
1. accepting a research question or task
2. routing work through orchestrator + agents
3. collecting synthesized outputs
4. saving results to structured output files

## Project Structure

```text
cite-mind/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py
├── config.py
├── app/
│   ├── orchestrator/
│   ├── agents/
│   ├── llm/
│   ├── tools/
│   ├── prompts/
│   ├── schemas/
│   ├── services/
│   └── utils/
├── data/
│   ├── uploads/
│   └── outputs/
└── tests/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Next Steps
- implement end-to-end orchestrator flow in `app/orchestrator/` to wire reader -> critic -> writer
- add automated tests for agent prompt building, schema parsing, and orchestration behavior
- add integration tests with mocked LLM providers to validate pipeline outputs
- expose a CLI/API workflow for running the multi-agent pipeline from a research input
