@echo off
echo ========================================
echo Restarting Backend Server
echo ========================================
echo.
echo Stopping any running Python processes...
taskkill /F /IM python.exe 2>nul

echo.
echo Starting backend server...
python app.py
