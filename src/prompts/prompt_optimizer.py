"""
Optimisation de la consommation de tokens.
Responsabilité 2 : Optimiser les prompts pour minimiser le coût en tokens.
"""

import tiktoken
from typing import Optional


class PromptOptimizer:
    """
    Optimise les prompts pour réduire la consommation de tokens.
    """
    
    def __init__(self):
        """Initialise l'optimiseur avec l'encodeur tiktoken."""
        # Utiliser l'encodeur compatible avec la plupart des modèles
        self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def compter_tokens(self, texte: str) -> int:
        """
        Compte le nombre de tokens dans un texte.
        
        Args:
            texte: Le texte à analyser
        
        Returns:
            Nombre de tokens
        """
        return len(self.encoder.encode(texte))
    
    def analyser_prompt(
        self, 
        system_prompt: str, 
        user_prompt: str,
        tarif_input: float = 0.075,  # $/1M tokens (Gemini Flash)
        tarif_output: float = 0.30   # $/1M tokens
    ) -> dict:
        """
        Analyse le coût d'un prompt complet.
        
        Args:
            system_prompt: Le prompt système
            user_prompt: Le prompt utilisateur
            tarif_input: Tarif par million de tokens (input)
            tarif_output: Tarif par million de tokens (output)
        
        Returns:
            Dictionnaire avec statistiques et coût estimé
        """
        tokens_system = self.compter_tokens(system_prompt)
        tokens_user = self.compter_tokens(user_prompt)
        tokens_total_input = tokens_system + tokens_user
        
        # Coût input
        cout_input = (tokens_total_input / 1_000_000) * tarif_input
        
        # Estimation output (moyenne basée sur type d'agent)
        tokens_output_estime = 500  # Moyenne conservative
        cout_output = (tokens_output_estime / 1_000_000) * tarif_output
        
        cout_total = cout_input + cout_output
        
        # Vérifier si respecte les limites
        limite_tokens = 1500  # Objectif par itération
        statut = " OK" if tokens_total_input <= limite_tokens else " TROP LONG"
        
        return {
            "tokens_system": tokens_system,
            "tokens_user": tokens_user,
            "tokens_total_input": tokens_total_input,
            "tokens_output_estime": tokens_output_estime,
            "cout_input_usd": cout_input,
            "cout_output_usd": cout_output,
            "cout_total_usd": cout_total,
            "statut": statut,
            "limite": limite_tokens,
            "marge": limite_tokens - tokens_total_input
        }
    
    def optimiser_code_contexte(
        self, 
        code: str, 
        max_tokens: int = 2000
    ) -> str:
        """
        Réduit la taille du code si trop long pour le contexte.
        
        Stratégie :
        1. Garder les imports
        2. Garder les signatures de fonctions/classes
        3. Résumer les corps de fonctions
        
        Args:
            code: Le code source complet
            max_tokens: Nombre maximum de tokens autorisés
        
        Returns:
            Code optimisé (ou original si déjà OK)
        """
        tokens_actuels = self.compter_tokens(code)
        
        if tokens_actuels <= max_tokens:
            return code  # Pas besoin d'optimiser
        
        print(f" Code trop long ({tokens_actuels} tokens), réduction à {max_tokens}...")
        
        lignes = code.split('\n')
        
        # Garder les imports (début du fichier)
        imports = []
        code_restant = []
        in_imports = True
        
        for ligne in lignes:
            stripped = ligne.strip()
            if in_imports:
                if stripped.startswith(('import ', 'from ')):
                    imports.append(ligne)
                elif stripped and not stripped.startswith('#'):
                    in_imports = False
                    code_restant.append(ligne)
            else:
                code_restant.append(ligne)
        
        # Extraire signatures de fonctions/classes
        signatures = []
        in_function = False
        indent_level = 0
        
        for ligne in code_restant:
            stripped = ligne.strip()
            
            # Détecter définition
            if stripped.startswith(('def ', 'class ', 'async def ')):
                signatures.append(ligne)
                in_function = True
                indent_level = len(ligne) - len(ligne.lstrip())
                
                # Ajouter docstring si présente (ligne suivante)
                continue
            
            # Si dans une fonction, chercher docstring
            if in_function:
                if '"""' in stripped or "'''" in stripped:
                    signatures.append(ligne)
                else:
                    # Remplacer corps par commentaire
                    signatures.append(" " * (indent_level + 4) + "# ... (code résumé)")
                    in_function = False
        
        # Reconstruire code optimisé
        code_optimise = '\n'.join(imports + [''] + signatures)
        
        tokens_optimises = self.compter_tokens(code_optimise)
        print(f" Code réduit : {tokens_actuels} → {tokens_optimises} tokens")
        
        return code_optimise
    
    def generer_rapport(self, analyses: list[dict]) -> str:
        """
        Génère un rapport d'optimisation pour plusieurs prompts.
        
        Args:
            analyses: Liste de résultats d'analyse_prompt()
        
        Returns:
            Rapport formaté en texte
        """
        total_tokens = sum(a["tokens_total_input"] for a in analyses)
        total_cout = sum(a["cout_total_usd"] for a in analyses)
        
        rapport = " RAPPORT D'OPTIMISATION TOKENS\n"
        rapport += "=" * 50 + "\n\n"
        
        for i, analyse in enumerate(analyses, 1):
            rapport += f"Prompt {i}:\n"
            rapport += f"  Tokens: {analyse['tokens_total_input']} "
            rapport += f"({analyse['statut']})\n"
            rapport += f"  Coût: ${analyse['cout_total_usd']:.6f}\n\n"
        
        rapport += f"TOTAL:\n"
        rapport += f"  Tokens: {total_tokens}\n"
        rapport += f"  Coût: ${total_cout:.6f}\n"
        rapport += f"  Par itération: ~{total_tokens} tokens\n"
        rapport += f"  Sur 10 itérations: ~{total_tokens * 10} tokens\n"
        
        return rapport


# Instance globale
prompt_optimizer = PromptOptimizer()