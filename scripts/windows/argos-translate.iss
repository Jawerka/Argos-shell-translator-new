; Argos Translate Windows installer (Inno Setup 6).
; Stage: dist/ArgosTranslate (Flutter Release + sidecar/ + argos_models/)

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\..\dist\ArgosTranslate"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist"
#endif

#define MyAppName "Argos Translate"
#define MyAppExeName "translator.exe"
#define MyAppPublisher "Argos Translate"
#define MyAppUrl "https://github.com/Jawerka/Argos-shell-translator-new"

[Setup]
AppId={{C3E8A14F-7B92-4D6A-8F1E-5A0C9B7D2E44}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppUrl}
AppSupportURL={#MyAppUrl}
AppUpdatesURL={#MyAppUrl}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=argos-translate-{#MyAppVersion}-windows-x64-setup
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=force

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#ReleaseDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
