@echo off
REM Build script para gerar executável standalone do Martelo_Orcamentos_V2
REM Passos:
REM 1) Opcional: ativar venv (.venv\Scripts\activate). Caso contrário usa python global.
REM 2) Instala PyInstaller (se não existir) e executa o build.


rem .\.venv_Martelo\Scripts\Activate.ps1   
rem .\build_exe.bat    -> para executar este script

setlocal

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
if exist Martelo_Orcamentos_V2.spec del /q Martelo_Orcamentos_V2.spec

REM Executa PyInstaller
set ICON_PATH=martelo.ico
if not exist "%ICON_PATH%" (
    set ICON_PATH=Martelo_Orcamentos_V2\martelo.ico
)
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
    %ICON_FLAG% ^
    --hidden-import passlib.handlers.bcrypt ^
    --paths Martelo_Orcamentos_V2 ^
    --add-data "Martelo_Orcamentos_V2\\ui\\forms;Martelo_Orcamentos_V2/ui/forms" ^
    --collect-all PySide6 ^
    Martelo_Orcamentos_V2\run_dev.py

if errorlevel 1 (
    echo Build falhou.
    exit /b 1
)

echo.
echo ============================================================
echo Build concluido.
echo Copie a pasta dist\Martelo_Orcamentos_V2 para outro PC e
echo execute Martelo_Orcamentos_V2.exe (manter estrutura de pastas).
echo Se faltar runtime do VC++ instale o redistribuivel x64.
echo ============================================================

endlocal
