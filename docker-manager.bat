@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Airco Insights Docker Manager
echo ========================================
echo.

:menu
echo Choose an option:
echo 1. Start services
echo 2. Restart services
echo 3. Rebuild services
echo 4. Rebuild services (no cache)
echo 5. Stop services
echo 6. View logs
echo 7. Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto restart
if "%choice%"=="3" goto rebuild
if "%choice%"=="4" goto rebuild-no-cache
if "%choice%"=="5" goto stop
if "%choice%"=="6" goto logs
if "%choice%"=="7" goto exit
echo Invalid choice. Please try again.
echo.
goto menu

:start
echo.
echo Starting Docker services...
docker-compose up -d
echo.
echo Services started successfully!
echo.
echo Access URLs:
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo Keycloak: http://localhost:8080
echo MinIO Console: http://localhost:9001
echo RabbitMQ Management: http://localhost:15672
echo.
pause
goto menu

:restart
echo.
echo Restarting Docker services...
docker-compose restart
echo.
echo Services restarted successfully!
echo.
pause
goto menu

:rebuild
echo.
echo Rebuilding and starting Docker services...
docker-compose up --build -d
echo.
echo Services rebuilt and started successfully!
echo.
pause
goto menu

:rebuild-no-cache
echo.
echo Rebuilding Docker services (no cache)...
docker-compose build --no-cache
docker-compose up -d
echo.
echo Services rebuilt (no cache) and started successfully!
echo.
pause
goto menu

:stop
echo.
echo Stopping Docker services...
docker-compose down
echo.
echo Services stopped successfully!
echo.
pause
goto menu

:logs
echo.
echo Showing Docker logs (press Ctrl+C to exit)...
docker-compose logs -f
echo.
pause
goto menu

:exit
echo.
echo Goodbye!
exit /b 0
