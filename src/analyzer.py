import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import os
import time

# Konfigurácia (Európa)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "europe-west1" 

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Vertex AI init failed: {e}")

def analyze_content(scraped_data: dict, client_brief: dict):
    """
    AGENCY MODE 3.0: Deep Interrogation (Sériový výsluch)
    Vykonáva sériu cielených otázok na AI, aby zistil skutočnú reputáciu.
    """
    
    try:
        model = GenerativeModel("gemini-2.5-pro")
    except Exception as e:
        return _error_response(str(e))
    
    client = client_brief.get('client_name')
    goals = client_brief.get('goals')
    industry = client_brief.get('industry')
    
    print(f"--- ZAČÍNAM SÉRIOVÝ VÝSLUCH PRE: {client} ---")

    # --- KROK 1: BLIND REPUTATION CHECK (Bez webu) ---
    # Pýtame sa AI, čo vie o firme len z názvu.
    print("1. Fáza: Test Znalosti (Blind Test)...")
    q1_prompt = f"""
    Jsi nezávislý analytik značek.
    Otázka: Co přesně víš o entitě "{client}" v segmentu "{industry}"? 
    Buď upřímný. Pokud ji neznáš, řekni "Neznámá entita". 
    Pokud ji znáš, jaké jsou její 3 hlavní atributy (pozitivní i negativní)?
    Odpověz stručně v češtině.
    """
    res1 = model.generate_content(q1_prompt).text

    # --- KROK 2: GOAL ALIGNMENT CHECK (Validace Cílů) ---
    # Konfrontujeme AI: "Klient chce byť X, je to pravda?"
    print("2. Fáza: Validace Ambicí...")
    q2_prompt = f"""
    Kontext: Entita "{client}" tvrdí, že její identita je: "{goals}".
    
    Úkol kritika:
    Na základě tvých znalostí (a předchozí odpovědi: "{res1}"), je toto tvrzení pravdivé? 
    Vnímá trh tuto firmu takto? Ano/Ne a proč? Buď kritický.
    Odpověz stručně v češtině.
    """
    res2 = model.generate_content(q2_prompt).text

    # --- KROK 3: FINAL SYNTHESIS & WEB GAP ANALYSIS ---
    # Spojíme všetko dokopy aj s webom.
    print("3. Fáza: Finální Syntéza s Webem...")
    final_prompt = f"""
    Jsi AI Perception Auditor. Provedi finální syntézu reputace.

    VSTUPNÍ DATA Z VÝSLUCHU:
    1. CO VÍ AI (Memory): {res1}
    2. NÁZOR AI NA CÍLE (Critique): {res2}
    3. REALITA NA WEBU (Scraped): {scraped_data.get('content_preview')}... (zkráceno)

    ÚKOL:
    Vygeneruj finální JSON report v Češtině.
    Porovnej "Co AI ví" vs "Co je na webu" vs "Co klient chce".
    
    VÝSTUP JSON:
    {{
        "summary": {{
            "overall_score": int, // 0-100 (Skóre reputační autority)
            "page_title": "{scraped_data.get('title')}"
        }},
        "insights": [
            {{ 
                "type": "info", 
                "title": "Fáze 1: AI Paměť", 
                "message": "Shrnutí toho, co o firmě víš (z odpovědi: {res1})" 
            }},
            {{ 
                "type": "warning", 
                "title": "Fáze 2: Reality Check", 
                "message": "Kritické zhodnocení cílů (z odpovědi: {res2})" 
            }},
            {{ 
                "type": "success", 
                "title": "Fáze 3: Web Důkazy", 
                "message": "Podporuje obsah webu tyto cíle? Nebo je tam 'Gap'?" 
            }}
        ],
        "recommendation": "Jedna strategická rada, jak zlepšit vnímání AI."
    }}
    """
    
    try:
        final_response = model.generate_content(
            final_prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        return json.loads(final_response.text)
    except Exception as e:
        print(f"Chyba ve finále: {e}")
        return _error_response(str(e))

def _error_response(msg):
    return {
        "summary": { "overall_score": 0, "page_title": "Chyba Analýzy" },
        "insights": [{ "type": "warning", "title": "Error", "message": f"Selhání modelu: {msg}" }],
        "recommendation": "Zkuste opakovat analýzu."
    }
