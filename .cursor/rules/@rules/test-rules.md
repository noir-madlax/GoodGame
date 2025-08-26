# GoodGame Unit Testing Rules and Templates

This document defines how we author, run, and evaluate automated tests for both frontend and backend. It is intended for humans and AI assistants and should be kept current as our test strategy evolves.

## Principles
- Tests are part of the product quality bar, not optional
- Prefer fast, deterministic, isolated tests
- Test behaviors and contracts, not implementation details
- Aim for meaningful coverage where it reduces risk most

## Scope and Types
- Frontend
  - Component tests: rendering, interactions, accessibility
  - API route tests: input validation and response shapes
- Backend
  - Pure function tests: data transforms and parsing
  - Integration tests (lightweight): repository and fetcher boundaries using fakes or recorded fixtures

## Frontend Testing
### Tools
- Jest/Vitest + React Testing Library (recommended setup)

### Conventions
- Place tests alongside code or under `__tests__/` with `.test.ts(x)` suffix
- Use descriptive test names and arrange-act-assert pattern
- Mock network calls; avoid hitting real external services
- Validate a11y attributes and keyboard interactions

### Example Test Skeleton
```ts
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExampleComponent } from '@/components/example-component'

describe('ExampleComponent', () => {
  it('renders title and handles click', async () => {
    const user = userEvent.setup()
    render(<ExampleComponent title="Hello" />)
    expect(screen.getByRole('heading', { name: /hello/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /open/i }))
    expect(screen.getByText(/opened/i)).toBeVisible()
  })
})
```

## Backend Testing
### Tools
- pytest (recommended)

### Conventions
- Tests live under `backend/tests/` or near modules with `.test.py`
- Use fixtures for common setup; avoid global state
- Record sample fixtures under version control where possible (e.g., JSON in `backend/test/output`) and avoid network by default

### Example Test Skeleton
```python
import json
from tikhub_api.fetchers.douyin_video_fetcher import DouyinVideoFetcher

def test_parse_video_info_fixture():
    with open('backend/tikhub_api/downloads/douyin/7383012850161241385/video_info.json', 'r') as f:
        data = json.load(f)
    fetcher = DouyinVideoFetcher()
    parsed = fetcher.parse_video_info(data)
    assert parsed.id
    assert isinstance(parsed.stats.likes, int)
```

## Coverage Targets
- Frontend: aim for 70%+ statements/branches on critical components and API routes
- Backend: aim for 70%+ on core parsing, repositories, and workflows

## Running Tests and Reporting
- Frontend: `pnpm test` (configure in `frontend/package.json`) and optional coverage with `--coverage`
- Backend: `pytest -q` and coverage with `pytest --cov`
- Generate reports in CI; store artifacts for failed runs

## Test Data and Fixtures
- Keep fixtures small, readable, and representative
- Anonymize any sensitive values in stored samples
- Prefer JSON fixtures for API payloads

## MCP and Supabase
- Reads are allowed through MCP for verification
- Any mutation to Supabase by AI requires explicit human instruction
- Prefer stubbed repositories for unit tests; use live DB only in approved integration tests

## Pull Request Expectations
- New features include tests or a clear rationale when tests are not needed
- Bug fixes include regression tests
- CI must execute test suites and report pass/fail with coverage deltas

## Flaky Tests Policy
- Quarantine flaky tests and fix within one sprint
- Do not use excessive retries; stabilize through deterministic setup

## Accessibility Testing
- Validate roles, names, and keyboard navigation in component tests
- Consider automated a11y checks (e.g., axe) for critical pages


