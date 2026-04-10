# Airco Insights AWS Setup Pack

This repo now includes a repeatable AWS setup pack with:

- Local Windows launcher: [setup-aws-local.bat](X:\FinTech SAAS\Airco Insights Fintech\Migration Setup\setup-aws-local.bat)
- Local Windows PowerShell worker: [setup-aws-local.ps1](X:\FinTech SAAS\Airco Insights Fintech\Migration Setup\setup-aws-local.ps1)
- EC2 Linux setup and deploy script: [setup-aws-server.sh](X:\FinTech SAAS\Airco Insights Fintech\Migration Setup\setup-aws-server.sh)

## What Each Script Does

### Local Windows

Use [setup-aws-local.bat](X:\FinTech SAAS\Airco Insights Fintech\Migration Setup\setup-aws-local.bat) from Windows.

It will:

- create a clean deployment archive
- upload the archive to EC2
- upload the server setup script to EC2
- run the remote setup or deploy action over SSH

### AWS Server

Use [setup-aws-server.sh](X:\FinTech SAAS\Airco Insights Fintech\Migration Setup\setup-aws-server.sh) on EC2.

It will:

- detect the Linux distribution
- install Docker if needed
- install Docker Compose if needed
- prepare the project directory
- unpack the uploaded project archive
- create `.env` from `.env.ec2.example` if needed
- clean common bad build artifacts like `.next`, `node_modules`, and `__pycache__`
- create a temporary self-signed SSL certificate if no cert is present
- run the EC2 deploy flow

## Recommended Workflow

From your local Windows machine:

```bat
Migration Setup\setup-aws-local.bat full
```

Useful actions:

```bat
Migration Setup\setup-aws-local.bat ssh
Migration Setup\setup-aws-local.bat status
Migration Setup\setup-aws-local.bat deploy
Migration Setup\setup-aws-local.bat logs
```

If you want logs for one service, use PowerShell:

```powershell
.\Migration Setup\setup-aws-local.ps1 -Action logs -LogsService frontend
```

## Required Inputs

Before production deployment, confirm these files and values:

- [`.env`](X:\FinTech SAAS\Airco Insights Fintech\.env)
- [`.env.ec2.example`](X:\FinTech SAAS\Airco Insights Fintech\.env.ec2.example)
- SSL cert files in `/opt/airco/ssl`

If SSL cert files are missing, the server script generates temporary self-signed certs so the stack can still boot.

## Vibe Code Editor Prompt

Use this prompt in Vibe / Cascade / agent mode:

```text
You are working inside the Airco Insights repo.

Use the existing deployment pack instead of inventing a new setup flow.

Primary files:
- Migration Setup/setup-aws-local.bat
- Migration Setup/setup-aws-local.ps1
- Migration Setup/setup-aws-server.sh
- scripts/deploy-ec2.sh
- .env.ec2.example

Rules:
- On Windows, use Migration Setup/setup-aws-local.bat as the main entrypoint.
- On EC2, use Migration Setup/setup-aws-server.sh.
- Do not reintroduce localhost browser API URLs.
- Keep frontend browser calls same-origin through /api.
- Keep Keycloak behind the public domain and Nginx.
- Keep only intended public ports exposed.
- If changing AWS hosts, update only the host, key path, user, and remote directory variables in Migration Setup/setup-aws-local.ps1 or pass them as parameters.
- Preserve .env when refreshing the EC2 project directory.
- Prefer idempotent fixes and reusable scripts over one-off shell commands.

What to do:
1. Validate .env values.
2. Validate docker-compose.yml and docker-compose.ec2.yml.
3. Use the provided setup scripts for upload, bootstrap, and deploy.
4. If deployment fails, fix the repo and rerun the same scripts.
5. Summarize any file changes made.
```

## Changing AWS Servers Later

You do not need to rewrite the flow.

Update the parameters in [setup-aws-local.ps1](X:\FinTech SAAS\Airco Insights Fintech\Migration Setup\setup-aws-local.ps1):

- `Host`
- `User`
- `KeyPath`
- `RemoteProjectDir`

Then run:

```bat
Migration Setup\setup-aws-local.bat full
```

## Notes

- The EC2 machine is Linux, so the server-side setup script is `.sh`, not `.bat`.
- The `.bat` file is the local launcher and is the correct Windows entrypoint.
- This setup pack is intended to reduce repeated one-off manual fixes during future redeploys.
