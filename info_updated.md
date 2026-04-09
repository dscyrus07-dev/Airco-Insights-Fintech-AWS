# Airco Insights - System Architecture and Real Runtime Documentation

This document describes how the current codebase works today, based on actual implementation across frontend, backend, infra, and supporting services.

Date of documentation update: 2026-04-09
Workspace: X:\FinTech SAAS\Airco Insights Fintech

## 1) High-level system overview

Airco Insights is a bank statement processing platform with:

1. Next.js frontend for login and dashboard UX
2. FastAPI backend (monolith) as primary runtime API and processing engine
3. Supporting microservices (auth, file, pdf, ai, report) for gradual migration
4. Redis for async job tracking
5. RabbitMQ for event-driven async processing
6. MinIO for object storage (uploads/reports)
7. PostgreSQL for metadata/history and domain tables
8. Nginx as reverse proxy and TLS termination in deployed environments

## 2) Deployment topology (docker-compose)

Primary local/dev compose stack is defined in:
- docker-compose.yml

Main containers:
- frontend (3000)
- backend (8000)
- auth-service (8001)
- file-service (8002)
- pdf-service (8003)
- ai-service (8004)
- report-service (8005)
- app-postgres (5434 -> 5432)
- keycloak (8080) + keycloak-postgres
- redis (6379)
- rabbitmq (5672, 15672)
- minio (9000, 9001)

Production compose file:
- docker-compose.prod.yml
Contains a lighter setup focused on frontend + backend with externalized infra expectations.

## 3) Request flow: how the system works end-to-end

### 3.1 User login and session

Frontend login page:
- frontend/app/page.tsx

Current behavior:
- Custom login form posts directly to Keycloak token endpoint (`password` grant).
- Access token and refresh token are stored in session storage and mirrored to cookies.
- Token payload is decoded client-side for user identity headers.

Key files:
- frontend/lib/sessionToken.ts
- frontend/lib/keycloak.ts
- frontend/contexts/AuthContext.tsx

### 3.2 Upload + processing flow (current primary path)

Dominant runtime path is asynchronous processing via backend:

1. Dashboard submits PDF + metadata to backend endpoint:
   - POST /api/upload/bank-statement-async
   - backend/app/api/routes/upload_async.py
2. Backend validates and stores upload temp file.
3. Backend uploads original PDF to MinIO bucket `airco-files`.
4. Backend creates async job in Redis.
5. Backend writes upload record into Postgres `user_file_records`.
6. Backend publishes RabbitMQ event `file.uploaded` on exchange `file_processing`.
7. Backend event consumer receives queue message and runs bank pipeline in-process.
8. Pipeline outputs Excel report and metrics.
9. Backend uploads Excel to MinIO bucket `airco-reports`.
10. Job status in Redis becomes `completed` or `failed`.
11. Frontend polls job status and enables report download.

Core files for this flow:
- backend/app/api/routes/upload_async.py
- backend/app/services/message_queue.py
- backend/app/services/event_consumer.py
- backend/app/services/pipeline_orchestrator.py
- backend/app/services/redis_job_store.py
- backend/app/services/file_history_service.py

### 3.3 Job polling and download

Endpoints:
- GET /api/jobs/{job_id}
- GET /api/jobs/{job_id}/download

Behavior:
- Job state is fetched from Redis.
- Download returns local file if still present, else streams from MinIO object key.

Files:
- backend/app/api/routes/jobs.py

### 3.4 Profile/history

Endpoint:
- GET /api/profile/history

Behavior:
- Resolves user identity from token or forwarded user headers.
- Reads upload/report history from Postgres `user_file_records`.

File:
- backend/app/api/routes/profile.py

### 3.5 Sync/learning events (current state)

Endpoint:
- POST /api/sync

Behavior:
- Accepts sheet data and learning events.
- Stores observations through learning store and returns promoted rule hints.
- Does not implement full persisted sync pipeline yet.

File:
- backend/app/api/routes/sync.py

## 4) Backend architecture details

Backend entrypoint:
- backend/app/main.py

Startup lifecycle performs:
- DB initialization (`initialize_database`)
- task processor startup
- RabbitMQ connection bootstrap
- event consumer start

Routers included:
- `/process` and download routes (sync/legacy path)
- `/api/upload/*` async and migration routes
- `/api/jobs/*`
- `/api/profile/*`
- `/api/sync`
- `/api/feedback/*` (placeholder/disabled learning features)

### Bank processing engine

Routing + orchestration:
- backend/app/services/pipeline_orchestrator.py

Supported bank keys in orchestrator:
- hdfc
- axis
- icici
- kotak
- sbi
- (extra aliases present such as hsbc/state bank, but runtime processor mapping exists for above core banks)

