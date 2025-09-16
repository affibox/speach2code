@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "ENV_NAME=whisper-fast"
set "APP_ARGS="

rem Attempt to locate conda.bat automatically
set "CONDA_BAT="
for /f "delims=" %%i in ('where conda.bat 2^>nul') do (
    set "CONDA_BAT=%%i"
    goto :conda_found
)

:conda_found
if not defined CONDA_BAT (
    rem Fallback path; update this if your conda installation lives elsewhere
    set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
)

if not exist "%CONDA_BAT%" (
    echo [ERROR] Unable to find conda.bat.
    echo Update the CONDA_BAT variable near the top of this script to match your installation.
    goto :fail
)

echo Launching Speech to Code helper from %SCRIPT_DIR%
pushd "%SCRIPT_DIR%" >nul

call "%CONDA_BAT%" run -n "%ENV_NAME%" python "%SCRIPT_DIR%main.py" %APP_ARGS%
set "APP_EXIT=%ERRORLEVEL%"

popd >nul

if not "%APP_EXIT%"=="0" (
    echo.
    echo The application exited with an error (code %APP_EXIT%).
    goto :fail
)

goto :end

:fail
echo.
echo Press any key to close this window.
pause >nul
exit /b 1

:end
exit /b 0

