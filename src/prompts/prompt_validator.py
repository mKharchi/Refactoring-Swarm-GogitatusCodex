"""
Validation des réponses LLM pour éviter les hallucinations.
Responsabilité 2 : Optimiser les prompts pour minimiser les hallucinations.
"""

import json
from typing import Tuple, Dict, Any, Optional


class PromptValidator:
    """
    Valide que les réponses des LLM respectent les formats attendus.
    Anti-hallucination : vérifie structure, types, et cohérence.
    """
    
    @staticmethod
    def valider_reponse_auditeur(reponse: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valide la réponse de l'agent auditeur.
        
        Vérifie :
        - Pas de markdown (```json)
        - JSON parsable
        - Tous les champs obligatoires présents
        - Types et valeurs correctes
        
        Args:
            reponse: La réponse brute du LLM
        
        Returns:
            (est_valide, message_erreur, donnees_parsed)
        """
        reponse_clean = reponse.strip()
        
        # 1. Vérifier absence de markdown
        if reponse_clean.startswith("```"):
            return False, " Markdown détecté - hallucination format", None
        
        # 2. Parser JSON
        try:
            data = json.loads(reponse_clean)
        except json.JSONDecodeError as e:
            return False, f" JSON invalide : {str(e)}", None
        
        # 3. Vérifier structure principale
        champs_requis = ["score_qualite", "problemes", "resume"]
        for champ in champs_requis:
            if champ not in data:
                return False, f" Champ manquant : {champ}", None
        
        # 4. Valider le score
        score = data["score_qualite"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 10):
            return False, f" Score invalide : {score} (doit être 0-10)", None
        
        # 5. Valider chaque problème
        if not isinstance(data["problemes"], list):
            return False, " 'problemes' doit être une liste", None
        
        for idx, prob in enumerate(data["problemes"]):
            # Champs obligatoires
            champs_prob = ["fichier", "ligne", "type", "severite", "description", "suggestion"]
            for champ in champs_prob:
                if champ not in prob:
                    return False, f" Problème {idx} : champ '{champ}' manquant", None
            
            # Valider type
            types_valides = ["bug", "pep8", "documentation", "naming"]
            if prob["type"] not in types_valides:
                return False, f" Problème {idx} : type '{prob['type']}' invalide", None
            
            # Valider sévérité
            severites_valides = ["critique", "majeur", "mineur"]
            if prob["severite"] not in severites_valides:
                return False, f" Problème {idx} : sévérité '{prob['severite']}' invalide", None
            
            # Valider numéro de ligne
            if not isinstance(prob["ligne"], int) or prob["ligne"] < 1:
                return False, f" Problème {idx} : ligne invalide ({prob['ligne']})", None
            
            # Vérifier longueurs (optimisation tokens)
            if len(prob["description"]) > 100:
                return False, f" Problème {idx} : description trop longue (>100 car)", None
            
            if len(prob["suggestion"]) > 150:
                return False, f" Problème {idx} : suggestion trop longue (>150 car)", None
        
        # 6. Vérifier longueur résumé
        if len(data["resume"]) > 200:
            return False, " Résumé trop long (>200 caractères)", None
        
        return True, " Réponse valide", data
    
    @staticmethod
    def valider_reponse_correcteur(reponse: str) -> Tuple[bool, str, Optional[str]]:
        """
        Valide que le code corrigé est du Python valide.
        
        Args:
            reponse: La réponse brute du LLM (code Python)
        
        Returns:
            (est_valide, message_erreur, code_clean)
        """
        code_clean = reponse.strip()
        
        # 1. Nettoyer markdown si présent (tolérance)
        if code_clean.startswith("```python"):
            code_clean = code_clean[9:]
        elif code_clean.startswith("```"):
            code_clean = code_clean[3:]
        
        if code_clean.endswith("```"):
            code_clean = code_clean[:-3]
        
        code_clean = code_clean.strip()
        
        # 2. Vérifier longueur minimale
        if len(code_clean) < 10:
            return False, " Code trop court - possible hallucination", None
        
        # 3. Vérifier syntaxe Python
        try:
            compile(code_clean, '<string>', 'exec')
        except SyntaxError as e:
            return False, f" Erreur syntaxe Python : {str(e)}", None
        
        # 4. Vérifier absence de commentaires suspects (hallucination)
        lignes_suspectes = [
            "# TODO",
            "# FIXME",
            "# placeholder",
            "# à implémenter",
            "pass  # à compléter"
        ]
        
        code_lower = code_clean.lower()
        for suspect in lignes_suspectes:
            if suspect.lower() in code_lower:
                return False, f" Commentaire suspect : '{suspect}'", None
        
        return True, " Code valide", code_clean
    
    @staticmethod
    def valider_reponse_testeur(reponse: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valide la décision du testeur/juge.
        
        Args:
            reponse: La réponse brute du LLM
        
        Returns:
            (est_valide, message_erreur, donnees_parsed)
        """
        try:
            data = json.loads(reponse.strip())
        except json.JSONDecodeError:
            return False, " JSON invalide", None
        
        # Vérifier décision
        if "decision" not in data:
            return False, " Champ 'decision' manquant", None
        
        if data["decision"] not in ["VALIDE", "ECHEC"]:
            return False, f" Décision invalide : {data['decision']}", None
        
        # Vérifier raison
        if "raison" not in data:
            return False, " Champ 'raison' manquant", None
        
        if len(data["raison"]) > 200:
            return False, " Raison trop longue (>200 car)", None
        
        # Vérifier score_qualite
        if "score_qualite" not in data:
            return False, " Champ 'score_qualite' manquant", None
        
        # Vérifier problemes_restants (liste)
        if "problemes_restants" not in data:
            return False, " Champ 'problemes_restants' manquant", None
        
        if not isinstance(data["problemes_restants"], list):
            return False, " 'problemes_restants' doit être une liste", None
        
        # Vérifier suggestions
        if "suggestions_correcteur" not in data:
            return False, " Champ 'suggestions_correcteur' manquant", None
        
        if len(data["suggestions_correcteur"]) > 500:
            return False, " Suggestions trop longues (>500 car)", None
        
        return True, " Décision valide", data


# Instance globale
prompt_validator = PromptValidator()