# Cross-stack integration and E2E tests

Place shared test fixtures and end-to-end tests here.

```
tests/
├── integration/   # API + DB integration tests
├── e2e/           # Playwright browser tests (Phase 2)
└── fixtures/      # Sample ABIs, contracts, golden files
```

Run after implementation:

```powershell
# Backend integration
cd backend && pytest ../tests/integration

# E2E (future)
cd frontend && npx playwright test
```
