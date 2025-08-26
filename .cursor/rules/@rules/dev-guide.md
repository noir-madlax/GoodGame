# GoodGame Team Development Guide

This guide standardizes how we build, review, and ship software in the GoodGame monorepo. It applies to both the frontend (Next.js/TypeScript) and backend (Python) projects and is intended to be used by engineers and AI assistants.

## Objectives
- Consistent developer experience and code quality
- Predictable delivery using shared workflows
- Safe collaboration with clear ownership and responsibilities
- AI-assisted development that is auditable and reversible

## Tech Stack Summary
- Frontend: Next.js (App Router), TypeScript, TailwindCSS, shadcn/ui, pnpm
- Backend: Python 3, modular `tikhub_api` (fetchers, ORM, workflow), `backend/test` sandbox utilities
- Data: Supabase Postgres (project: GoodGame, id: kctuxiejpwykosghunib)

## Environment Setup
### Prerequisites
- Node.js (LTS) + pnpm
- Python 3.10+
- Git with access to the repository

### Frontend
1. Install dependencies
   - `pnpm install`
2. Local development
   - `pnpm dev`
3. Build (must succeed before merge)
   - `pnpm build`

### Backend
1. Create virtual environment and install requirements
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r backend/requirements.txt`
2. Run ad-hoc scripts from `backend/test` or `tikhub/` as needed

## Branching, Commits, and PRs
### Branching Model
- `main`: deployable at all times
- Feature branches: `feat/<scope>-<short-desc>`
- Fix branches: `fix/<scope>-<issue#-or-desc>`

### Conventional Commits
- feat: add a new feature
- fix: bug fix
- docs: documentation only changes
- refactor: code change that neither fixes a bug nor adds a feature
- chore: tooling/build/infra changes
- test: add or refactor tests only

Examples:
- `feat(frontend): add video detail page skeleton`
- `fix(backend): handle missing douyin video_info.json`

### Pull Requests
- Small, focused PRs are preferred
- Include clear description, screenshots for UI, and risk notes
- Link related issues/tasks
- CI must pass (build and lint)

PR checklist:
- [ ] Frontend builds: `pnpm build`
- [ ] Naming, accessibility, i18n (English-only user-facing)
- [ ] Security review (secrets, tokens, PII)
- [ ] Testing updated or added (if applicable)
- [ ] No unrelated changes

## Code Style and Conventions
### TypeScript/React (Frontend)
- Strong typing; avoid `any`
- Descriptive names; event handlers use `handleX`
- Early returns to reduce nesting
- Tailwind-only for styling; prefer semantic HTML and a11y attributes
- Keep components small and focused
- Utilities in `frontend/lib/` and `frontend/hooks/`

Accessibility:
- Interactive elements require keyboard handlers and `aria-*` where appropriate
- Images need `alt` text; decorative images use empty `alt` strings

File organization:
- Pages in `frontend/app/`
- Server routes in `frontend/app/api/`
- Shared UI in `frontend/components/`
- Public assets in `frontend/public/`

### Python (Backend)
- Follow PEP 8; descriptive function and variable names
- Keep modules cohesive: fetching in `tikhub_api/fetchers/`, ORM in `tikhub_api/orm/`
- Pure functions where reasonable; avoid unnecessary classes
- Log actionable messages; avoid noisy prints
- Handle network and IO errors explicitly with clear exceptions

## Linting and Formatting
- Respect existing linters and formatters
- Frontend: run TypeScript build to surface type issues
- Python: use `flake8`/`black` if configured; otherwise keep PEP 8

## Configuration and Secrets
- Do not commit secrets or API keys
- Use environment variables and `.env.local` for local overrides (untracked)
- For Supabase, use project-provided keys from a secure source

## Data and Supabase Usage
- Supabase project: GoodGame (id: kctuxiejpwykosghunib)
- All database operations by AI must use MCP and be read-only unless there is an explicit human instruction to modify or delete data
- Treat destructive operations with extreme caution and change management

## AI-Assisted Development Policy
- AI must follow this guide and project-specific rules
- AI should propose designs before large changes and keep edits minimal and localized
- AI must not introduce new dependencies or migrations without explicit approval
- AI should provide clear, well-structured edits and reference impacted files

## Security and Privacy
- Do not log secrets or sensitive user data
- Validate and sanitize external inputs (URLs, IDs, query params)
- Follow the principle of least privilege when accessing services

## Performance and Reliability
- Prefer simple, readable solutions first
- Cache or debounce heavy operations in the UI when needed
- Add guards and error boundaries around network calls and async flows

## Internationalization
- All user-visible content must be in English

## Documentation Expectations
- Keep `@rules/` up-to-date when introducing new patterns
- Update `project-arch.md` for architectural changes
- Update `test-rules.md` when test strategy evolves

## Common Workflows
### Adding a new frontend API route
1. Create handler in `frontend/app/api/.../route.ts`
2. Type inputs/outputs; validate payload
3. Add usage in components/hooks
4. Build and test locally

### Adding a new backend fetcher
1. Create a new fetcher in `tikhub_api/fetchers/`
2. Integrate with `fetcher_factory.py`
3. Add unit tests (see `test-rules.md`)
4. Document the flow in `project-arch.md`


