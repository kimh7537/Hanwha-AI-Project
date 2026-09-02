# Repository Guidelines

## Project Structure & Module Organization

- `backend/app/` contains the FastAPI service. Shared Pydantic contracts live in `models/contracts.py`; HTTP routes are in `api/`; pipeline logic is grouped under `services/`; LLM adapters are under `llm/`.
- `backend/tests/` contains the pytest suite, and `backend/fixtures/` holds deterministic sample inputs and expected JSON/PPTX artifacts.
- `frontend/app/` contains the Next.js App Router entry points and global styles. Reusable UI belongs in `frontend/components/`; API, types, labels, and export helpers belong in `frontend/lib/`.
- `docs/` contains the module specifications (`00-overview.md` through `10-quality-safety.md`). Update relevant specs when behavior or contracts change. `.claude/` contains repository checks and demo scripts.

## Build, Test, and Development Commands

Run backend commands from `backend/` using the local virtual environment:

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Run frontend commands from `frontend/`:

```powershell
npm install                 # install dependencies
npm run dev                 # local Next.js server on port 3000
npm run lint                # ESLint
npm run build               # production build/type checks
```

Repository checks include `backend\.venv\Scripts\python.exe .claude\skills\contract-sync\check_contracts.py` and `backend\.venv\Scripts\python.exe .claude\skills\demo-check\run_demo.py`. Use `backend\scripts\build_fixtures.py` after intentional contract changes.

## Coding Style & Naming Conventions

Use 4-space indentation and type hints in Python; keep modules and functions `snake_case`, classes `PascalCase`, and constants `UPPER_SNAKE_CASE`. Follow the existing Pydantic models and explicit service boundaries. Use TypeScript with 2-space indentation, `PascalCase` React components, and `camelCase` helpers/variables. Keep shared backend/frontend labels and contracts synchronized.

## Testing Guidelines

Pytest discovers `backend/tests/test_*.py` (configured by `backend/pytest.ini`); add focused regression tests beside the affected module. Keep tests deterministic with the default `LLM_PROVIDER=mock`, and include fixture updates when serialized contracts change. Run `npm run lint` and `npm run build` for frontend changes.

## Commit & Pull Request Guidelines

Write concise, imperative commit subjects (for example, `Fix evidence reference validation`) and keep unrelated changes separate. Pull requests should describe user-visible behavior, list validation commands and results, identify contract or fixture changes, link the relevant issue/spec, and include screenshots or a short demo recording for UI changes.

## Security & Configuration Tips

Copy `.env.example` to a local `.env`; never commit API keys or `.env` files. Keep LLM calls behind the backend API, preserve mock-provider fallback behavior, and update CORS configuration deliberately when changing deployment origins.
