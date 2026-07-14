# CareerOS

CareerOS is a modern AI SaaS project for managing a job search from one intelligent workspace. The project is currently focused on a Next.js frontend landing page and a FastAPI backend foundation, with Docker support for running the full stack locally.

## Status

Currently in working phase.

## Tech Stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui, pnpm
- Backend: FastAPI, Python, uv
- Infrastructure: Docker Compose, PostgreSQL, Redis

## Installation

### Prerequisites

- Node.js
- pnpm
- Python 3.13
- uv
- Docker Desktop

### Run With Docker

```bash
docker compose build
docker compose up -d
```

Frontend runs at:

```text
http://localhost:3000
```

Backend runs at:

```text
http://localhost:8000
```

### Run Frontend Locally

```bash
cd frontend
pnpm install
pnpm dev
```

### Run Backend Locally

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

## Project Structure

```text
frontend/   Next.js frontend application
backend/    FastAPI backend application
docker-compose.yml
```