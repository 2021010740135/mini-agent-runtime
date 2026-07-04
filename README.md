# Mini Agent Runtime

A minimal agent runtime built from scratch using Python 3.11+ and OpenAI-compatible Chat Completion API.

## Architecture

The project implements a lightweight agent loop with tool-calling capabilities, memory management, and session persistence — without relying on any agent frameworks like LangGraph, OpenHands, AutoGen, or OpenClaw.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # edit .env with your API key
python main.py
```

## Project Structure

- `agent/` — Core agent runtime, LLM client, decision engine, session & memory management
- `tools/` — Pluggable tool system with registry, calculator, search, todo, and document reader
- `tests/` — Unit tests for core modules
- `data/sessions/` — Session persistence directory
- `logs/` — Log output directory
