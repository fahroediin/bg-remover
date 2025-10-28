@echo off
REM Background Remover API - Setup Script for Windows
REM This script helps you set up the environment quickly

echo 🚀 Background Remover API - Setup Script
echo ========================================

REM Check if .env file exists
if exist ".env" (
    echo [WARNING] .env file already exists!
    set /p overwrite="Do you want to overwrite it? (y/N): "
    if /i "%overwrite%"=="y" (
        copy .env.sample .env >nul
        echo [SUCCESS] Created new .env from .env.sample
    ) else (
        echo [INFO] Keeping existing .env file
    )
) else (
    copy .env.sample .env >nul
    echo [SUCCESS] Created .env file from .env.sample
)

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo [INFO] Using Python command: python

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed successfully!

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs
if not exist "temp" mkdir temp
echo [SUCCESS] Directories created

REM Test the setup
echo [INFO] Testing setup...
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Environment variables loaded successfully'); print('✅ Rate limiting configuration:', os.getenv('RATE_LIMIT_STORAGE', 'memory')); print('✅ Flask configuration loaded')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Setup test failed
    pause
    exit /b 1
)
echo [SUCCESS] Setup test passed!

echo.
echo 🎉 Setup completed successfully!
echo.
echo Next steps:
echo 1. Review and customize your .env file if needed
echo 2. Start the server: python app.py
echo 3. Open your browser to test: http://localhost:5001
echo 4. Or use the test.html file for easy testing
echo.
echo For production deployment:
echo 1. Copy .env.production to .env
echo 2. Install and configure Redis
echo 3. Update CORS_ORIGINS in .env
echo 4. Set DEBUG=False
echo.
echo Happy coding! 🚀
pause