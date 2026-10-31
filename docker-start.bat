@echo off
rem Runs the whole app in Docker (Docker Desktop must be running).
rem
rem   docker-start.bat          placeholder reviewer
rem   docker-start.bat model    real AI model (downloads about 5 GB the first time)
rem
rem Open http://localhost:8080 when it says the website is started. Stop with docker-stop.bat.
setlocal
cd /d "%~dp0"
title Code Snippet Analyzer - Docker

docker info >nul 2>nul
if errorlevel 1 (
  echo Docker is not running. Start Docker Desktop, wait until it says it is running, then try again.
  pause
  exit /b 1
)

if /i "%~1"=="model" (
  set "REVIEWER=llm"
  docker compose --profile model up --build -d
) else (
  docker compose up --build -d
)
if errorlevel 1 (
  echo.
  echo Docker could not start the app. See the messages above.
  pause
  exit /b 1
)

echo.
echo Started. Open http://localhost:8080
if /i "%~1"=="model" echo The model downloads in the background the first time: docker compose logs -f model-pull
start "" http://localhost:8080
pause
