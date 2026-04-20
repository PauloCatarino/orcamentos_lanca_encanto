@echo off
setlocal EnableExtensions

rem Build do executavel standalone do Martelo_Orcamentos_V2.
rem Uso:
rem   .\build_exe.bat

cd /d "%~dp0"

set "ROOT=%CD%"
set "PKG=%ROOT%\Martelo_Orcamentos_V2"

set "PYTHON=python"
if exist ".venv_Martelo\Scripts\python.exe" (
    set "PYTHON=.venv_Martelo\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
)

echo ===========================================
echo Usando Python: %PYTHON%
echo ===========================================
echo A executar PyInstaller. Este passo pode demorar varios minutos.

%PYTHON% -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo [ERRO] Falha ao instalar ou atualizar o PyInstaller.
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if not exist build mkdir build

set "ICON_PATH=%ROOT%\martelo.ico"
if not exist "%ICON_PATH%" set "ICON_PATH=%PKG%\martelo.ico"

set "ICON_FLAG="
if exist "%ICON_PATH%" (
    set "ICON_FLAG=--icon=%ICON_PATH%"
    echo Icone: %ICON_PATH%
) else (
    echo [AVISO] Icone martelo.ico nao encontrado. O build segue sem icon.
)

%PYTHON% -m PyInstaller ^
    --noconfirm ^
    --noconsole ^
    --name Martelo_Orcamentos_V2 ^
    --specpath build ^
    %ICON_FLAG% ^
    --hidden-import passlib.handlers.bcrypt ^
    --hidden-import win32com.client ^
    --hidden-import pythoncom ^
    --hidden-import pywintypes ^
    --hidden-import win32clipboard ^
    --hidden-import win32con ^
    --hidden-import win32gui ^
    --hidden-import win32process ^
    --hidden-import pywinauto ^
    --hidden-import pywinauto.application ^
    --hidden-import pywinauto.mouse ^
    --hidden-import pywinauto.controls.uia_controls ^
    --hidden-import pywinauto.controls.win32_controls ^
    --hidden-import comtypes ^
    --hidden-import PySide6.QtPdf ^
    --hidden-import pypdf ^
    --collect-all reportlab ^
    --paths "%PKG%" ^
    --add-data "%ICON_PATH%;." ^
    --add-data "%ICON_PATH%;Martelo_Orcamentos_V2" ^
    --add-data "%PKG%\ui\forms;Martelo_Orcamentos_V2/ui/forms" ^
    --collect-all PySide6 ^
    "%PKG%\run_dev.py"

if errorlevel 1 (
    echo [ERRO] Build do executavel falhou.
    exit /b 1
)

set "DIST_ENV=dist\Martelo_Orcamentos_V2\.env"
if exist ".env" (
    copy /Y ".env" "%DIST_ENV%" >nul
    echo Copiado .env para %DIST_ENV%
) else (
    echo [AVISO] Ficheiro .env nao encontrado na raiz. Nao foi copiado.
)

set "DIST_LOG=dist\Martelo_Orcamentos_V2\martelo_debug.log"
type nul > "%DIST_LOG%"

echo.
echo ============================================================
echo Build concluido.
echo Executavel: %ROOT%\dist\Martelo_Orcamentos_V2\Martelo_Orcamentos_V2.exe
echo Nota: manter a estrutura da pasta dist\Martelo_Orcamentos_V2.
echo ============================================================

endlocal
