param(
    [switch]$CheckOnly,
    [ValidateRange(2,16)][int]$Factor = 8
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw "Environnement Python absent : $pythonPath" }
$scriptArguments = @('-u', (Join-Path $PSScriptRoot 'continue_fixed_work.py'), '--factor', "$Factor")
if ($CheckOnly) { $scriptArguments += '--check-only' }
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath @scriptArguments
    $resultCode = $LASTEXITCODE
}
finally { Pop-Location }
exit $resultCode
