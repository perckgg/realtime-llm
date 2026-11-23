param(
    [switch]$Print,
    [switch]$Clean,
    [switch]$NoPause,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

# Ho tro ca kieu co GNU (--print, --clean, --no-pause) khi goi qua build.bat %*
foreach ($arg in $ExtraArgs) {
    switch -Regex ($arg) {
        '^(--print|-p)$'    { $Print = $true }
        '^(--clean|-c)$'    { $Clean = $true }
        '^(--no-pause)$'    { $NoPause = $true }
        default             { Write-Warning "Bo qua tham so khong nhan dien: $arg" }
    }
}

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

if ($Clean) {
    Write-Host "=== Clean intermediate files ==="
    $junk = @("main.aux", "main.log", "main.out", "main.toc", "main.lof", "main.lot", "main.fls", "main.fdb_latexmk")
    foreach ($f in $junk) {
        if (Test-Path $f) {
            Remove-Item -Force $f
        }
    }
}

$modeLabel = if ($Print) { "PRINT (black links)" } else { "ONLINE PDF (clickable navy links)" }
Write-Host "=== Mode: $modeLabel ==="

function Invoke-PdfLatexPass {
    param([int]$PassNum, [int]$MaxPasses)
    Write-Host "=== Pass $PassNum/${MaxPasses}: pdflatex ==="
    $argsList = @(
        "-shell-escape",
        "-synctex=1",
        "-interaction=nonstopmode",
        "-file-line-error",
        "-jobname=main"
    )
    if ($Print) {
        $argsList += '\def\PRINTMODE{1}\input{main.tex}'
    } else {
        $argsList += "main.tex"
    }
    & pdflatex @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "pdflatex Pass $PassNum failed with exit code $LASTEXITCODE"
    }
}

# Luon chay toi thieu 2 pass; tu dong chay Pass 3 neu tham chieu/muc luc/hyperlink chua hoi tu.
$maxPasses = 3
Invoke-PdfLatexPass -PassNum 1 -MaxPasses $maxPasses
Invoke-PdfLatexPass -PassNum 2 -MaxPasses $maxPasses

$needsPass3 = $false
if (Test-Path "main.log") {
    $logText = Get-Content "main.log" -Raw -ErrorAction SilentlyContinue
    if ($logText -match "Rerun to get cross-references right|Label\(s\) may have changed|Rerun to get outlines right|Rerun to get the bars right") {
        $needsPass3 = $true
    }
}

if ($needsPass3) {
    Invoke-PdfLatexPass -PassNum 3 -MaxPasses $maxPasses
} else {
    Write-Host "=== Cross-references converged after Pass 2 (skip Pass 3) ==="
}

# Hau kiem main.log: canh bao link chet, tham chieu thieu, PDF string warnings
if (Test-Path "main.log") {
    $finalLog = Get-Content "main.log" -Raw -ErrorAction SilentlyContinue
    $undefRefs  = ([regex]::Matches($finalLog, "Reference `[^']+` on page .* undefined|Citation `[^']+` on page .* undefined")).Count
    $deadLinks  = ([regex]::Matches($finalLog, "has been referenced but does not exist")).Count
    $pdfStrings = ([regex]::Matches($finalLog, "Token not allowed in a PDF string")).Count
    $dupDests   = ([regex]::Matches($finalLog, "destination with the same identifier")).Count
    $stillRerun = $finalLog -match "Rerun to get cross-references right|Label\(s\) may have changed"
    $pagesMatch = [regex]::Match($finalLog, "Output written on main\.pdf \((\d+) pages")
    $pagesInfo  = if ($pagesMatch.Success) { "$($pagesMatch.Groups[1].Value) pages" } else { "unknown pages" }

    Write-Host "=== Log Audit ($pagesInfo) ==="
    Write-Host ("  Undefined refs/cites : {0}" -f $undefRefs)
    Write-Host ("  Dead hyperlinks      : {0}" -f $deadLinks)
    Write-Host ("  PDF string warnings  : {0}" -f $pdfStrings)
    Write-Host ("  Duplicate dests      : {0}" -f $dupDests)
    if ($stillRerun) {
        Write-Warning "main.log van con goi y Rerun — hay chay build.bat them 1 lan."
    }
    if ($deadLinks -gt 0 -or $undefRefs -gt 0 -or $pdfStrings -gt 0) {
        Write-Warning "Phat hien canh bao tham chieu/hyperlink trong main.log — vui long kiem tra."
    }
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
