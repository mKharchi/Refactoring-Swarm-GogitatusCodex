"""
Construction des prompts avec contexte intelligent.
Responsabilité 3 : Gérer le contexte pour ne pas saturer la mémoire.
"""

import json
from typing import Tuple, Dict, List, Optional
from src.prompts.context_manager import context_manager
from src.prompts.prompt_optimizer import prompt_optimizer


class PromptBuilder:
    """
    Construit les prompts complets (system + user) pour chaque agent.
    Gère le contexte de manière optimale pour minimiser les tokens.
    """
    
    def __init__(self):
        """Initialise le builder avec context manager et optimizer."""
        self.context_mgr = context_manager
        self.optimizer = prompt_optimizer
    
    def construire_prompt_auditeur(
        self,
        code_source: str,
        nom_fichier: str,
        score_pylint: Optional[float] = None
    ) -> Tuple[str, str]:
        """
        Construit le prompt pour l'agent auditeur.
        
        Contexte léger : juste le code + score pylint optionnel.
        
        Args:
            code_source: Le code à analyser
            nom_fichier: Nom du fichier
            score_pylint: Score Pylint optionnel (contexte métrique)
        
        Returns:
            (system_prompt, user_prompt)
        """
        # Charger le prompt système depuis le cache
        system_prompt = self.context_mgr.get_system_prompt("auditor")
        
        # Construire le prompt utilisateur SANS balises markdown
        user_prompt = f"FICHIER: {nom_fichier}\n"
        
        if score_pylint is not None:
            user_prompt += f"SCORE PYLINT ACTUEL: {score_pylint:.1f}/10\n"
        
        # Code sans balises markdown pour éviter confusion
        user_prompt += f"\nCODE À ANALYSER:\n{code_source}\n"
        user_prompt += "\nRetourne ton analyse au format JSON strict (pas de markdown, pas de texte avant/après)."
        
        return system_prompt, user_prompt
    
    def construire_prompt_correcteur(
        self,
        code_source: str,
        problemes: List[Dict],
        nom_fichier: str
    ) -> Tuple[str, str]:
        """
        Construit le prompt pour l'agent correcteur.
        
        Contexte ciblé : code + problèmes prioritaires (filtrés).
        
        Args:
            code_source: Le code à corriger
            problemes: Liste des problèmes détectés
            nom_fichier: Nom du fichier
        
        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.context_mgr.get_system_prompt("fixer")
        
        # Filtrer pour garder seulement problèmes critiques/majeurs
        # (optimisation tokens)
        problemes_prioritaires = [
            p for p in problemes
            if p.get("severite") in ["critique", "majeur"]
        ]
        
        # Si aucun prioritaire, prendre tous (max 10 pour éviter saturation)
        if not problemes_prioritaires:
            problemes_prioritaires = problemes[:10] if len(problemes) > 10 else problemes
        else:
            problemes_prioritaires = problemes_prioritaires[:10]
        
        # Construire user prompt SANS balises markdown pour éviter confusion
        user_prompt = f"""FICHIER: {nom_fichier}

CODE À CORRIGER:
{code_source}

