# Purpose: Extract, update, and compile every configured Qt translation catalogue.
# Contract: Rewrites TS/QM outputs unless narrowed by CompileOnly or UpdateOnly.

param(
    [switch]$CompileOnly,
    [switch]$UpdateOnly
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$translationsDir = Join-Path $root "astro_viewer\translations"
$lupdate = Join-Path $root ".venv\Lib\site-packages\PySide6\lupdate.exe"
$lrelease = Join-Path $root ".venv\Lib\site-packages\PySide6\lrelease.exe"
$python = Join-Path $root ".venv\Scripts\python.exe"

foreach ($tool in @($lupdate, $lrelease, $python)) {
    if (-not (Test-Path -LiteralPath $tool)) {
        throw "Qt translation tool not found: $tool"
    }
}

$packs = @(
    Get-ChildItem -LiteralPath $translationsDir -Filter "*.json" |
        Sort-Object Name |
        ForEach-Object {
            $payload = [IO.File]::ReadAllText(
                $_.FullName,
                [Text.Encoding]::UTF8
            ) | ConvertFrom-Json
            if ($payload.schema_version -ne 1 -or -not $payload.language.code -or -not $payload.language.locale) {
                throw "Invalid language pack metadata: $($_.FullName)"
            }
            if ($payload.language.code -ne $_.BaseName) {
                throw "Language code and filename differ: $($_.FullName)"
            }
            [pscustomobject]@{
                Code = [string]$payload.language.code
                Locale = [string]$payload.language.locale
                Source = [bool]$payload.language.source
                TsPath = Join-Path $translationsDir ($_.BaseName + ".ts")
                QmPath = Join-Path $translationsDir ($_.BaseName + ".qm")
            }
        }
)

$sourcePacks = @($packs | Where-Object Source)
if ($sourcePacks.Count -ne 1) {
    throw "Exactly one source language pack is required."
}
$sourcePack = $sourcePacks[0]

if ($CompileOnly -and $UpdateOnly) {
    throw "CompileOnly and UpdateOnly cannot be used together."
}

if (-not $CompileOnly) {
    $sourceFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $root "astro_viewer\app\ui") -Recurse -Filter "*.qml" |
            Sort-Object FullName |
            Select-Object -ExpandProperty FullName
    )
    $pythonTranslationSource = Join-Path ([IO.Path]::GetTempPath()) "nightscope_python_translations.cpp"
    & $python (Join-Path $root "tools\extract_python_translations.py") $pythonTranslationSource
    if ($LASTEXITCODE -ne 0) {
        throw "Python translation extraction failed with exit code $LASTEXITCODE"
    }
    $sourceFiles += $pythonTranslationSource
    $catalogPaths = @($packs | ForEach-Object TsPath)
    try {
        & $lupdate -no-obsolete @sourceFiles -ts @catalogPaths
        if ($LASTEXITCODE -ne 0) {
            throw "lupdate failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Remove-Item -LiteralPath $pythonTranslationSource -ErrorAction SilentlyContinue
    }

    foreach ($pack in $packs) {
        [xml]$catalog = [IO.File]::ReadAllText(
            $pack.TsPath,
            [Text.Encoding]::UTF8
        )
        $catalog.DocumentElement.SetAttribute("language", $pack.Locale)
        $catalog.DocumentElement.SetAttribute("sourcelanguage", $sourcePack.Locale)
        if ($pack.Source) {
            foreach ($message in @($catalog.SelectNodes("//message"))) {
                $sourceNode = $message.SelectSingleNode("source")
                $translationNode = $message.SelectSingleNode("translation")
                if ($null -eq $sourceNode -or $null -eq $translationNode) {
                    continue
                }
                if ($translationNode.GetAttribute("type") -in @("obsolete", "vanished")) {
                    continue
                }
                $translationNode.InnerText = $sourceNode.InnerText
                if ($translationNode.HasAttribute("type")) {
                    $translationNode.RemoveAttribute("type")
                }
            }
        }

        $settings = New-Object System.Xml.XmlWriterSettings
        $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
        $settings.Indent = $true
        $settings.IndentChars = "  "
        $settings.NewLineChars = "`n"
        $writer = [System.Xml.XmlWriter]::Create($pack.TsPath, $settings)
        try {
            $catalog.Save($writer)
        }
        finally {
            $writer.Close()
        }
    }
}

if ($UpdateOnly) {
    Write-Output "$($packs.Count) language catalogs were updated."
    return
}

foreach ($pack in $packs) {
    [xml]$catalog = [IO.File]::ReadAllText(
        $pack.TsPath,
        [Text.Encoding]::UTF8
    )
    foreach ($message in @($catalog.SelectNodes("//message"))) {
        $sourceNode = $message.SelectSingleNode("source")
        $translationNode = $message.SelectSingleNode("translation")
        if ($null -eq $sourceNode -or $null -eq $translationNode) {
            continue
        }
        if ($translationNode.GetAttribute("type") -in @("obsolete", "vanished")) {
            continue
        }
        $placeholderPattern = "\{([A-Za-z_][A-Za-z0-9_]*)(?:![rsa])?(?::[^{}]+)?\}"
        $sourcePlaceholders = @([regex]::Matches($sourceNode.InnerText, $placeholderPattern) | ForEach-Object { $_.Groups[1].Value } | Sort-Object)
        $translationPlaceholders = @([regex]::Matches($translationNode.InnerText, $placeholderPattern) | ForEach-Object { $_.Groups[1].Value } | Sort-Object)
        if (($sourcePlaceholders -join "|") -ne ($translationPlaceholders -join "|")) {
            throw "Placeholder mismatch in $($pack.TsPath): $($sourceNode.InnerText)"
        }
    }
    $unfinished = @($catalog.SelectNodes('//translation[@type="unfinished"]')).Count
    $empty = @($catalog.SelectNodes(
        '//message[not(translation/@type="obsolete" or translation/@type="vanished") and ' +
        '(not(translation) or normalize-space(translation)="")]'
    )).Count
    if ($unfinished -ne 0 -or $empty -ne 0) {
        throw "Incomplete catalog $($pack.TsPath) (unfinished=$unfinished, empty=$empty)"
    }
    & $lrelease $pack.TsPath -qm $pack.QmPath
    if ($LASTEXITCODE -ne 0) {
        throw "lrelease failed for $($pack.Code) with exit code $LASTEXITCODE"
    }
}

Write-Output "$($packs.Count) language packs are complete and compiled."
