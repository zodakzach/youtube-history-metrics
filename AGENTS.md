# Repository Guidelines

## Project Structure & Module Organization
YouTube History Metrics is split into `Backend/` and `Frontend/`. The FastAPI app lives in `Backend/src/` with modules for ingestion (`data_processing.py`), analytics (`analytics.py`), Redis session state (`redis_utils.py`), and the ASGI entry point (`main.py`). Shared data contracts sit in `models.py`, while automated checks live in `Backend/tests/`. HTMX templates and static assets reside under `Frontend/templates/` and `Frontend/static/` (Tailwind CSS compiles into `static/css/app.css`). Keep reusable fragments in `templates/partials/` and place uploaded media in `static/images/`.

## Build, Test, and Development Commands
- `pip install -r Backend/requirements.txt` — install Python dependencies.
- `npm install` (run inside `Frontend/`) — install the UI toolchain.
- `npm run dev` — watch Tailwind, bundle assets, and launch `uvicorn` with reload; ensure `UPSTASH_REDIS_URL` is set (falls back to `REDIS_HOST:REDIS_PORT` if you prefer local Redis).
- `npm run build` — produce production-ready assets via Rollup and Tailwind.
- `npm run start` — single-run build followed by the FastAPI server for lightweight demos.

## Coding Style & Naming Conventions
Follow PEP 8 in `Backend/src` (4-space indents, snake_case for modules and functions, PascalCase for data classes). Prefer type hints on public functions; new models should derive from `pydantic.BaseModel`. Frontend scripts use ES modules—default to camelCase for JavaScript and hyphenated filenames for HTMX partials. Run `npm run format` before committing template changes; it applies Prettier with Tailwind-aware sorting.

## Testing Guidelines
Backend tests rely on the standard-library `unittest` suite in `Backend/tests/`. Name new files `<module>_tests.py` and test classes `Test<Feature>`. Execute `python -m unittest discover Backend/tests` from the repo root, or target a module with `python -m unittest Backend.tests.analytics_tests`. Store sizeable fixtures in `Backend/tests/fixtures/` (create if absent) to keep tests lean. Document any manual HTMX flows in PRs until automated frontend coverage is added.

## Commit & Pull Request Guidelines
Keep commits small and descriptive—present-tense summaries such as `update redis session cleanup`. Reference the touched surface in the subject (`backend:`, `frontend:`) when helpful. PRs should include purpose, setup steps, test output (`python -m unittest` and/or `npm run build`), and screenshots for UI changes. Link issues where relevant and call out new environment variables so reviewers can refresh `.env` settings before deploying.
