@echo off
setlocal
chcp 65001 >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Build failed with exit code %EXIT_CODE%.
)

REM Chi pause khi mo bang double-click tu Explorer (cmd /c ""...""), khong pause khi goi tu terminal
if /i not "%~1"=="--no-pause" (
    echo %cmdcmdline% | find /i "/c """ >nul
    if not errorlevel 1 pause
)

exit /b %EXIT_CODE%
