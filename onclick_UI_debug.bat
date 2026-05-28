@echo off
REM MarkItDown GUI - diagnostic launcher.
REM
REM Uses python.exe (console subsystem) instead of pythonw.exe so import
REM errors, traceback, and Qt platform plugin warnings are visible. The
REM console stays open after exit (pause) so the user can read or screenshot
REM the output when reporting a startup problem.

setlocal

set "EMBED_PY=%~dp0python312\python.exe"

if not exist "%EMBED_PY%" (
    echo [ERROR] Portable Python runtime not found at %~dp0python312
    echo This launcher expects the bundled python312\ folder shipped with the integrated package.
    pause
    exit /b 1
)

echo ============================================================
echo  MarkItDown GUI - diagnostic mode
echo  Runtime: %EMBED_PY%
echo ============================================================
echo.

"%EMBED_PY%" -m markitdown_gui
set "RC=%ERRORLEVEL%"

echo.
echo ============================================================
echo  Exit code: %RC%
echo ============================================================
pause

endlocal
