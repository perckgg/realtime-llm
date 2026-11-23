@echo off
setlocal
chcp 65001 >nul

set "NO_PAUSE=0"
for %%A in (%*) do (
    if /i "%%~A"=="--no-pause" set "NO_PAUSE=1"
    if /i "%%~A"=="-NoPause" set "NO_PAUSE=1"
    if /i "%%~A"=="--help" goto :show_help
    if /i "%%~A"=="-h" goto :show_help
    if /i "%%~A"=="/?" goto :show_help
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Build failed with exit code %EXIT_CODE%.
)

REM Chi pause khi mo bang double-click tu Explorer (cmd /c ""...""), khong pause khi goi tu terminal
if "%NO_PAUSE%"=="0" (
    echo %cmdcmdline% | find /i "/c """ >nul
    if not errorlevel 1 pause
)

exit /b %EXIT_CODE%

:show_help
echo Cach dung: build.bat [--print] [--clean] [--no-pause] [--help]
echo.
echo   (khong co co)  Build ban PDF doc online (link mau xanh navy, tu dong chay du 2-3 pass).
echo   --print        Build ban in giay (toan bo link chuyen sang mau den, khong sua main.tex).
echo   --clean        Xoa file trung gian (.aux, .toc, .lof, .lot, .out, .log) truoc khi build.
echo   --no-pause     Khong dung cho bam phim khi chay xong.
echo   --help         Hien thi huong dan nay.
exit /b 0
