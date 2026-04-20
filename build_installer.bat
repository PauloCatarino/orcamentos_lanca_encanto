@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PYTHON=python"
if exist ".venv_Martelo\Scripts\python.exe" (
  set "PYTHON=.venv_Martelo\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
)

for /f "delims=" %%I in ('%PYTHON% -c "from Martelo_Orcamentos_V2.release_tools import read_static_app_version; print(read_static_app_version())"') do set "APP_VERSION=%%I"

if not defined APP_VERSION (
  echo [ERRO] Nao foi possivel ler a versao atual em Martelo_Orcamentos_V2\version.py.
  exit /b 1
)

echo.
echo ==========================================
echo 0) Versao atual
echo ==========================================
echo %APP_VERSION%
echo Nota: este script recompila a versao atual.
echo Para criar a proxima versao e copiar para o servidor, use: .\release.bat patch

echo.
echo ==========================================
echo 1) Build PyInstaller (dist\Martelo_Orcamentos_V2)
echo ==========================================
echo A executar PyInstaller. Este passo pode demorar varios minutos.
call build_exe.bat
if errorlevel 1 (
  echo [ERRO] build_exe.bat falhou.
  exit /b 1
)

echo.
echo ==========================================
echo 2) Password do instalador
echo ==========================================

set "SETUP_PW=%~1"
if not defined SETUP_PW set "SETUP_PW=%MARTELO_SETUP_PASSWORD%"
if not defined SETUP_PW set "SETUP_PW=Martelo_V2"

echo.
echo ==========================================
echo 3) Compilar Inno Setup (ISCC)
echo ==========================================
echo A compilar o instalador. Este passo pode demorar alguns minutos.

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
  echo [ERRO] Nao encontrei o ISCC.exe.
  echo Instala o Inno Setup ou verifica o caminho.
  exit /b 1
)

set "ISS_FILE=%CD%\installer\Martelo_Orcamentos_V2.iss"
if not exist "%ISS_FILE%" (
  echo [ERRO] Nao encontrei o .iss em:
  echo %ISS_FILE%
  exit /b 1
)

set "OUTPUT_DIR=%CD%\installer\Output"
set "OUTPUT_FILE=%OUTPUT_DIR%\Setup_Martelo Orcamentos V2_%APP_VERSION%.exe"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo Saida esperada:
echo %OUTPUT_FILE%
if exist "%OUTPUT_FILE%" (
  echo [AVISO] Ja existe um setup com esta mesma versao; o ficheiro sera substituido se nao estiver bloqueado.
)

"%ISCC%" "%ISS_FILE%" "/DSetupPassword=%SETUP_PW%" "/DAppVersion=%APP_VERSION%"
if errorlevel 1 (
  echo [ERRO] Compilacao do Inno falhou.
  echo Verifique se o ficheiro de destino nao esta aberto ou bloqueado:
  echo %OUTPUT_FILE%
  exit /b 1
)

if not exist "%OUTPUT_FILE%" (
  echo [ERRO] O Inno terminou sem erro, mas o setup esperado nao foi encontrado em:
  echo %OUTPUT_FILE%
  exit /b 1
)

echo.
echo ==========================================
echo OK! Instalador criado:
echo %OUTPUT_FILE%
echo ==========================================
endlocal
