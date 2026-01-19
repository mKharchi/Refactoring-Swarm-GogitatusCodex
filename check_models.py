import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

print("📋 Modèles Gemini disponibles:\n")
print(f"{'Nom du modèle':<40} {'Description':<50}")
print("="*90)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"{model.name:<40} {model.display_name:<50}")

print("\n💡 Modèles recommandés pour votre projet:")
print("  - gemini-1.5-flash      (Bon équilibre vitesse/qualité)")
print("  - gemini-1.5-pro        (Meilleure qualité, plus lent)")
print("  - gemini-2.0-flash-exp  (Expérimental, rapide)")