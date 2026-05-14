# Local Docker Setup

This guide explains how to run Airco Insights locally with Docker **without touching AWS/EC2 configuration**.

## What this setup uses

- `docker-compose.yml` as the base stack
- `docker-compose.local.yml` as the local-only override
- `docker-manager.bat` for a simple Windows menu
- `scripts/setup-local-keycloak.ps1` to create the local Keycloak realm, client, and test user

## What it does not use

- `docker-compose.ec2.yml`
- `scripts/deploy-ec2.sh`
- any AWS public domain or SSL certificate settings

## Prerequisites

- Docker Desktop installed
- PowerShell 5.1+ on Windows
- `docker compose` available from the terminal

## Start the local stack

### Option 1: Windows menu

Run:

```bat
docker-manager.bat
```

Then choose:

- `7` = **Start local dev stack**

### Option 2: Direct command

Run:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

## Initialize Keycloak for local login

After the containers are running, set up the local Keycloak realm and test user:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-local-keycloak.ps1
```

This script creates or updates:

- Realm: `airco-insights`
- Client: `frontend-app`
- Client secret: `airco-frontend-secret`
- Test user: `test@airco.com`
- Test password: `Test123!`

## Login flow

Open:

- Frontend: `http://localhost:3000`

Then sign in with:

- Email: `test@airco.com`
- Password: `Test123!`

The frontend login form calls:

- `POST /api/auth/login`

That routes to the local auth service, which forwards credentials to the local Keycloak instance.

## Service URLs

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Auth Service: `http://localhost:8001`
- File Service: `http://localhost:8002`
- PDF Service: `http://localhost:8003`
- AI Service: `http://localhost:8004`
- Report Service: `http://localhost:8005`
- Keycloak: `http://localhost:8080`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- RabbitMQ Management: `http://localhost:15672`

## Default local environment values

The local overlay expects localhost-friendly defaults.

Recommended values if you use a `.env` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=airco-insights
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=frontend-app
NEXT_PUBLIC_AIRCO_API_KEY=
```

## Troubleshooting

### Login fails with 401

- Run the local Keycloak setup script again
- Confirm the test user exists
- Confirm the client secret is `airco-frontend-secret`
- Restart the auth service after Keycloak setup if needed

### Backend cannot connect to services

- Make sure the local stack was started with `docker-compose.local.yml`
- Check that the service ports are published on localhost

### Keycloak page opens but login does not work

- Verify `http://localhost:8080` is reachable
- Re-run `scripts/setup-local-keycloak.ps1`
- Ensure the frontend is using `localhost:8080` and not the AWS domain

### If you already ran the AWS stack

Stop it first so ports do not conflict:

```bash
docker compose down
```

Then start the local stack with the local override.

## Clean shutdown

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml down
```
