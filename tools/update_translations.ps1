param(
    [switch]$CompileOnly
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$translationsDir = Join-Path $root "astro_viewer\translations"
$enTs = Join-Path $translationsDir "en.ts"
$itTs = Join-Path $translationsDir "it.ts"
$lupdate = Join-Path $root ".venv\Lib\site-packages\PySide6\lupdate.exe"
$lrelease = Join-Path $root ".venv\Lib\site-packages\PySide6\lrelease.exe"

foreach ($tool in @($lupdate, $lrelease)) {
    if (-not (Test-Path -LiteralPath $tool)) {
        throw "Qt translation tool not found: $tool"
    }
}

if (-not $CompileOnly) {
    $qmlFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $root "astro_viewer\app\ui") -Recurse -Filter "*.qml" |
            Sort-Object FullName |
            Select-Object -ExpandProperty FullName
    )
    & $lupdate @qmlFiles -ts $enTs $itTs
    if ($LASTEXITCODE -ne 0) {
        throw "lupdate failed with exit code $LASTEXITCODE"
    }

    [xml]$italianCatalog = Get-Content -LiteralPath $itTs -Raw
    foreach ($message in @($italianCatalog.SelectNodes("//message"))) {
        $sourceNode = $message.SelectSingleNode("source")
        $translationNode = $message.SelectSingleNode("translation")
        if ($null -eq $sourceNode -or $null -eq $translationNode) {
            continue
        }
        $translationNode.InnerText = $sourceNode.InnerText
        if ($translationNode.HasAttribute("type")) {
            $translationNode.RemoveAttribute("type")
        }
    }

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $settings.Indent = $true
    $settings.IndentChars = "  "
    $settings.NewLineChars = "`n"
    $writer = [System.Xml.XmlWriter]::Create($itTs, $settings)
    try {
        $italianCatalog.Save($writer)
    }
    finally {
        $writer.Close()
    }
}

foreach ($catalogPath in @($enTs, $itTs)) {
    [xml]$catalog = Get-Content -LiteralPath $catalogPath -Raw
    $unfinished = @($catalog.SelectNodes('//translation[@type="unfinished"]')).Count
    $empty = @($catalog.SelectNodes('//message[not(translation) or normalize-space(translation)=""]')).Count
    if ($unfinished -ne 0 -or $empty -ne 0) {
        throw "Incomplete catalog $catalogPath (unfinished=$unfinished, empty=$empty)"
    }
}

& $lrelease $enTs -qm (Join-Path $translationsDir "en.qm")
if ($LASTEXITCODE -ne 0) {
    throw "English lrelease failed with exit code $LASTEXITCODE"
}

& $lrelease $itTs -qm (Join-Path $translationsDir "it.qm")
if ($LASTEXITCODE -ne 0) {
    throw "Italian lrelease failed with exit code $LASTEXITCODE"
}

Write-Output "Translation catalogs are complete and compiled."
