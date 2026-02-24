# Refactoring-Swarm-GogitatusCodex

## Dépôt — checklist de soumission

Suivre ces étapes avant de pousser votre dépôt pour la notation :

- **Structure obligatoire** : la racine du dépôt doit contenir — `src/`, `main.py`, `requirements.txt`, `logs/` (avec `logs/experiment_data.json`).
- **Fichiers à exclure** : votre `.gitignore` doit exclure `venv/` ou `env/`, `.env`, `sandbox/`, et `__pycache__/`.
- **Logs** : `logs/` est généralement ignoré ; forcez l'ajout du fichier final avec :

	PowerShell:

	```powershell
	git add -f logs/experiment_data.json
	git commit -m "Add experiment_data.json for submission"
	git push origin main
	```

- Un script d'aide est fourni : `scripts/prepare_submission.ps1` (PowerShell) pour forcer l'ajout et committer.

## Rappel sécurité
- Ne publiez jamais vos clés dans le dépôt. Assurez-vous que le fichier `.env` est listé dans `.gitignore`.
