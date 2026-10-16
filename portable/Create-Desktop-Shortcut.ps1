$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskExe = Join-Path $taskRoot 'MarkdownFigureTool.exe'
if (-not (Test-Path -LiteralPath $taskExe -PathType Leaf)) {
    throw 'Extract the entire portable ZIP before creating a shortcut.'
}
$taskShell = New-Object -ComObject WScript.Shell
$taskDesktop = [Environment]::GetFolderPath('DesktopDirectory')
$taskShortcut = $taskShell.CreateShortcut((Join-Path $taskDesktop 'Markdown Figure Tool.lnk'))
$taskShortcut.TargetPath = $taskExe
$taskShortcut.WorkingDirectory = $taskRoot
$taskShortcut.IconLocation = $taskExe + ',0'
$taskShortcut.Description = 'Offline Markdown figure renderer'
$taskShortcut.Save()
Write-Output 'Desktop shortcut created.'
