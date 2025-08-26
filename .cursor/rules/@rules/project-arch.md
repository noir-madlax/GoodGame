# GoodGame Project Architecture Blueprint

This document describes the technical architecture, core modules, runtime interactions, and ownership model for the GoodGame project. It serves as the single source of truth for architectural decisions and must be updated as the system evolves.

## Goals
- Clear, shared understanding of system boundaries and contracts
- Make trade-offs explicit and reviewable
- Enable safe, incremental changes with minimal coupling

## System Overview
- Monorepo with separate frontend and backend folders
- Frontend: Next.js App Router, TypeScript, TailwindCSS, shadcn/ui
- Backend: Python modules for data fetching, downloading, ORM, and workflows
- Data: Supabase Postgres (GoodGame, id: kctuxiejpwykosghunib)

## High-Level Architecture
- Client (browser) → Next.js UI → API Routes (Next.js or backend services) → Supabase / External Platforms (Douyin, Xiaohongshu, etc.)

### Frontend Modules
- `app/`: Route handlers, pages, and API routes
  - `app/api/video/card/route.ts`: Returns video card data
  - `app/api/video/detail/route.ts`: Returns video detail data
- `components/`: Presentational and container components (shadcn/ui based)
- `hooks/`: Reusable React hooks, e.g., `use-toast`, `use-mobile`
- `lib/`: Utilities such as `supabase.ts` client and helpers
- `public/`: Static assets and sample JSON under `public/data`

Key concerns:
- Server components and client components separation
- API route typing and validation
- Accessibility (a11y) and internationalization (English-only content)

### Backend Modules
- `tikhub_api/`:
  - `fetchers/`: Platform-specific fetchers (e.g., `douyin_video_fetcher.py`, `xiaohongshu_fetcher.py`) and `fetcher_factory.py`
  - `orm/`: `models.py`, repositories for posts and comments, `supabase_client.py`
  - `video_downloader.py`: Downloads and stores media in `downloads/`
  - `workflow.py`: Orchestrates fetching, processing, and persistence

### Data Layer
- Supabase Postgres stores posts, comments, and related metadata
- Access via `supabase_client.py` and repositories
- All AI-driven DB modifications must use MCP with explicit human approval; reads are safe

## Cross-Cutting Concerns
- Observability: structured logs (backend), meaningful errors surfaced to UI
- Security: secrets via environment variables; no secrets in code
- Performance: simple first; cache where needed; paginate large lists

## API Contracts
Example: Video detail API
- Request: `GET /api/video/detail?id=<string>`
- Response: `{ id: string; title: string; author: string; stats: { likes: number; comments: number; shares: number } }`
- Error model: `{ error: string; code?: string }` with appropriate HTTP status

Validation guidelines:
- Validate required query params and payload types
- Sanitize external identifiers before downstream calls

## Error Handling Strategy
- Frontend: show toast or inline error with retry; log to console in dev
- Backend: raise descriptive exceptions; never swallow; return normalized error payloads to API consumers

## Deployment and Environments
- `main` is deployable; feature branches for work-in-progress
- Frontend must pass `pnpm build` before merge
- Backend deployments are manual; server restarts are controlled by ops

## Ownership and Responsibility Matrix
- Frontend UI/UX: Frontend team
- API route design and types: Shared
- Backend fetchers and workflows: Backend team
- Data schema and migrations: Backend + DBA
- Supabase access via MCP: AI with human approval for mutating actions

## Architectural Decisions (ADRs)
Track key decisions here with date and rationale. Example entries:
- 2025-08-19: Use Next.js App Router for SSR/ISR and API routes; aligns with shadcn/ui and Tailwind
- 2025-08-19: Supabase as primary data store; strict MCP mediation for AI writes

## Future Work
- Introduce unified logging and tracing correlation IDs
- Add schema validation in API routes (e.g., Zod)
- Document data models and ERD


