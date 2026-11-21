param([switch]$CheckOnly, [switch]$Quality)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Python du projet absent : .venv\Scripts\python.exe' }
$mutex = New-Object System.Threading.Mutex($false, 'Local\Skate4DLocalGpu')
$acquired = $false
$runExit = 1
try {
    $acquired = $mutex.WaitOne(0)
    if (-not $acquired) { throw 'Un lancement est deja actif dans un autre terminal.' }
    Write-Host 'DyNeRF sur votre RTX 4050 - installation, entrainement court et rendu' -ForegroundColor Cyan
    $launcher = Join-Path $PSScriptRoot 'local_gpu_terminal.py'
    $launcherArgs = @()
    if ($CheckOnly) { $launcherArgs += '--check-only' }
    if ($Quality) { $launcherArgs += '--quality' }
    & $python -u $launcher @launcherArgs
    $runExit = $LASTEXITCODE
}
finally {
    if ($acquired) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
exit $runExit