Per-bank modules:
- backend/app/services/banks/hdfc/*
- backend/app/services/banks/axis/*
- backend/app/services/banks/icici/*
- backend/app/services/banks/kotak/*
- backend/app/services/banks/sbi/*

Typical processor components:
- parser
- rule engine
- recurring engine
- reconciliation
- report/excel generator
- optional AI fallback hooks (bank-specific)

## 5) Frontend architecture details

Framework:
- Next.js 14 + React 18 + TypeScript + Tailwind

Main UI:
- frontend/app/dashboard/page.tsx
- frontend/app/components/Dashboard.tsx
- multi-step statement processing flow with status polling

Frontend API layer behavior:
- Some routes proxy to backend via Next API routes (`frontend/app/api/**`)
- Dashboard currently calls backend directly using `NEXT_PUBLIC_API_URL` for key flows.

Important result:
- There are both direct-backend and proxy-based integration patterns active at the same time.

## 6) Microservices status (real current integration)

Services present:
- auth-service
- file-service
- pdf-service
- ai-service
- report-service

Current practical status:
- `auth-service` is integrated and used by backend token verification client.
- `file/pdf/ai/report` services are implemented and containerized but not the primary execution path for statement processing in current backend flow.
- Main processing remains in backend in-process bank modules, with RabbitMQ + event consumer for async orchestration.

Interpretation:
- Architecture is in migration mode: hybrid monolith-first runtime with partially active microservices.

## 7) Data stores and schema

### PostgreSQL (app-postgres)

Backend SQLAlchemy models:
- merchants
- transactions
- user_file_records

Most actively used table in current UX flow:
- user_file_records
Used for uploads, report history, status snapshots, and user profile summary.

Files:
- backend/app/database/models.py
- backend/app/database/session.py

### Redis

Used for async job persistence:
- Job object serialized and stored with TTL (24h)
- Indexed by status and user

File:
- backend/app/services/redis_job_store.py

### RabbitMQ

Used for queueing and event-driven processing:
- exchanges: file_processing, pdf_processing, ai_processing, report_processing
- key live path: `file.uploaded` -> `file_upload_queue`

File:
- backend/app/services/message_queue.py

### MinIO

Buckets used:
- `airco-files` for uploaded source PDFs
- `airco-reports` for generated Excel outputs

Uploads are best-effort in helper (non-fatal on failure), but async flow expects MinIO for durable retrieval when local temp files expire.

File:
- backend/app/utils/file_handler.py

## 8) Technology stack

### Backend and services
- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy
- Redis client (async)
- RabbitMQ (pika)
- Boto3/MinIO S3 API
- PDF tooling: pdfplumber, PyMuPDF, pikepdf
- Excel tooling: openpyxl, xlsxwriter
- AI SDKs available: anthropic, groq

### Frontend
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Handsontable and spreadsheet-related libs
- keycloak-js package present, but custom token flow is currently dominant

### Infra
- Docker Compose
- Nginx reverse proxy
- Keycloak for IAM
- PostgreSQL
- Redis
- RabbitMQ
- MinIO

## 9) Security/auth model (current)

Current auth model is mixed:
- Frontend performs password grant directly against Keycloak.
- Backend validates bearer tokens by calling auth-service `/auth/verify-token`.
- If auth-service call fails, backend can decode JWT payload locally as fallback in optional and required deps.
- User identity propagation also uses forwarded headers (`X-Airco-User-*`) in several paths.

Implication:
- Functional, but there are multiple trust paths that should be tightened and unified.

## 10) Pros and cons of current architecture

### Pros

1. Practical scalability path
   - Async jobs + Redis + RabbitMQ already reduce blocking request load.
2. Good separation direction
   - Service boundaries are clearly modeled (auth/file/pdf/ai/report).
3. Strong domain specialization
   - Bank-specific processing modules improve deterministic control and debugging.
4. Durable artifacts
   - MinIO storage supports report retrieval after local temp cleanup.
5. Operational flexibility
   - Monolith path remains available while migration proceeds.

### Cons

1. Architectural duality
   - Monolith and microservice paths coexist, increasing cognitive and operational complexity.
2. Integration inconsistency
   - Frontend uses both direct backend calls and Next API proxy routes.
3. Auth flow fragmentation
   - Token verification relies on multiple fallback methods and forwarded headers.
4. Partial service maturity mismatch
   - Some standalone services use in-memory caches/metadata stores (not full persistent state).
5. Documentation drift risk
   - Some older docs no longer match actual runtime flows.

## 11) Operational notes and known hotspots

1. Secrets handling
   - `.env` currently contains sensitive keys; rotate and move to secret manager for production.
2. Queue failure fallback
   - Upload async path falls back to local task processor when Rabbit publish fails, which is good for resilience.
3. Temp/local vs object storage
   - Downloads may use local file path first, then MinIO fallback.
4. Learning/feedback modules
   - Feedback APIs are largely placeholder/disabled pending architecture cleanup.

## 12) Suggested next architecture milestones

1. Choose one canonical API integration style in frontend (direct or proxy) and standardize.
2. Promote service-to-service ownership:
   - backend orchestrator delegates parsing/categorization/reporting to pdf/ai/report services via stable contracts.
3. Consolidate authentication path:
   - remove optional trust-by-header where possible and enforce signed token validation consistently.
4. Replace in-memory stores in standalone services with persistent backends.
5. Add versioned API contracts and architecture tests for queue/event schemas.
6. Keep this file synced with each migration phase to prevent drift.

## 13) File map (quick pointers)

- Frontend dashboard: frontend/app/components/Dashboard.tsx
- Frontend upload API route: frontend/app/api/upload/route.ts
- Backend app entry: backend/app/main.py
- Async upload route: backend/app/api/routes/upload_async.py
- Job routes: backend/app/api/routes/jobs.py
- Profile history route: backend/app/api/routes/profile.py
- Sync route: backend/app/api/routes/sync.py
- Pipeline orchestrator: backend/app/services/pipeline_orchestrator.py
- RabbitMQ client: backend/app/services/message_queue.py
- Event consumer: backend/app/services/event_consumer.py
- Redis job store: backend/app/services/redis_job_store.py
- File history service: backend/app/services/file_history_service.py
- DB models: backend/app/database/models.py
- Nginx config: nginx/nginx.conf
- Docker topology: docker-compose.yml

---

This document is intended to represent the current real behavior of the codebase, not just intended target architecture.
