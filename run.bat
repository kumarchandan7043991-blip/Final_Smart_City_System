@echo off
echo ---------------------------------------
echo Starting Smart Traffic Dashboard...
echo ---------------------------------------

echo [1/2] Starting Python Backend ...
start "Backend (Python)" cmd /k "cd backend && set OPENBLAS_NUM_THREADS=1 && set OMP_NUM_THREADS=1 && python app.py"

echo [2/2] Starting React Frontend ...
cd frontend
start "Frontend (React)" cmd /k "set PORT=3001 && set NODE_OPTIONS=--max-old-space-size=8192 --openssl-legacy-provider && npm start"

echo.
echo Both services are starting up!
echo A new browser window will open automatically.
echo.
pause
