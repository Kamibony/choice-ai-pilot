import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import os

# Konfigurácia pre Cloud Run v Európe
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "europe-west1" 

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Vertex AI init failed: {e}")

def analyze_content(scraped_data: dict, client_brief: dict):
    """
    AI Reputation & Perception Analysis (Možnosť B)
    Zisťuje, ako AI vníma značku a či web komunikuje správne hodnoty.
    """
    
    # Používame Gemini 2.5 Pro pre najlepšie uvažovanie
    try:
        model = GenerativeModel("gemini-2.5-pro")
    except Exception as e:
        return _error_response(str(e))
    
    # --- PROMPT PRE REPUTAČNÚ ANALÝZU ---
    prompt = f"""
    Jsi expertní AI konzultant pro řízení reputace (AI Perception Management).
    Tvým úkolem není jen analyzovat web, ale zjistit, zda má značka vybudovanou "digitální identitu", které AI rozumí.

    VSTUPNÍ DATA:
    1. KLIENT (Identita): {client_brief.get('client_name')}
    2. SEKTOR: {client_brief.get('industry')}
    3. CÍLE KLIENTA (Jak chtějí být vnímáni): {client_brief.get('goals', 'Lídr na trhu')}
    4. REALITA (Obsah jejich webu): 
       URL: {scraped_data.get('url')}
       Titulek: {scraped_data.get('title')}
       Obsah (úryvek): {scraped_data.get('content_preview')}...

    POKYNY K ANALÝZE (Krok za krokem):
    1. Krok: Zkontroluj svou interní znalostní bázi (Training Data). Znáš entitu "{client_brief.get('client_name')}"? Pokud ne, je to "Unknown Entity".
    2. Krok: Analyzuj "Brand Gap". Je obsah webu v souladu s CÍLI klienta? (Např. Klient chce být "Premium", ale web působí "Levně").
    3. Krok: Navrhni, jak zlepšit vnímání značky v očích AI (LLM Optimization).

    VÝSTUPNÍ FORMÁT (JSON, Čeština):
    {{
        "summary": {{
            "overall_score": int,  // 0 = AI o vás neví, 100 = Silná AI autorita
            "ux_score": int,       // Zde použij jako "Skóre Jasnosti Komunikace"
            "seo_score": int,      // Zde použij jako "Skóre AI Čitelnosti"
            "page_title": "string" // Titulek stránky
        }},
        "insights": [
            // Zde buď velmi konkrétní a kritický
            {{ "type": "warning", "title": "AI Znalost (Perception)", "message": "Např: Gemini o vás nemá dost informací..." }},
            {{ "type": "info", "title": "Soulad s Cíli (Alignment)", "message": "Např: Web komunikuje X, ale cílem je Y..." }},
            {{ "type": "success", "title": "Silná stránka", "message": "Co dělá web dobře pro AI..." }}
        ],
        "recommendation": "Strategické doporučení v jedné větě, jak zlepšit reputaci u AI."
    }}
    """

    print(f"Spouštím AI Reputation Analysis v {LOCATION}...")
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3 # Nízká teplota pro analytickou přesnost
            )
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"Chyba AI: {e}")
        return _error_response(str(e))

def _error_response(msg):
    return {
        "summary": { "overall_score": 0, "ux_score": 0, "seo_score": 0, "page_title": "Chyba Analýzy" },
        "insights": [{ "type": "warning", "title": "System Error", "message": f"Selhání modelu: {msg}" }],
        "recommendation": "Zkuste opakovat analýzu."
    }
