@echo off
title Running Streamlit App (CyberSentinel: AutoSOC)
echo Starting CyberSentinel: AutoSOC...

:: Navigate to script directory
cd /d "%~dp0"

:: Activate virtual environment if present
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Detect Python executable
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python -m streamlit run app.py %*
    goto :end
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -m streamlit run app.py %*
    goto :end
)

echo.
echo [ERROR] Python is not found on your PATH.
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.

:end
if %ERRORLEVEL% neq 0 (
    echo.
    echo App exited with error code %ERRORLEVEL%.
)

pause
