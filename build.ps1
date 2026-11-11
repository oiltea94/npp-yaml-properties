param([switch]$CoreOnly)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $compiler = Join-Path $PSScriptRoot '.tools\llvm-mingw-20261104-ucrt-x86_64\bin\x86_64-w64-mingw32-clang++.exe'
    if (-not (Test-Path -LiteralPath $compiler)) {
        throw 'Build toolchain missing. Run python bootstrap.py first (downloads the pinned portable compiler).'
    }
    $arguments = @('build.py', '--compiler', $compiler)
    if ($CoreOnly) { $arguments += '--core-only' }
    & python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Build or tests failed with exit code $LASTEXITCODE" }
} finally { Pop-Location }
