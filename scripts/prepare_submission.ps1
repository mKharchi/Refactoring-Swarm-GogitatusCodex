<#
Force-add `logs/experiment_data.json` (qui est normalement ignoré),
commite et affiche l'état git pour vérifier.

Usage (PowerShell):
  ./scripts/prepare_submission.ps1 -Message "Mon message de commit"
#>
param(
    [string]$Message = "Add logs/experiment_data.json for submission"
)

Write-Host "Forcer l'ajout de logs/experiment_data.json..." -ForegroundColor Cyan
git add -f logs/experiment_data.json

Write-Host "Vérifier l'état git actuel..." -ForegroundColor Cyan
git status --porcelain

Write-Host "Création du commit..." -ForegroundColor Cyan
git commit -m $Message
if ($LASTEXITCODE -ne 0) {
  Write-Host "Aucun changement à committer." -ForegroundColor Yellow
}

Write-Host "Rappel: poussez vos commits avec 'git push origin main' (ou branche appropriée)." -ForegroundColor Green
