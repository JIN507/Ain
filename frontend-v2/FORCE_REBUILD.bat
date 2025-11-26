@echo off
echo ========================================
echo FORCING COMPLETE REBUILD
echo ========================================
echo.

echo Step 1: Stopping any running servers...
taskkill /F /IM node.exe 2>nul

echo.
echo Step 2: Clearing Vite cache...
if exist .vite rmdir /s /q .vite
if exist dist rmdir /s /q dist
if exist node_modules\.vite rmdir /s /q node_modules\.vite

echo.
echo Step 3: Starting fresh dev server...
echo.
npm run dev
