@echo off
setlocal enabledelayedexpansion

set "COMPOSE_CMD=docker compose -f docker-compose.yml -f docker-compose.local.yml --env-file local.env"

echo ========================================
echo  Airco Insights Docker Manager (Local)
echo  Database: Supabase (cloud)
echo ========================================
echo.

:menu
echo Choose an option:
echo  1. Start local dev stack
echo  2. Restart local dev stack
echo  3. Rebuild local dev stack (full rebuild)
echo  4. Stop local dev stack
echo  5. View backend logs (live)
echo  6. View all service status
echo  7. Setup Keycloak (run after first start)
echo  8. Exit
echo.
set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto restart
if "%choice%"=="3" goto rebuild
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto status
if "%choice%"=="7" goto keycloak
if "%choice%"=="8" goto exit
echo Invalid choice. Please try again.
echo.
goto menu

:start
echo.
echo Starting local development stack...
echo NOTE: PostgreSQL is Supabase (cloud) - no local DB container.
echo.
%COMPOSE_CMD% up -d
echo.
echo ----------------------------------------
echo  Stack started successfully!
echo ----------------------------------------
echo  Frontend:           http://localhost:3000
echo  Backend API:        http://localhost:8000
echo  Backend API Docs:   http://localhost:8000/docs
echo  Keycloak:           http://localhost:8080
echo  MinIO Console:      http://localhost:9001
echo  RabbitMQ Mgmt:      http://localhost:15672
echo ----------------------------------------
echo.
pause
goto menu

:restart
echo.
echo Restarting local development stack...
%COMPOSE_CMD% restart
echo.
echo Stack restarted successfully!
echo.
pause
goto menu

:rebuild
echo.
echo Rebuilding local development stack (full rebuild)...
%COMPOSE_CMD% up -d --build
echo.
echo ----------------------------------------
echo  Stack rebuilt and started!
echo ----------------------------------------
echo  Frontend:           http://localhost:3000
echo  Backend API:        http://localhost:8000
echo  Backend API Docs:   http://localhost:8000/docs
echo  Keycloak:           http://localhost:8080
echo  MinIO Console:      http://localhost:9001
echo  RabbitMQ Mgmt:      http://localhost:15672
echo ----------------------------------------
echo.
pause
goto menu

:stop
echo.
echo Stopping local development stack...
%COMPOSE_CMD% down
echo.
echo Stack stopped successfully!
echo.
pause
goto menu

:logs
echo.
echo Streaming backend logs (Ctrl+C to stop)...
echo.
%COMPOSE_CMD% logs -f backend
echo.
pause
goto menu

:status
echo.
echo Current container status:
echo.
%COMPOSE_CMD% ps
echo.
pause
goto menu

:keycloak
echo.
echo Setting up Keycloak realm and test user...
echo Make sure the stack is running first (option 1).
echo.
powershell -ExecutionPolicy Bypass -File "scripts\setup-local-keycloak.ps1"
echo.
echo Keycloak setup complete!
echo Login with: test@airco.com / Test123!
echo.
pause
goto menu

:exit
echo.
echo Goodbye!
exit /b 0
