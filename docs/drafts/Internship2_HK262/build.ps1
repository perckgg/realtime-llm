$ErrorActionPreference = "Stop"
$miktexBin = Join-Path $env:LOCALAPPDATA "Programs\MiKTeX\miktex\bin\x64"
if ((Test-Path $miktexBin) -and ($env:PATH -notlike "*$miktexBin*")) {
    $env:PATH = "$miktexBin;$env:PATH"
}
Set-Location $PSScriptRoot
if (Test-Path "main.pdf") {
    try {
        $fs = [System.IO.File]::Open((Join-Path $PSScriptRoot "main.pdf"), "Open", "ReadWrite", "None")
        $fs.Close()
    } catch {
        throw "File main.pdf đang bị khóa bởi ứng dụng khác (trình đọc PDF). Hãy đóng main.pdf rồi chạy lại."
    }
}
Write-Host "=== Pass 1/2: pdflatex ==="
pdflatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error main.tex
if ($LASTEXITCODE -ne 0) {
    throw "pdflatex Pass 1 failed with exit code $LASTEXITCODE"
}
Write-Host "=== Pass 2/2: pdflatex ==="
pdflatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error main.tex
if ($LASTEXITCODE -ne 0) {
    throw "pdflatex Pass 2 failed with exit code $LASTEXITCODE"
}
if (Test-Path "main.pdf") {
    $size = (Get-Item "main.pdf").Length
    Write-Host "=== Done: main.pdf ($size bytes) ==="
}
if (Test-Path "main.synctex.gz") {
    $syncSize = (Get-Item "main.synctex.gz").Length
    Write-Host "=== SyncTeX: main.synctex.gz ($syncSize bytes) ==="
} else {
    Write-Warning "main.synctex.gz was not generated."
}
