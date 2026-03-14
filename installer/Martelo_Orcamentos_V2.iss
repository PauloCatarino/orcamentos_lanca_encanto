; Inno Setup Script - Martelo Orcamentos V2
; Requisitos:
; 1) Gerar o build PyInstaller primeiro: build_exe.bat  -> dist\Martelo_Orcamentos_V2\
; 2) Compilar este .iss no Inno Setup Compiler (ISCC.exe)
;
; Exemplo de compilacao (com password):
;   ISCC.exe Martelo_Orcamentos_V2.iss /DSetupPassword=Martelo_V2
;
; Exemplo de compilacao (password + versao):
;   ISCC.exe Martelo_Orcamentos_V2.iss /DSetupPassword=Martelo_V2 /DAppVersion=2.0.1

#define AppName "Martelo Orcamentos V2"
#define AppExeName "Martelo_Orcamentos_V2.exe"

#ifndef AppVersion
  #define AppVersion "2.2.1"
#endif

; =========================================================@
; PASSWORD DO INSTALADOR (não fica escrita no .iss)
; Opções para definir a password:
; A) (Recomendado) Compilar via build_installer.bat (pede password)
; B) ISCC.exe ... /DSetupPassword=MINHA_PASSWORD
; C) Definir a variável de ambiente MARTELO_SETUP_PASSWORD e compilar no IDE
; =========================================================
#ifndef SetupPassword
  #define SetupPassword GetEnv('MARTELO_SETUP_PASSWORD')
#endif

#if SetupPassword == ""
  #error SetupPassword nao definido. Use build_installer.bat ou compile com /DSetupPassword=... (ou defina MARTELO_SETUP_PASSWORD).
#endif

[Setup]
AppId={{D94AEF7B-11A0-48A5-9A65-0F8E5C4AC0B9}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Lanca Encanto
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=

DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

OutputDir=Output
OutputBaseFilename=Setup_{#AppName}_{#AppVersion}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

SetupIconFile=..\martelo.ico
UninstallDisplayIcon={app}\{#AppExeName}

; Apenas 64-bit (preferido: x64compatible = x64 + ARM64)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
InfoBeforeFile=info_before.txt

; Password + encriptacao (pede password no início e encripta ficheiros embebidos)
Password={#SetupPassword}
Encryption=yes

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho no Ambiente de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
; Binarios e dependencias do PyInstaller
Source: "..\dist\Martelo_Orcamentos_V2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "martelo_debug.log;.env"

; .env - instalar apenas na primeira vez (para nao sobrescrever ajustes locais)
#if FileExists("..\dist\Martelo_Orcamentos_V2\.env")
Source: "..\dist\Martelo_Orcamentos_V2\.env"; DestDir: "{app}"; Flags: onlyifdoesntexist
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"
