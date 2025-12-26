import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import os

# Inicializácia Vertex AI
# ZMENA: Nastavené na europe-west1, pretože tam beží váš Cloud Run
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "europe-west1" 

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Vertex AI init failed (local run?): {e}")

def analyze_content(scraped_data: dict, client_brief: dict):
    """
    Odošle dáta do Gemini a získa skutočnú analýzu.
    """
    
    # 1. Príprava modelu
    # ZMENA: Používame model gemini-2.5-pro podľa vašej požiadavky
    try:
        model = GenerativeModel("gemini-2.5-pro")
    except Exception as e:
        print(f"Error initializing model: {e}")
        return {
            "summary": {"overall_score": 0, "ux_score": 0, "seo_score": 0, "page_title": "Model Error"},
            "insights": [{"type": "warning", "title": "Model Init Error", "message": f"Model gemini-2.5-pro nebol nájdený: {str(e)}"}],
            "recommendation": "Skontrolujte názov modelu."
        }
    
    # 2. Vytvorenie Promptu
    prompt = f"""
    You are a Senior UX & Marketing Auditor. Analyze the following website content based on the client brief using Gemini 2.5 Pro capabilities.
    
    CLIENT BRIEF:
    - Client Name: {client_brief.get('client_name')}
    - Industry: {client_brief.get('industry')}
    - Goals: {client_brief.get('goals')}
    
    WEBSITE DATA (Scraped):
    - URL: {scraped_data.get('url')}
    - Title: {scraped_data.get('title')}
    - Description: {scraped_data.get('description')}
    - Content Preview: {scraped_data.get('content_preview')}... (truncated)

    TASK:
    Analyze the website and provide a structured JSON response. Do NOT use Markdown formatting.
    Evaluate:
    1. UX Score (0-100) based on clarity and structure.
    2. SEO Score (0-100) based on keywords and meta tags.
    3. 3 specific insights (Success, Warning, Info).
    4. One strategic recommendation.

    OUTPUT FORMAT (JSON ONLY):
    {{
        "summary": {{
            "overall_score": int,
            "ux_score": int,
            "seo_score": int,
            "page_title": "string"
        }},
        "insights": [
            {{ "type": "success", "title": "string", "message": "string" }},
            {{ "type": "warning", "title": "string", "message": "string" }},
            {{ "type": "info", "title": "string", "message": "string" }}
        ],
        "recommendation": "string"
    }}
    """

    print(f"Sending request to Gemini 2.5 Pro in {LOCATION}...")
    
    try:
        # 3. Volanie AI
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        
        # 4. Spracovanie odpovede
        json_response = json.loads(response.text)
        return json_response

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        # Fallback pre prípad chyby
        return {
            "summary": { "overall_score": 0, "ux_score": 0, "seo_score": 0, "page_title": "Error in Analysis" },
            "insights": [{ "type": "warning", "title": "AI Error", "message": f"Chyba pri volaní AI: {str(e)}" }],
            "recommendation": "Skontrolujte dostupnosť modelu a kvóty v Google Cloud."
        }
