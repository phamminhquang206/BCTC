param([Parameter(ValueFromRemainingArguments=$true)][string[]]$AppArguments)
$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$runtimeDir = Join-Path $appRoot '.runtime'
$runtimePython = Join-Path $runtimeDir 'python.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

try {
    # Optional developer override; ordinary double-click uses an isolated portable runtime.
    if ($env:FINHAY_PYTHON) {
        $runtimePython = $env:FINHAY_PYTHON
    } elseif (-not (Test-Path -LiteralPath $runtimePython)) {
        Write-Host 'Lan dau: dang tai Python 3.12.10 chinh thuc (khong cai toan he thong)...'
        New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
        $archivePath = Join-Path $runtimeDir 'python.zip'
        Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $archivePath
        Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeDir -Force
        Remove-Item -LiteralPath $archivePath
        $pthPath = Join-Path $runtimeDir 'python312._pth'
        (Get-Content -LiteralPath $pthPath) -replace '#import site', 'import site' | Set-Content -LiteralPath $pthPath -Encoding ASCII
    }
    & $runtimePython -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('pip') else 1)"
    if ($LASTEXITCODE -ne 0) {
        $pipPath = Join-Path $runtimeDir 'get-pip.py'
        Invoke-WebRequest -UseBasicParsing -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $pipPath
        & $runtimePython $pipPath --disable-pip-version-check
        if ($LASTEXITCODE -ne 0) { throw 'Khong cai duoc pip.' }
    }
    $requirements = Join-Path $appRoot 'requirements.txt'
    $stamp = Join-Path $runtimeDir 'requirements.sha256'
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = [System.BitConverter]::ToString($hasher.ComputeHash([System.IO.File]::ReadAllBytes($requirements))).Replace('-', '')
    } finally { $hasher.Dispose() }
    $installed = if (Test-Path -LiteralPath $stamp) { (Get-Content -LiteralPath $stamp -Raw).Trim() } else { '' }
    & $runtimePython -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ('mcp','PySide6','keyring','openpyxl')) else 1)"
    $importsReady = $LASTEXITCODE -eq 0
    if ($installed -ne $hash -or -not $importsReady) {
        Write-Host 'Dang chuan bi thu vien GUI va Finhay MCP. Lan dau can Internet...'
        & $runtimePython -m pip install --disable-pip-version-check -r $requirements
        if ($LASTEXITCODE -ne 0) { throw 'Khong cai duoc thu vien. Kiem tra Internet.' }
        New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
        Set-Content -LiteralPath $stamp -Value $hash -Encoding ASCII
    }
    Write-Host 'Dang mo Finhay Desktop...'
    & $runtimePython (Join-Path $appRoot 'main.py') @AppArguments
    exit $LASTEXITCODE
} catch {
    Write-Host ('Loi: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
