"""
Gestion du contexte et cache des prompts système.
Responsabilité 3 : Gérer le contexte intelligemment.
"""

from pathlib import Path
from typing import Optional


class ContextManager:
    """
    Gère le chargement et le cache des prompts système pour optimisation.
    """
    
    def __init__(self, prompts_dir: str = "src/prompts/system_prompts"):
        """
        Initialise le gestionnaire de contexte.
        
        Args:
            prompts_dir: Chemin vers le dossier contenant les prompts
        """
        self.prompts_dir = Path(prompts_dir)
        self.cache_prompts = {}
    
    def get_system_prompt(self, agent_name: str) -> str:
        """
        Charge et met en cache un prompt système.
        
        Args:
            agent_name: Nom de l'agent ("auditor", "fixer", ou "judge")
        
        Returns:
            Le contenu du prompt système
        
        Raises:
            FileNotFoundError: Si le fichier prompt n'existe pas
            ValueError: Si le nom d'agent est invalide
        """
        # Validation
        agents_valides = ["auditor", "fixer", "judge"]
        if agent_name not in agents_valides:
            raise ValueError(
                f"Agent '{agent_name}' invalide. "
                f"Utilisez: {', '.join(agents_valides)}"
            )
        
        # Vérifier le cache d'abord (optimisation)
        if agent_name in self.cache_prompts:
            return self.cache_prompts[agent_name]
        
        # Charger depuis le fichier
        fichier = self.prompts_dir / f"{agent_name}_current_prompt.txt"
        
        if not fichier.exists():
            raise FileNotFoundError(
                f" Prompt introuvable : {fichier}\n"
                f"Créez le fichier avec le contenu du prompt système."
            )
        
        with open(fichier, 'r', encoding='utf-8') as f:
            contenu = f.read()
        
        # Mettre en cache pour éviter lectures multiples
        self.cache_prompts[agent_name] = contenu
        
        return contenu
    
    def clear_cache(self):
        """
        Vide le cache des prompts.
        
        Utile pour rechargement après modification des fichiers prompts.
        """
        self.cache_prompts.clear()
    
    def get_cache_stats(self) -> dict:
        """
        Retourne les statistiques du cache.
        
        Returns:
            Dictionnaire avec les stats (agents en cache, taille)
        """
        return {
            "agents_en_cache": list(self.cache_prompts.keys()),
            "nombre_agents": len(self.cache_prompts)
        }


# Instance globale pour faciliter l'import
context_manager = ContextManager()