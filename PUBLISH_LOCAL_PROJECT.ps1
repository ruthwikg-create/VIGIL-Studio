# VIGIL Studio v4.8 — local GitHub publisher
# Downloads nothing from ChatGPT. Copies only selected source/documentation folders.
# Review source content before publishing; never include identifiable patient records.
param([string]$SourceFolder)
$ErrorActionPreference = "Stop"
$repoUrl = "https://github.com/ruthwikg-create/VIGIL-Studio.git"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git for Windows is required: https://git-scm.com/downloads/win" -ForegroundColor Red
    exit 1
}
if (-not $SourceFolder) {
    $SourceFolder = Read-Host "Paste the path of your extracted VIGIL Studio v4.8 folder"
}
$resolved = Resolve-Path -LiteralPath $SourceFolder -ErrorAction Stop
$source = $resolved.Path
if (-not ((Test-Path (Join-Path $source "vigil_studio")) -and (Test-Path (Join-Path $source "tests")))) {
    throw "That folder does not contain the complete source. Select a folder containing vigil_studio and tests."
}
Write-Host "Publishing research source from: $source"
Write-Host "Do not continue if this folder contains confidential hospital/patient data." -ForegroundColor Yellow
$choice = Read-Host "Confirm source review and upload to the PUBLIC repository (type YES)"
if ($choice -ne "YES") { Write-Host "Cancelled"; exit 0 }

$temp = Join-Path $env:TEMP ("vigil-publish-" + [guid]::NewGuid().ToString("N"))
try {
    git clone $repoUrl $temp
    if ($LASTEXITCODE -ne 0) { throw "Could not clone GitHub repository. Check GitHub sign-in." }
    $folders = @("vigil_studio", "scripts", "tests", "docs", "examples", "media", ".github")
    foreach ($folder in $folders) {
        $from = Join-Path $source $folder
        if (Test-Path $from) {
            $to = Join-Path $temp $folder
            New-Item -Path $to -ItemType Directory -Force | Out-Null
            Get-ChildItem -LiteralPath $from -Force | ForEach-Object {
                Copy-Item -LiteralPath $_.FullName -Destination $to -Recurse -Force
            }
        }
    }
    $files = @(
        "README.md", "LICENSE", "SECURITY.md", ".gitignore", "CHANGELOG.md",
        "TEST_RESULTS.md", "launch.py", "launch_showcase.py",
        "requirements.txt", "requirements-ai.txt", "requirements-build.txt",
        "requirements-security.txt", "START_WINDOWS.bat", "START_SHOWCASE_WINDOWS.bat",
        "START_AI_RESEARCH_WINDOWS.bat", "RUN_RESEARCH_WINDOWS.bat",
        "RUN_SELF_TEST_WINDOWS.bat", "RUN_MITBIH_VERIFICATION_WINDOWS.bat",
        "RUN_SECURITY_TESTS_WINDOWS.bat", "RUN_ENGINEERING_EVIDENCE_WINDOWS.bat",
        "RUN_HOSPITAL_READINESS_CHECK_WINDOWS.bat",
        "GENERATE_REFERENCE_REPORT_WINDOWS.bat",
        "VERIFY_EVIDENCE_PACKAGE_WINDOWS.bat",
        "INSTALL_ADVANCED_AI_WINDOWS.bat", "INSTALL_FULL_RESEARCH_WINDOWS.bat"
    )
    foreach ($file in $files) {
        $from = Join-Path $source $file
        if (Test-Path $from) { Copy-Item -LiteralPath $from -Destination $temp -Force }
    }
    Push-Location $temp
    try {
        git add -A
        if ($LASTEXITCODE -ne 0) { throw "Git add failed" }
        $pending = git status --porcelain
        if (-not $pending) {
            Write-Host "Repository already contains these files. Nothing to upload." -ForegroundColor Green
            exit 0
        }
        git commit -m "Publish VIGIL Studio v4.8 research source and screenshots"
        if ($LASTEXITCODE -ne 0) { throw "Git commit failed. Configure Git user.name and user.email." }
        git push origin HEAD:main
        if ($LASTEXITCODE -ne 0) { throw "Git push failed. Verify GitHub authentication." }
        Write-Host "SUCCESS: https://github.com/ruthwikg-create/VIGIL-Studio" -ForegroundColor Green
    } finally { Pop-Location }
} finally {
    if (Test-Path $temp) { Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue }
}
