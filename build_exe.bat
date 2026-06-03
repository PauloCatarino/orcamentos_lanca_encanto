@echo off
setlocal EnableExtensions

rem Build do executavel standalone do Martelo_Orcamentos_V2.
rem Uso:
rem   .\build_exe.bat
rem   .\build_exe.bat lean

cd /d "%~dp0"

set "ROOT=%CD%"
set "PKG=%ROOT%\Martelo_Orcamentos_V2"
set "BUILD_PROFILE=%~1"
if not defined BUILD_PROFILE set "BUILD_PROFILE=%MARTELO_BUILD_PROFILE%"
if not defined BUILD_PROFILE set "BUILD_PROFILE=full"

if /I not "%BUILD_PROFILE%"=="full" if /I not "%BUILD_PROFILE%"=="lean" (
    echo [ERRO] Perfil de build invalido: %BUILD_PROFILE%
    echo Use: full ^| lean
    exit /b 1
)

set "MARTELO_BUILD_PROFILE=%BUILD_PROFILE%"

set "PYTHON=python"
if exist ".venv_Martelo\Scripts\python.exe" (
    set "PYTHON=.venv_Martelo\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
)

echo ===========================================
echo Usando Python: %PYTHON%
echo Perfil de build: %BUILD_PROFILE%
echo ===========================================
echo A executar PyInstaller. Este passo pode demorar varios minutos.

%PYTHON% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] PyInstaller nao esta instalado neste ambiente.
    echo Instale com: %PYTHON% -m pip install pyinstaller
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if not exist build mkdir build

set "ICON_PATH=%ROOT%\martelo.ico"
if not exist "%ICON_PATH%" set "ICON_PATH=%PKG%\martelo.ico"
set "SPEC_FILE=%ROOT%\Martelo_Orcamentos_V2.spec"

if not exist "%SPEC_FILE%" (
    echo [ERRO] Spec file nao encontrado:
    echo %SPEC_FILE%
    exit /b 1
)

set "ICON_FLAG="
if exist "%ICON_PATH%" (
    echo Icone: %ICON_PATH%
) else (
    echo [AVISO] Icone martelo.ico nao encontrado. O build segue sem icon.
)

%PYTHON% -m PyInstaller ^
    --noconfirm ^
    "%SPEC_FILE%"

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