PROBLÈMES DÉTECTÉS ({len(problemes_prioritaires)}):
{json.dumps(problemes_prioritaires, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
1. Lis le code ci-dessus
2. Corrige tous les problèmes listés
3. Ajoute docstrings Google-style manquantes
4. Assure-toi que le code compile sans erreur
5. Retourne UNIQUEMENT le code corrigé complet

IMPORTANT:
- NE mets PAS de ```python ou ```
- NE mets PAS d'explications
- Retourne DIRECTEMENT le code corrigé
- Le code doit commencer par import, def, class, ou #

CODE CORRIGÉ DU FICHIER {nom_fichier}:
"""
        
        return system_prompt, user_prompt
    
    def construire_prompt_testeur(
        self,
        resultats_tests: str,
        scores_pylint: Dict[str, float],
        iteration: int
    ) -> Tuple[str, str]:
        """
        Construit le prompt pour l'agent testeur/juge.
        
        Contexte résumé : logs tests (filtrés) + scores moyens.
        
        Args:
            resultats_tests: Sortie de pytest
            scores_pylint: Dictionnaire {fichier: score}
            iteration: Numéro d'itération actuelle
        
        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.context_mgr.get_system_prompt("judge")
        
        # Optimiser les logs si trop longs (>1500 caractères)
        if len(resultats_tests) > 1500:
            lignes = resultats_tests.split('\n')
            # Garder seulement lignes importantes
            lignes_importantes = [
                l for l in lignes
                if any(mot in l for mot in [
                    'FAILED', 'ERROR', 'passed', 'failed',
                    'AssertionError', 'Exception', '===='
                ])
            ]
            resultats_tests = '\n'.join(lignes_importantes)
        
        # Calculer score moyen
        if scores_pylint:
            score_moyen = sum(scores_pylint.values()) / len(scores_pylint)
        else:
            score_moyen = 0.0
        
        # Construire user prompt
        user_prompt = f"ITÉRATION: {iteration}/10\n"
        user_prompt += f"\nRÉSULTATS TESTS:\n{resultats_tests}\n"
        user_prompt += f"\nSCORES PYLINT:\n"
        user_prompt += json.dumps(scores_pylint, indent=2)
        user_prompt += f"\nScore moyen: {score_moyen:.2f}/10\n"
        user_prompt += "\nAnalyse et produis ta décision JSON."
        
        return system_prompt, user_prompt
    
    def analyser_couts(
        self,
        system_prompt: str,
        user_prompt: str,
        agent_name: str
    ) -> Dict:
        """
        Analyse le coût d'un prompt avant envoi.
        
        Args:
            system_prompt: Le prompt système
            user_prompt: Le prompt utilisateur
            agent_name: Nom de l'agent (pour logging)
        
        Returns:
            Dictionnaire avec analyse des tokens et coûts
        """
        analyse = self.optimizer.analyser_prompt(system_prompt, user_prompt)
        
        # Ajouter le nom de l'agent
        analyse["agent"] = agent_name
        
        # Warning si trop long
        if analyse["tokens_total_input"] > 1500:
            print(f"⚠️ [{agent_name}] Prompt long : {analyse['tokens_total_input']} tokens")
        
        return analyse


# Instance globale
prompt_builder = PromptBuilder()
def construire_prompt_correcteur(
    self,
    code_source: str,
    problemes: List[Dict],
    nom_fichier: str
) -> Tuple[str, str]:
    """
    Construit le prompt pour l'agent correcteur.
    
    Contexte ciblé : code + problèmes prioritaires (filtrés).
    
    Args:
        code_source: Le code à corriger
        problemes: Liste des problèmes détectés
        nom_fichier: Nom du fichier
    
    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = self.context_mgr.get_system_prompt("fixer")
    
    # Filtrer pour garder seulement problèmes critiques/majeurs
    # (optimisation tokens)
    problemes_prioritaires = [
        p for p in problemes
        if p.get("severite") in ["critique", "majeur"]
    ]
    
    # Si aucun prioritaire, prendre tous (max 10 pour éviter saturation)
    if not problemes_prioritaires:
        problemes_prioritaires = problemes[:10] if len(problemes) > 10 else problemes
    else:
        problemes_prioritaires = problemes_prioritaires[:10]
    
    # Construire user prompt SANS balises markdown pour éviter confusion
    user_prompt = f"""FICHIER: {nom_fichier}

CODE À CORRIGER:
{code_source}

PROBLÈMES DÉTECTÉS ({len(problemes_prioritaires)}):
{json.dumps(problemes_prioritaires, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
1. Lis le code ci-dessus
2. Corrige tous les problèmes listés
3. Ajoute docstrings Google-style manquantes
4. Assure-toi que le code compile sans erreur
5. Retourne UNIQUEMENT le code corrigé complet

IMPORTANT:
- NE mets PAS de ```python ou ```
- NE mets PAS d'explications
- Retourne DIRECTEMENT le code corrigé
- Le code doit commencer par import, def, class, ou #

CODE CORRIGÉ DU FICHIER {nom_fichier}:
"""
    
    return system_prompt, user_prompt