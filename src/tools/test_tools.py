"""
Mock implementations for testing tools.
TEMPORARY - À remplacer par le Toolsmith dans 2 jours.
"""
import os
import subprocess
import tempfile
from typing import Dict, Optional


def write_test_file(filepath: str, content: str) -> bool:
    """
    MOCK - Écrit un fichier de test.
    Sera remplacé par l'implémentation sécurisée du Toolsmith.
    
    Args:
        filepath: Chemin du fichier de test (relatif au sandbox)
        content: Contenu du fichier de test Python
    
    Returns:
        True si succès, False sinon
    """
    try:
        # Créer le dossier si nécessaire
        test_dir = os.path.dirname(filepath)
        if test_dir and not os.path.exists(test_dir):
            os.makedirs(test_dir, exist_ok=True)
        
        # Écrire le fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ Fichier de test créé: {filepath}")
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur création test: {e}")
        return False


def run_pytest(test_file_path: str, code_files: list = None) -> Dict:
    """
    MOCK - Exécute pytest sur un fichier de test.
    Sera remplacé par l'implémentation sécurisée du Toolsmith.
    
    Args:
        test_file_path: Chemin du fichier de test
        code_files: Liste des fichiers de code à tester (optionnel)
    
    Returns:
        Dict avec résultats:
        {
            "success": bool,
            "passed": bool,
            "total_tests": int,
            "passed_tests": int,
            "failed_tests": int,
            "output": str,
            "errors": list,
            "execution_time": float
        }
    """
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(test_file_path):
            return {
                "success": False,
                "passed": False,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "output": "",
                "errors": [f"Fichier de test non trouvé: {test_file_path}"],
                "execution_time": 0.0
            }
        
        # Exécuter pytest
        result = subprocess.run(
            ['pytest', test_file_path, '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=30  # Timeout de 30 secondes
        )
        
        # Parser la sortie
        output = result.stdout + result.stderr
        
        # Compter les tests (basique)
        passed_tests = output.count(' PASSED')
        failed_tests = output.count(' FAILED')
        total_tests = passed_tests + failed_tests
        
        # Extraire les erreurs
        errors = []
        if result.returncode != 0:
            # Extraire les lignes d'erreur
            for line in output.split('\n'):
                if 'FAILED' in line or 'ERROR' in line or 'AssertionError' in line:
                    errors.append(line.strip())
        
        return {
            "success": True,
            "passed": result.returncode == 0,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "output": output,
            "errors": errors[:10],  # Limiter à 10 erreurs
            "execution_time": 0.0  # Mock - sera calculé par le Toolsmith
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "passed": False,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "output": "",
            "errors": ["Timeout: Les tests ont pris plus de 30 secondes"],
            "execution_time": 30.0
        }
        
    except Exception as e:
        return {
            "success": False,
            "passed": False,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "output": "",
            "errors": [f"Erreur pytest: {str(e)}"],
            "execution_time": 0.0
        }


def cleanup_test_files(test_file_path: str) -> bool:
    """
    MOCK - Nettoie les fichiers de test temporaires.
    Sera remplacé par l'implémentation du Toolsmith.
    
    Args:
        test_file_path: Chemin du fichier de test à supprimer
    
    Returns:
        True si succès, False sinon
    """
    try:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"  🗑️  Fichier de test nettoyé: {test_file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"  ⚠️  Erreur nettoyage: {e}")
        return False


def validate_test_syntax(test_content: str) -> Dict:
    """
    MOCK - Valide la syntaxe d'un fichier de test avant exécution.
    
    Args:
        test_content: Contenu du fichier de test
    
    Returns:
        Dict avec résultat validation
    """
    try:
        # Essayer de compiler le code
        compile(test_content, '<string>', 'exec')
        return {
            "valid": True,
            "error": None
        }
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Erreur syntaxe ligne {e.lineno}: {e.msg}"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }