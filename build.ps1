# ============================================
#  一键构建 - 产出免依赖单文件 dist\FTPServer.exe（仅需 Windows x64）
#  说明: 仅构建机需要 Python；最终用户无需任何依赖
# ============================================
$ErrorActionPreference = 'Stop'

# --- 1. 检查 Python（优先 python，找不到则回退 py 启动器） ---
$PyCmd = $null; $PyPre = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PyCmd = 'python'
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PyCmd = 'py'; $PyPre = @('-3')
} else {
    Write-Host '[错误] 未找到 Python，请先安装 Python（仅构建需要，最终用户不需要）' -ForegroundColor Red
    exit 1
}
if (-not [Environment]::Is64BitProcess) {
    Write-Host '[警告] 当前 Python 为 32 位，产物将不是 x64 版本' -ForegroundColor Yellow
}

# --- 2. 检查并安装构建依赖（pyftpdlib + pyinstaller） ---
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $PyCmd @PyPre -c "import pyftpdlib" 2>$null
$hasServer = ($LASTEXITCODE -eq 0)
& $PyCmd @PyPre -c "import PyInstaller" 2>$null
$hasPyi = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
if (-not $hasServer -or -not $hasPyi) {
    Write-Host '正在安装构建依赖 (pyftpdlib / pyinstaller)...' -ForegroundColor Yellow
    & $PyCmd @PyPre -m pip install --quiet --disable-pip-version-check pyftpdlib pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[错误] 依赖安装失败，请检查网络后重试' -ForegroundColor Red
        exit 1
    }
}

# --- 3. PyInstaller 打包为单文件 exe ---
$root = $PSScriptRoot
$pyArgs = @(
    '-m', 'PyInstaller', '--onefile', '--clean', '-y',
    '--name', 'FTPServer',
    '--distpath', (Join-Path $root 'dist'),
    '--workpath', (Join-Path $root 'build_tmp'),
    '--specpath', (Join-Path $root 'build_tmp'),
    (Join-Path $root 'server.py')
)
& $PyCmd @PyPre @pyArgs
$exe = Join-Path $root 'dist\FTPServer.exe'
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) {
    Write-Host '[错误] 构建失败，请查看上方 PyInstaller 输出' -ForegroundColor Red
    exit 1
}
Remove-Item (Join-Path $root 'build_tmp') -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ''
Write-Host '构建完成: dist\FTPServer.exe' -ForegroundColor Green
Write-Host '单文件免依赖，双击运行；成功启动一次后会在同目录生成 start.bat'
