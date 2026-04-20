@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PYTHON=python"
if exist ".venv_Martelo\Scripts\python.exe" (
    set "PYTHON=.venv_Martelo\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
)

set "OUTPUT_DIR=%~dp0installer\Output"
set "LOG_FILE=%~dp0installer\release_last.log"

"%PYTHON%" -u scripts\release.py %*
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="0" (
    start "" explorer.exe "%OUTPUT_DIR%"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; $nl=[Environment]::NewLine; [System.Windows.Forms.MessageBox]::Show(('Release concluida com sucesso.' + $nl + $nl + 'Consulte a pasta installer\\Output e o ficheiro installer\\release_last.log.'),'Martelo Release')"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; $nl=[Environment]::NewLine; [System.Windows.Forms.MessageBox]::Show(('Release falhou.' + $nl + $nl + 'Consulte o ficheiro installer\\release_last.log para ver o erro.'),'Martelo Release')"
    start "" notepad.exe "%LOG_FILE%"
)

exit /b %EXITCODE%
