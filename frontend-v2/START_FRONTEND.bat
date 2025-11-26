@echo off
echo ====================================
echo   عين (Ain) - Frontend V2
echo   Pixel-Perfect Arabic RTL UI
echo ====================================
echo.

echo Checking dependencies...
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    echo.
)

echo Starting development server...
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:5000
echo.
echo Press Ctrl+C to stop
echo.

npm run dev

pause
