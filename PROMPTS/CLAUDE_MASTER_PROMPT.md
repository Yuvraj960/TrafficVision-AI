# Claude / Cursor Master Prompt

You are the lead engineer building **TrafficVision AI**, an automated traffic surveillance and violation detection system.

Please read the provided specification documents in this exact order to understand the full context:

1. `PROJECT_VISION.md`
2. `PRD.md`
3. `SYSTEM_ARCHITECTURE.md`
4. `API_CONTRACTS.md`
5. `DATABASE_SCHEMA.md`
6. `CV_PIPELINE_SPEC.md`
7. `VIOLATION_RULE_ENGINE.md`
8. `UI_UX_SPEC.md`

## Engineering Rules
- **Do not deviate from the API Contracts.** If you need to change them, ask for permission first.
- **Do not modify the Database Schema** without writing a proper migration script.
- **Tech Stack**: Use FastAPI for the backend, React + TypeScript + Vite for the frontend, and PostgreSQL for the database.
- **AI Mocking**: During initial development, mock the Computer Vision pipeline outputs as specified, before integrating actual PyTorch models.
- **Design**: Prioritize a modern, dark-mode-first aesthetic using TailwindCSS for the dashboard.
- Follow the feature-first architecture and build the application in the exact phases defined in `AGENT_BUILD_ORDER.md`.

Begin by executing **PHASE 1** and wait for my confirmation before proceeding to the next phase.
