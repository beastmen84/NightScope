$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Spec = Join-Path $PSScriptRoot "NightScope.spec"
$DistDir = Join-Path $Root "dist\NightScope"
$LicenseCheck = Join-Path $Root "tools\generate_third_party_licenses.py"
$QtBundleAudit = Join-Path $Root "tools\audit_qt_bundle.py"
$LegalFiles = @("LICENSE", "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_LICENSES.txt")

if (-not (Test-Path $Python)) {
    throw "Python venv not found at $Python"
}

& $Python $LicenseCheck --check
if ($LASTEXITCODE -ne 0) {
    throw "Third-party license archive is missing or stale"
}

& $Python -m PyInstaller --clean --noconfirm $Spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

foreach ($FileName in $LegalFiles) {
    Copy-Item -LiteralPath (Join-Path $Root $FileName) -Destination $DistDir
}

& $Python $QtBundleAudit $DistDir
if ($LASTEXITCODE -ne 0) {
    throw "Qt bundle or legal-file audit failed"
}
