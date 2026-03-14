@echo off
REM Build script para gerar executável standalone do Martelo_Orcamentos_V2
REM Passos:
REM 1) Opcional: ativar venv (.venv\Scripts\activate). Caso contrário usa python global.
REM 2) Instala PyInstaller (se não existir) e executa o build.


rem .\.venv_Martelo\Scripts\Activate.ps1   
rem .\build_exe.bat    -> para executar este script

setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PKG=%ROOT%\\Martelo_Orcamentos_V2"

REM Detecta python do venv se existir
set PYTHON=python
if exist ".venv_Martelo\Scripts\python.exe" (
    set PYTHON=.venv_Martelo\Scripts\python.exe
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
)

echo ===========================================
echo Usando Python: %PYTHON%
echo ===========================================

REM Garante PyInstaller instalado/atualizado
%PYTHON% -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo Falha ao instalar pyinstaller
    exit /b 1
)

REM Limpa builds anteriores
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if not exist build mkdir build

REM Executa PyInstaller
set "ICON_PATH=%ROOT%\\martelo.ico"
if not exist "%ICON_PATH%" set "ICON_PATH=%PKG%\\martelo.ico"
set ICON_FLAG=
if exist "%ICON_PATH%" (
    set ICON_FLAG=--icon "%ICON_PATH%"
) else (
    echo [AVISO] Icone martelo.ico nao encontrado; prosseguir sem icon.
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
    --add-data "%PKG%\\ui\\forms;Martelo_Orcamentos_V2/ui/forms" ^
    --collect-all PySide6 ^
    "%PKG%\\run_dev.py"

if errorlevel 1 (
    echo Build falhou.
    exit /b 1
)

REM Copia .env para a pasta do exe para garantir configuracao de BD/email
set DIST_ENV=dist\Martelo_Orcamentos_V2\.env
if exist ".env" (
    copy /Y ".env" "%DIST_ENV%" >nul
    echo Copiado .env para %DIST_ENV%
) else (
    echo [AVISO] Ficheiro .env nao encontrado na raiz; nao foi copiado.
)

REM Cria ficheiro de log (o programa tambem o vai criar/truncar no arranque)
set DIST_LOG=dist\Martelo_Orcamentos_V2\martelo_debug.log
type nul > "%DIST_LOG%"

echo.
echo ============================================================
echo Build concluido.
echo Copie a pasta dist\Martelo_Orcamentos_V2 para outro PC e
echo execute Martelo_Orcamentos_V2.exe (manter estrutura de pastas).
echo Se faltar runtime do VC++ instale o redistribuivel x64.
echo ============================================================

endlocal
