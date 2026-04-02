; Script generado por el Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Multiservicios Flores S. De R. L."
#define MyAppVersion "1.0"
#define MyAppPublisher "XatruchTech"
#define MyAppURL "https://www.xatruchtech.com/" ; Reemplaza con la URL real si existe
#define MyAppExeName "TallerProAuto.exe" ; Debe coincidir con el nombre generado por PyInstaller
#define MyAppIcon "Logo.ico" ; IMPORTANTE: Debe ser un archivo .ico para el instalador

[Setup]
; NOTA: El valor de AppId identifica de forma única esta aplicación.
; No uses el mismo valor de AppId en instaladores para otras aplicaciones.
; (Para generar un nuevo GUID, haz clic en Herramientas | Generar GUID dentro del IDE de Inno Setup.)
AppId={{631C0B37-5A64-4BA4-B743-C59D54E35748}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={commonpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputBaseFilename=TallerProAuto_Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppIcon}
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:CreateIcons}"; Flags: unchecked
Name: "autostart"; Description: "Iniciar {#MyAppName} automáticamente con Windows"; GroupDescription: "Opciones de inicio:"

[Files]
; Archivos generados por PyInstaller (deben estar en la carpeta 'dist' relativa al .iss)
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TallerProAuto.exe"; DestDir: "{app}"; Flags: ignoreversion

; Otros archivos de la aplicación (deben estar en la carpeta raíz del proyecto)
Source: "index.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "Logo.ico"; DestDir: "{app}"; Flags: ignoreversion
; Si deseas incluir una base de datos SQLite inicial (vacía o preconfigurada), descomenta la siguiente línea:
; Source: "taller.db"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Entrada de autoinicio para la aplicación de bandeja del sistema
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: "{app}\{#MyAppExeName}"; Tasks: autostart; Flags: uninsdeletevalue

[UninstallDelete]
Type: filesandordirs; Name: "{app}\taller.db"