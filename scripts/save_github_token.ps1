# Securely save a GitHub token for the publisher.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\save_github_token.ps1
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$secretDir = Join-Path $repoRoot ".secrets"
$tokenPath = Join-Path $secretDir "github_token.txt"

New-Item -ItemType Directory -Force -Path $secretDir | Out-Null

$secure = Read-Host "Paste GitHub token (input hidden)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "Token is empty."
    }
    Set-Content -LiteralPath $tokenPath -Value $token.Trim() -NoNewline -Encoding UTF8
    Write-Output "Saved to $tokenPath"
    Write-Output "The .secrets directory is gitignored and is never uploaded."
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
