param(
    [string]$NotepadDir = (Join-Path $env:ProgramFiles 'Notepad++'),
    [switch]$Restore
)
$ErrorActionPreference = 'Stop'
$NotepadDir = [IO.Path]::GetFullPath($NotepadDir)
$exe = Join-Path $NotepadDir 'notepad++.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Notepad++ not found: $exe" }
function Get-Machine([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    try {
        $reader = New-Object IO.BinaryReader($stream)
        if ($stream.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5a4d) { throw "Invalid PE file: $Path" }
        $stream.Position = 0x3c
        $peOffset = $reader.ReadUInt32()
        if ([long]$peOffset + 6 -gt $stream.Length) { throw "Invalid PE offset: $Path" }
        $stream.Position = $peOffset
        if ($reader.ReadUInt32() -ne 0x4550) { throw "Invalid PE signature: $Path" }
        return [int]$reader.ReadUInt16()
    } finally { $stream.Dispose() }
}
$architectures = @{ 0x014c = 'x86'; 0x8664 = 'x64'; 0xaa64 = 'arm64' }
$hostMachine = Get-Machine $exe
if (-not $architectures.ContainsKey($hostMachine)) { throw 'Unsupported Notepad++ architecture.' }
$architecture = $architectures[$hostMachine]
$pluginDir = Join-Path $NotepadDir 'plugins\YamlProperties'
$target = Join-Path $pluginDir 'YamlProperties.dll'
$journal = Join-Path $PSScriptRoot '.install-state.json'
$backupRoot = Join-Path $PSScriptRoot '.backups'
function Write-Journal($State) {
    $State | ConvertTo-Json | Set-Content -LiteralPath ($journal + '.tmp') -Encoding UTF8
    Move-Item -LiteralPath ($journal + '.tmp') -Destination $journal -Force
}
if ($Restore) {
    if (-not (Test-Path -LiteralPath $journal)) { throw 'No installation record exists beside this script.' }
    $state = Get-Content -Raw -LiteralPath $journal | ConvertFrom-Json
    if ($state.Target -ne $target) { throw 'The recorded installation is in another directory; pass its -NotepadDir.' }
    if (Test-Path -LiteralPath $target) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $state.InstalledHash) {
            throw 'The DLL changed after installation; preserve it before restoring.'
        }
    }
    if ($state.HadPrevious) {
        $backup = [IO.Path]::GetFullPath($state.Backup)
        if (-not $backup.StartsWith([IO.Path]::GetFullPath($backupRoot) + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Backup path is outside this package backup directory.'
        }
        if ((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash -ne $state.PreviousHash) { throw 'Backup checksum mismatch.' }
        Copy-Item -LiteralPath $backup -Destination ($target + '.restore') -Force
        Move-Item -LiteralPath ($target + '.restore') -Destination $target -Force
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $state.PreviousHash) { throw 'Restore verification failed.' }
        Write-Output "Restored previous DLL: $target"
    } else {
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
        if ((Get-ChildItem -LiteralPath $pluginDir -Force | Measure-Object).Count -eq 0) { Remove-Item -LiteralPath $pluginDir }
        Write-Output "Removed installed DLL: $target"
    }
    Remove-Item -LiteralPath $journal
    exit 0
}
$source = Join-Path $PSScriptRoot 'YamlProperties\YamlProperties.dll'
if (-not (Test-Path -LiteralPath $source)) {
    $relative = if ($architecture -eq 'x64') { 'dist\YamlProperties\YamlProperties.dll' } else { "dist\$architecture\YamlProperties\YamlProperties.dll" }
    $source = Join-Path $PSScriptRoot $relative
}
if (-not (Test-Path -LiteralPath $source)) { throw 'Build the plugin first, or extract the complete release ZIP.' }
if ((Get-Machine $source) -ne $hostMachine) { throw "Plugin architecture does not match $architecture Notepad++. Use the matching release package." }
$newHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if (Test-Path -LiteralPath $journal) {
    $state = Get-Content -Raw -LiteralPath $journal | ConvertFrom-Json
    if ($state.Target -ne $target) { throw 'This package already has an installation record for another directory.' }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $state.InstalledHash) { throw 'Installed DLL changed outside this installer.' }
} else {
    $state = [pscustomobject]@{Target=$target; HadPrevious=(Test-Path -LiteralPath $target); Backup=''; PreviousHash=''; InstalledHash=''}
    if ($state.HadPrevious) {
        $backupDir = Join-Path $backupRoot ([DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff'))
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        $state.Backup = Join-Path $backupDir 'YamlProperties.dll'
        $state.PreviousHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        Copy-Item -LiteralPath $target -Destination $state.Backup
        if ((Get-FileHash -LiteralPath $state.Backup -Algorithm SHA256).Hash -ne $state.PreviousHash) { throw 'Backup verification failed.' }
    }
}
New-Item -ItemType Directory -Path $pluginDir -Force | Out-Null
Copy-Item -LiteralPath $source -Destination ($target + '.new') -Force
Move-Item -LiteralPath ($target + '.new') -Destination $target -Force
if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $newHash) { throw 'Installed DLL verification failed.' }
$state.InstalledHash = $newHash
Write-Journal $state
Write-Output "Installed: $target"
Write-Output "SHA256: $newHash"
if ($state.HadPrevious) { Write-Output "Previous DLL backup: $($state.Backup)" }
Write-Output 'Restart Notepad++ to load the plugin. Use this same script with -Restore to undo.'
