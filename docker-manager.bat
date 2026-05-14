@echo off
setlocal enabledelayedexpansion

set "COMPOSE_CMD=docker compose -f docker-compose.yml -f docker-compose.local.yml --env-file local.env"

echo ========================================
echo Airco Insights Docker Manager - Local Dev
echo ========================================
echo.

:menu
echo Choose an option:
echo 1. Start local dev
echo 2. Restart local dev
echo 3. Rebuild local dev
echo 4. Stop local dev
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto restart
if "%choice%"=="3" goto rebuild
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto exit
echo Invalid choice. Please try again.
echo.
goto menu

:start
echo.
echo Starting local development stack...
%COMPOSE_CMD% up -d
echo.
echo Local development stack started successfully!
echo.
echo Access URLs:
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo Auth Service: http://localhost:8001
echo File Service: http://localhost:8002
echo PDF Service: http://localhost:8003
echo AI Service: http://localhost:8004
echo Report Service: http://localhost:8005
echo Keycloak: http://localhost:8080
echo MinIO Console: http://localhost:9001
echo RabbitMQ Management: http://localhost:15672
echo.
pause
goto menu

:restart
echo.
echo Restarting local development stack...
%COMPOSE_CMD% restart
echo.
echo Local development stack restarted successfully!
echo.
pause
goto menu

:rebuild
echo.
echo Rebuilding local development stack...
%COMPOSE_CMD% up -d --build
echo.
echo Local development stack rebuilt and started successfully!
echo.
pause
goto menu

:stop
echo.
echo Stopping local development stack...
%COMPOSE_CMD% down
echo.
echo Local development stack stopped successfully!
echo.
pause
goto menu

:exit
echo.
echo Goodbye!
exit /b 0
