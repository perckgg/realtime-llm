$ErrorActionPreference = "Stop"
$env:PATH = "C:\Users\knguyen302\AppData\Local\Programs\MiKTeX\miktex\bin\x64;C:\Users\knguyen302\AppData\Roaming\Python\Python314\Scripts;$env:PATH"
Set-Location $PSScriptRoot
Write-Host "=== Pass 1/2: pdflatex ==="
pdflatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error main.tex
Write-Host "=== Pass 2/2: pdflatex ==="
pdflatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error main.tex
if (Test-Path "main.pdf") {
    $size = (Get-Item "main.pdf").Length
    Write-Host "=== Done: main.pdf ($size bytes) ==="
}
