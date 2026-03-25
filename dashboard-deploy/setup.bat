@echo off
REM Quick Start Setup Script for Chakravyuh Dashboard (Windows)
REM This script automates the initial setup process

echo.
echo 🚀 Chakravyuh Dashboard - Quick Setup
echo ======================================
echo.

REM Check Node.js installation
echo ✓ Checking Node.js installation...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ✗ Node.js not found. Please install Node.js v18+ from https://nodejs.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
for /f "tokens=*" %%i in ('npm -v') do set NPM_VERSION=%%i

echo   Node.js %NODE_VERSION%
echo   npm %NPM_VERSION%
echo.

REM Install dependencies
echo ✓ Installing dependencies (this may take a few minutes)...
call npm install --legacy-peer-deps
if %errorlevel% neq 0 (
    echo ✗ Failed to install dependencies
    pause
    exit /b 1
)
echo.

REM Create .env file if it doesn't exist
echo ✓ Setting up environment...
if not exist .env (
    copy .env.example .env
    echo   Created .env file from .env.example
    echo   ⚠️  Update .env with your API URL if needed
) else (
    echo   .env file already exists
)
echo.

REM Build the project
echo ✓ Building the dashboard...
call npm run build
if %errorlevel% neq 0 (
    echo ✗ Build failed
    pause
    exit /b 1
)
echo.

echo ✅ Setup complete!
echo.
echo 📝 Next steps:
echo    1. Update .env with your API endpoint (if not localhost:8000)
echo    2. Start development server: npm run dev
echo    3. Open http://localhost:5173 in your browser
echo.
echo 📚 For more details, read README.md
echo.

pause
