param(
    [string]$Model = "gemma3",
    [int]$Rounds = 50,
    [double]$AuditProb = 0.25,
    [double]$LiePenalty = 25.0,
    [int]$Seed = 42,
    [double]$Temperature = 0.2
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$strategies = @("honest_fair", "self_interested", "deceptive")

foreach ($strategy in $strategies) {
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "Running Gemma 3 strategy: $strategy"
    Write-Host "============================================================"

    python scripts\run_gemma3_hidden_pie_demo.py `
        --model $Model `
        --rounds $Rounds `
        --temperature $Temperature `
        --audit-prob $AuditProb `
        --lie-penalty $LiePenalty `
        --seed $Seed `
        --strategy $strategy

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Gemma 3 strategy run failed for '$strategy' with exit code $LASTEXITCODE. Stopping batch."
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "All Gemma 3 strategy runs completed."
