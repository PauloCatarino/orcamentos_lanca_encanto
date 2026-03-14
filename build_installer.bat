@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo.
echo ==========================================
echo 1) Build PyInstaller (dist\Martelo_Orcamentos_V2)
echo ==========================================
call build_exe.bat
if errorlevel 1 (
  echo [ERRO] build_exe.bat falhou.
  pause
  exit /b 1
)

echo.
echo ==========================================
echo 2) Password do instalador
echo ==========================================

set "SETUP_PW=%~1"
if not "%SETUP_PW%"=="" goto GOT_PW

:ASK_PW
set /p SETUP_PW=Introduz a password do instalador: 
if "%SETUP_PW%"=="" goto ASK_PW

:GOT_PW

echo.
echo ==========================================
echo 3) Compilar Inno Setup (ISCC)
echo ==========================================

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
  echo [ERRO] Nao encontrei o ISCC.exe.
  echo Instala o Inno Setup ou verifica o caminho.
  pause
  exit /b 1
)

set "ISS_FILE=%CD%\installer\Martelo_Orcamentos_V2.iss"
if not exist "%ISS_FILE%" (
  echo [ERRO] Nao encontrei o .iss em:
  echo %ISS_FILE%
  pause
  exit /b 1
)

"%ISCC%" "%ISS_FILE%" "/DSetupPassword=%SETUP_PW%"
if errorlevel 1 (
  echo [ERRO] Compilacao do Inno falhou.
  pause
  exit /b 1
)

echo.
echo ==========================================
echo OK! Instalador criado em:
echo %CD%\installer\Output
echo ==========================================
pause
endlocal
