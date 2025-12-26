import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import os

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "europe-west1" 

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Vertex AI init failed: {e}")

def analyze_content(scraped_data: dict, client_brief: dict):
    try:
        model = GenerativeModel("gemini-2.5-pro")
    except Exception as e:
        return _error_response(str(e))
    
    # --- PROMPT PRE REPUTAČNÚ ANALÝZU ---
    prompt = f"""
    Jsi AI Perception Auditor. Tvým úkolem je porovnat, jak "AI vidí klienta" vs "Jak se klient prezentuje".
    
    VSTUPY:
    1. ENTITA (Klient): "{client_brief.get('client_name')}"
    2. WEB URL: {scraped_data.get('url')}
    3. OBSAH WEBU (Reality): {scraped_data.get('content_preview')}... (zkráceno)
    4. CÍLOVÁ IDENTITA (Co klient tvrdí): "{client_brief.get('goals')}"

    ÚKOL ANALÝZY (Postupuj přesně):
    1. MEMORY CHECK (Bez webu): Co víš o entitě "{client_brief.get('client_name')}" ze svých trénovacích dat?
       - Pokud ji znáš, jaké 3 klíčové atributy si s ní spojuješ?
       - Pokud ji neznáš, přiznej to (Unknown Entity).
    
    2. REALITY CHECK (S webem): Podporuje obsah webu "Cílovou Identitu"?
       - Hledáš rozpory (např. Cíl="Inovace", Web="Zastaralý text").

    VÝSTUP JSON (Čeština):
    {{
        "summary": {{
            "overall_score": int, // 0-100 (100 = AI vás perfektně zná a web odpovídá cílům)
            "page_title": "{client_brief.get('client_name')}" 
        }},
        "insights": [
            {{ 
                "type": "info", 
                "title": "Co o vás vím (AI Memory)", 
                "message": "Zde napiš, co o firmě víš z paměti. Pokud nic, napiš: 'Ve své paměti tuto firmu neeviduji jako známou značku.'" 
            }},
            {{ 
                "type": "warning", 
                "title": "Rozpor Identity (Gap Analysis)", 
                "message": "Porovnej 'Cílovou Identitu' s obsahem webu. Např: 'Tvrdíte, že jste lídři v AI, ale na webu o tom není zmínka.'" 
            }},
            {{ 
                "type": "success", 
                "title": "Verdikt", 
                "message": "Celkové shrnutí reputace." 
            }}
        ],
        "recommendation": "Jedna konkrétní rada, jak přesvědčit AI (LLM), aby vás vnímala lépe."
    }}
    """

    print(f"Spouštím Perception Audit pro: {client_brief.get('client_name')}")
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        return json.loads(response.text)

    except Exception as e:
        return _error_response(str(e))

def _error_response(msg):
    return {
        "summary": { "overall_score": 0, "page_title": "Chyba" },
        "insights": [{ "type": "warning", "title": "Error", "message": str(msg) }, { "type": "warning", "title": "-", "message": "-" }],
        "recommendation": "Skuste znova."
    }
