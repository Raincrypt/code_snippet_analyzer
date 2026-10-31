@echo off
rem Stops the Docker version of the app. Your saved reviews and the downloaded model are kept.
rem To delete them too, run:  docker compose --profile model down -v
setlocal
cd /d "%~dp0"
docker compose --profile model down
pause
